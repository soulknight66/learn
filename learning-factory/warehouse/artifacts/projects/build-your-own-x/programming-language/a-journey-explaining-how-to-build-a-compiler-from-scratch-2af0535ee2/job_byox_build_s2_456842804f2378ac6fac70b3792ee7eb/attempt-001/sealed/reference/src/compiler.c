#include "sprig.h"

#include <stdio.h>
#include <string.h>

typedef struct {
    char name[SPRIG_MAX_NAME + 1u];
    size_t slot;
} Binding;

typedef struct {
    Lexer lexer;
    Token current;
    Program *program;
    Diagnostic *diagnostic;
    Binding bindings[SPRIG_MAX_VARIABLES];
    size_t binding_count;
    size_t nesting;
    int failed;
} Parser;

static void set_error(Parser *parser, size_t line, size_t column,
                      const char *message) {
    if (parser->failed) {
        return;
    }
    parser->failed = 1;
    parser->diagnostic->line = line;
    parser->diagnostic->column = column;
    (void)snprintf(parser->diagnostic->message,
                   sizeof(parser->diagnostic->message), "%s", message);
}

static void advance_token(Parser *parser) {
    if (parser->failed) {
        return;
    }
    if (!lexer_next(&parser->lexer, &parser->current)) {
        set_error(parser, parser->lexer.error_line,
                  parser->lexer.error_column, parser->lexer.error);
    }
}

static int consume(Parser *parser, TokenKind expected,
                   const char *expectation) {
    char message[160];
    if (parser->failed) {
        return 0;
    }
    if (parser->current.kind != expected) {
        (void)snprintf(message, sizeof(message), "expected %s; found %s",
                       expectation, token_kind_name(parser->current.kind));
        set_error(parser, parser->current.line, parser->current.column,
                  message);
        return 0;
    }
    advance_token(parser);
    return !parser->failed;
}

static int emit(Parser *parser, OpCode opcode, int64_t operand,
                size_t line, size_t column) {
    Instruction *instruction;
    if (parser->failed) {
        return 0;
    }
    if (parser->program->count >= SPRIG_MAX_INSTRUCTIONS) {
        set_error(parser, line, column, "instruction limit exceeded");
        return 0;
    }
    instruction = &parser->program->code[parser->program->count++];
    instruction->opcode = opcode;
    instruction->operand = operand;
    instruction->line = line;
    instruction->column = column;
    return 1;
}

static int find_binding(const Parser *parser, const char *name) {
    size_t index;
    for (index = 0u; index < parser->binding_count; index++) {
        if (strcmp(parser->bindings[index].name, name) == 0) {
            return (int)parser->bindings[index].slot;
        }
    }
    return -1;
}

static int parse_expression(Parser *parser);

static int parse_primary(Parser *parser) {
    Token token = parser->current;
    int slot;
    char message[160];

    if (token.kind == TOK_INTEGER) {
        advance_token(parser);
        return emit(parser, OP_CONST, token.integer, token.line, token.column);
    }
    if (token.kind == TOK_IDENTIFIER) {
        slot = find_binding(parser, token.lexeme);
        if (slot < 0) {
            (void)snprintf(message, sizeof(message),
                           "undefined identifier '%s'", token.lexeme);
            set_error(parser, token.line, token.column, message);
            return 0;
        }
        advance_token(parser);
        return emit(parser, OP_LOAD, (int64_t)slot,
                    token.line, token.column);
    }
    if (token.kind == TOK_LEFT_PAREN) {
        advance_token(parser);
        if (parser->failed) {
            return 0;
        }
        if (parser->nesting >= SPRIG_MAX_NESTING) {
            set_error(parser, token.line, token.column,
                      "expression nesting limit exceeded");
            return 0;
        }
        parser->nesting++;
        if (!parse_expression(parser)) {
            parser->nesting--;
            return 0;
        }
        parser->nesting--;
        return consume(parser, TOK_RIGHT_PAREN, "')'");
    }
    (void)snprintf(message, sizeof(message),
                   "expected expression; found %s",
                   token_kind_name(token.kind));
    set_error(parser, token.line, token.column, message);
    return 0;
}

static int parse_unary(Parser *parser) {
    if (parser->current.kind == TOK_MINUS) {
        Token operator_token = parser->current;
        advance_token(parser);
        if (parser->failed) {
            return 0;
        }
        if (parser->nesting >= SPRIG_MAX_NESTING) {
            set_error(parser, operator_token.line, operator_token.column,
                      "expression nesting limit exceeded");
            return 0;
        }
        parser->nesting++;
        if (!parse_unary(parser)) {
            parser->nesting--;
            return 0;
        }
        parser->nesting--;
        return emit(parser, OP_NEG, 0, operator_token.line,
                    operator_token.column);
    }
    return parse_primary(parser);
}

static int parse_term(Parser *parser) {
    if (!parse_unary(parser)) {
        return 0;
    }
    while (!parser->failed &&
           (parser->current.kind == TOK_STAR ||
            parser->current.kind == TOK_SLASH)) {
        Token operator_token = parser->current;
        advance_token(parser);
        if (!parse_unary(parser)) {
            return 0;
        }
        if (!emit(parser,
                  operator_token.kind == TOK_STAR ? OP_MUL : OP_DIV,
                  0, operator_token.line, operator_token.column)) {
            return 0;
        }
    }
    return !parser->failed;
}

static int parse_expression(Parser *parser) {
    if (!parse_term(parser)) {
        return 0;
    }
    while (!parser->failed &&
           (parser->current.kind == TOK_PLUS ||
            parser->current.kind == TOK_MINUS)) {
        Token operator_token = parser->current;
        advance_token(parser);
        if (!parse_term(parser)) {
            return 0;
        }
        if (!emit(parser,
                  operator_token.kind == TOK_PLUS ? OP_ADD : OP_SUB,
                  0, operator_token.line, operator_token.column)) {
            return 0;
        }
    }
    return !parser->failed;
}

static int parse_let(Parser *parser) {
    Token name;
    size_t slot;
    char message[160];

    advance_token(parser);
    if (parser->failed) {
        return 0;
    }
    if (parser->current.kind != TOK_IDENTIFIER) {
        set_error(parser, parser->current.line, parser->current.column,
                  "expected identifier after 'let'");
        return 0;
    }
    name = parser->current;
    if (find_binding(parser, name.lexeme) >= 0) {
        (void)snprintf(message, sizeof(message),
                       "duplicate declaration of '%s'", name.lexeme);
        set_error(parser, name.line, name.column, message);
        return 0;
    }
    if (parser->binding_count >= SPRIG_MAX_VARIABLES) {
        set_error(parser, name.line, name.column,
                  "variable limit exceeded");
        return 0;
    }
    slot = parser->binding_count;
    advance_token(parser);
    if (!consume(parser, TOK_EQUAL, "'='") ||
        !parse_expression(parser) ||
        !consume(parser, TOK_SEMICOLON, "';'") ||
        !emit(parser, OP_STORE, (int64_t)slot, name.line, name.column)) {
        return 0;
    }
    (void)snprintf(parser->bindings[slot].name,
                   sizeof(parser->bindings[slot].name), "%s", name.lexeme);
    parser->bindings[slot].slot = slot;
    parser->binding_count++;
    return 1;
}

static int parse_print(Parser *parser) {
    Token keyword = parser->current;
    advance_token(parser);
    if (!parse_expression(parser) ||
        !consume(parser, TOK_SEMICOLON, "';'")) {
        return 0;
    }
    return emit(parser, OP_PRINT, 0, keyword.line, keyword.column);
}

static int parse_statement(Parser *parser) {
    char message[160];
    if (parser->current.kind == TOK_LET) {
        return parse_let(parser);
    }
    if (parser->current.kind == TOK_PRINT) {
        return parse_print(parser);
    }
    (void)snprintf(message, sizeof(message),
                   "expected 'let' or 'print'; found %s",
                   token_kind_name(parser->current.kind));
    set_error(parser, parser->current.line, parser->current.column, message);
    return 0;
}

int compile_source(const unsigned char *source, size_t length,
                   Program *program, Diagnostic *diagnostic) {
    Parser parser;

    memset(program, 0, sizeof(*program));
    memset(diagnostic, 0, sizeof(*diagnostic));
    memset(&parser, 0, sizeof(parser));
    parser.program = program;
    parser.diagnostic = diagnostic;
    lexer_init(&parser.lexer, source, length);
    advance_token(&parser);
    while (!parser.failed && parser.current.kind != TOK_EOF) {
        (void)parse_statement(&parser);
    }
    if (!parser.failed) {
        (void)emit(&parser, OP_HALT, 0,
                   parser.current.line, parser.current.column);
    }
    program->variable_count = parser.binding_count;
    return !parser.failed;
}

static const char *opcode_name(OpCode opcode) {
    static const char *const names[] = {
        "CONST", "LOAD", "STORE", "ADD", "SUB",
        "MUL", "DIV", "NEG", "PRINT", "HALT"
    };
    size_t index = (size_t)opcode;
    if (index >= sizeof(names) / sizeof(names[0])) {
        return "UNKNOWN";
    }
    return names[index];
}

void disassemble_program(const Program *program, FILE *output) {
    size_t index;
    for (index = 0u; index < program->count; index++) {
        const Instruction *instruction = &program->code[index];
        fprintf(output, "%04zu %-5s", index,
                opcode_name(instruction->opcode));
        if (instruction->opcode == OP_CONST ||
            instruction->opcode == OP_LOAD ||
            instruction->opcode == OP_STORE) {
            fprintf(output, " %lld", (long long)instruction->operand);
        }
        fprintf(output, " @ %zu:%zu\n",
                instruction->line, instruction->column);
    }
}
