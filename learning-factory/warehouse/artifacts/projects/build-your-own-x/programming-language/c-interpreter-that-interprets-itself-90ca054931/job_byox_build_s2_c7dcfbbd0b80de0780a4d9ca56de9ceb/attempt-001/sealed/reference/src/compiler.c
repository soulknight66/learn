#include "internal.h"

#include <stdarg.h>
#include <stdio.h>
#include <string.h>

typedef struct {
    char name[EMBER_IDENT_MAX + 1U];
    size_t length;
    size_t slot;
    size_t depth;
} Symbol;

typedef struct {
    const char *path;
    Lexer lexer;
    Token current;
    EmberProgram *program;
    Symbol symbols[EMBER_LOCAL_MAX];
    size_t symbol_count;
    size_t slot_count;
    size_t max_slots;
    size_t depth;
    int failed;
    char *error;
    size_t error_size;
} Compiler;

static void fail_at(Compiler *compiler, Token token, const char *format, ...) {
    char detail[256];
    va_list arguments;
    if (compiler->failed) {
        return;
    }
    va_start(arguments, format);
    (void)vsnprintf(detail, sizeof(detail), format, arguments);
    va_end(arguments);
    (void)snprintf(compiler->error, compiler->error_size, "%s:%zu:%zu: %s",
                   compiler->path, token.line, token.column, detail);
    compiler->failed = 1;
}

static void advance_token(Compiler *compiler) {
    if (compiler->failed) {
        return;
    }
    compiler->current = lexer_next(&compiler->lexer);
    if (compiler->current.kind == TOK_ERROR) {
        fail_at(compiler, compiler->current, "%s", compiler->current.message);
    }
}

static int match(Compiler *compiler, TokenKind kind) {
    if (compiler->current.kind != kind || compiler->failed) {
        return 0;
    }
    advance_token(compiler);
    return 1;
}

static Token consume(Compiler *compiler, TokenKind kind, const char *message) {
    Token token = compiler->current;
    if (compiler->failed) {
        return token;
    }
    if (token.kind != kind) {
        fail_at(compiler, token, "%s (found %s)", message,
                token_kind_name(token.kind));
        return token;
    }
    advance_token(compiler);
    return token;
}

static size_t emit_word(Compiler *compiler, int64_t word, Token site) {
    size_t index = compiler->program->count;
    if (compiler->failed) {
        return 0U;
    }
    if (index >= EMBER_CODE_MAX) {
        fail_at(compiler, site, "bytecode exceeds %u words", EMBER_CODE_MAX);
        return 0U;
    }
    compiler->program->words[index] = word;
    compiler->program->lines[index] = (uint32_t)site.line;
    compiler->program->columns[index] = (uint32_t)site.column;
    compiler->program->count++;
    return index;
}

static void emit_op(Compiler *compiler, OpCode op, Token site) {
    (void)emit_word(compiler, (int64_t)op, site);
}

static size_t emit_with_operand(Compiler *compiler, OpCode op, int64_t operand,
                                Token site) {
    emit_op(compiler, op, site);
    return emit_word(compiler, operand, site);
}

static size_t emit_jump(Compiler *compiler, OpCode op, Token site) {
    return emit_with_operand(compiler, op, -1, site);
}

static void patch_jump(Compiler *compiler, size_t operand_index) {
    if (compiler->failed) {
        return;
    }
    if (operand_index >= compiler->program->count) {
        fail_at(compiler, compiler->current, "internal invalid patch location");
        return;
    }
    compiler->program->words[operand_index] =
        (int64_t)compiler->program->count;
}

static int same_name(const Symbol *symbol, Token token) {
    return symbol->length == token.length &&
           memcmp(symbol->name, token.start, token.length) == 0;
}

static int find_symbol(const Compiler *compiler, Token name, size_t *slot) {
    size_t index = compiler->symbol_count;
    while (index > 0U) {
        index--;
        if (same_name(&compiler->symbols[index], name)) {
            *slot = compiler->symbols[index].slot;
            return 1;
        }
    }
    return 0;
}

static int duplicate_in_scope(const Compiler *compiler, Token name) {
    size_t index;
    for (index = compiler->symbol_count; index > 0U; index--) {
        const Symbol *symbol = &compiler->symbols[index - 1U];
        if (symbol->depth < compiler->depth) {
            break;
        }
        if (symbol->depth == compiler->depth && same_name(symbol, name)) {
            return 1;
        }
    }
    return 0;
}

static void add_symbol(Compiler *compiler, Token name, size_t slot) {
    Symbol *symbol;
    if (compiler->failed) {
        return;
    }
    if (compiler->symbol_count >= EMBER_LOCAL_MAX) {
        fail_at(compiler, name, "too many active local declarations");
        return;
    }
    symbol = &compiler->symbols[compiler->symbol_count++];
    memcpy(symbol->name, name.start, name.length);
    symbol->name[name.length] = '\0';
    symbol->length = name.length;
    symbol->slot = slot;
    symbol->depth = compiler->depth;
}

static void parse_expression(Compiler *compiler);
static void parse_statement(Compiler *compiler);

static void parse_primary(Compiler *compiler) {
    Token token = compiler->current;
    size_t slot;
    if (match(compiler, TOK_INTEGER)) {
        (void)emit_with_operand(compiler, OP_PUSH, token.integer, token);
        return;
    }
    if (match(compiler, TOK_IDENTIFIER)) {
        if (!find_symbol(compiler, token, &slot)) {
            fail_at(compiler, token, "unknown local '%.*s'", (int)token.length,
                    token.start);
            return;
        }
        (void)emit_with_operand(compiler, OP_LOAD_LOCAL, (int64_t)slot, token);
        return;
    }
    if (match(compiler, TOK_LPAREN)) {
        parse_expression(compiler);
        (void)consume(compiler, TOK_RPAREN, "expected ')' after expression");
        return;
    }
    if (match(compiler, TOK_ARG)) {
        (void)consume(compiler, TOK_LPAREN, "expected '(' after arg");
        parse_expression(compiler);
        (void)consume(compiler, TOK_RPAREN, "expected ')' after arg index");
        emit_op(compiler, OP_ARG, token);
        return;
    }
    if (match(compiler, TOK_LOAD)) {
        (void)consume(compiler, TOK_LPAREN, "expected '(' after load");
        parse_expression(compiler);
        (void)consume(compiler, TOK_RPAREN, "expected ')' after heap index");
        emit_op(compiler, OP_HLOAD, token);
        return;
    }
    fail_at(compiler, token, "expected expression");
}

static void parse_unary(Compiler *compiler) {
    Token token = compiler->current;
    if (match(compiler, TOK_BANG)) {
        parse_unary(compiler);
        emit_op(compiler, OP_NOT, token);
    } else if (match(compiler, TOK_MINUS)) {
        parse_unary(compiler);
        emit_op(compiler, OP_NEG, token);
    } else if (match(compiler, TOK_PLUS)) {
        parse_unary(compiler);
    } else {
        parse_primary(compiler);
    }
}

static void parse_factor(Compiler *compiler) {
    parse_unary(compiler);
    while (!compiler->failed &&
           (compiler->current.kind == TOK_STAR ||
            compiler->current.kind == TOK_SLASH ||
            compiler->current.kind == TOK_PERCENT)) {
        Token token = compiler->current;
        advance_token(compiler);
        parse_unary(compiler);
        if (token.kind == TOK_STAR) {
            emit_op(compiler, OP_MUL, token);
        } else if (token.kind == TOK_SLASH) {
            emit_op(compiler, OP_DIV, token);
        } else {
            emit_op(compiler, OP_MOD, token);
        }
    }
}

static void parse_term(Compiler *compiler) {
    parse_factor(compiler);
    while (!compiler->failed &&
           (compiler->current.kind == TOK_PLUS ||
            compiler->current.kind == TOK_MINUS)) {
        Token token = compiler->current;
        advance_token(compiler);
        parse_factor(compiler);
        emit_op(compiler, token.kind == TOK_PLUS ? OP_ADD : OP_SUB, token);
    }
}

static void parse_comparison(Compiler *compiler) {
    parse_term(compiler);
    while (!compiler->failed &&
           (compiler->current.kind == TOK_LT ||
            compiler->current.kind == TOK_LE ||
            compiler->current.kind == TOK_GT ||
            compiler->current.kind == TOK_GE)) {
        Token token = compiler->current;
        OpCode op = OP_LT;
        advance_token(compiler);
        parse_term(compiler);
        if (token.kind == TOK_LE) {
            op = OP_LE;
        } else if (token.kind == TOK_GT) {
            op = OP_GT;
        } else if (token.kind == TOK_GE) {
            op = OP_GE;
        }
        emit_op(compiler, op, token);
    }
}

static void parse_equality(Compiler *compiler) {
    parse_comparison(compiler);
    while (!compiler->failed &&
           (compiler->current.kind == TOK_EQ ||
            compiler->current.kind == TOK_NE)) {
        Token token = compiler->current;
        advance_token(compiler);
        parse_comparison(compiler);
        emit_op(compiler, token.kind == TOK_EQ ? OP_EQ : OP_NE, token);
    }
}

static void parse_logical_and(Compiler *compiler) {
    parse_equality(compiler);
    while (!compiler->failed && compiler->current.kind == TOK_AND) {
        Token token = compiler->current;
        size_t false_jump;
        size_t end_jump;
        advance_token(compiler);
        false_jump = emit_jump(compiler, OP_JZ, token);
        parse_equality(compiler);
        emit_op(compiler, OP_NOT, token);
        emit_op(compiler, OP_NOT, token);
        end_jump = emit_jump(compiler, OP_JMP, token);
        patch_jump(compiler, false_jump);
        (void)emit_with_operand(compiler, OP_PUSH, 0, token);
        patch_jump(compiler, end_jump);
    }
}

static void parse_logical_or(Compiler *compiler) {
    parse_logical_and(compiler);
    while (!compiler->failed && compiler->current.kind == TOK_OR) {
        Token token = compiler->current;
        size_t rhs_jump;
        size_t end_jump;
        advance_token(compiler);
        rhs_jump = emit_jump(compiler, OP_JZ, token);
        (void)emit_with_operand(compiler, OP_PUSH, 1, token);
        end_jump = emit_jump(compiler, OP_JMP, token);
        patch_jump(compiler, rhs_jump);
        parse_logical_and(compiler);
        emit_op(compiler, OP_NOT, token);
        emit_op(compiler, OP_NOT, token);
        patch_jump(compiler, end_jump);
    }
}

static void parse_expression(Compiler *compiler) {
    parse_logical_or(compiler);
}

static void parse_declaration(Compiler *compiler) {
    Token int_token = consume(compiler, TOK_INT, "expected int");
    Token name = consume(compiler, TOK_IDENTIFIER,
                         "expected local name after int");
    size_t slot;
    if (compiler->failed) {
        return;
    }
    if (duplicate_in_scope(compiler, name)) {
        fail_at(compiler, name, "duplicate declaration '%.*s'",
                (int)name.length, name.start);
        return;
    }
    if (compiler->slot_count >= EMBER_LOCAL_MAX) {
        fail_at(compiler, name, "more than %u active local slots",
                EMBER_LOCAL_MAX);
        return;
    }
    slot = compiler->slot_count++;
    if (compiler->slot_count > compiler->max_slots) {
        compiler->max_slots = compiler->slot_count;
    }

    if (match(compiler, TOK_ASSIGN)) {
        parse_expression(compiler);
    } else {
        (void)emit_with_operand(compiler, OP_PUSH, 0, int_token);
    }
    add_symbol(compiler, name, slot);
    emit_with_operand(compiler, OP_STORE_LOCAL, (int64_t)slot, name);
    (void)consume(compiler, TOK_SEMICOLON,
                  "expected ';' after declaration");
}

static void parse_assignment(Compiler *compiler) {
    Token name = consume(compiler, TOK_IDENTIFIER, "expected local name");
    size_t slot;
    if (compiler->failed) {
        return;
    }
    if (!find_symbol(compiler, name, &slot)) {
        fail_at(compiler, name, "unknown local '%.*s'", (int)name.length,
                name.start);
        return;
    }
    (void)consume(compiler, TOK_ASSIGN, "expected '=' after local name");
    parse_expression(compiler);
    (void)consume(compiler, TOK_SEMICOLON,
                  "expected ';' after assignment");
    (void)emit_with_operand(compiler, OP_STORE_LOCAL, (int64_t)slot, name);
}

static void parse_block(Compiler *compiler) {
    size_t symbol_base;
    size_t slot_base;
    (void)consume(compiler, TOK_LBRACE, "expected '{'");
    if (compiler->failed) {
        return;
    }
    compiler->depth++;
    symbol_base = compiler->symbol_count;
    slot_base = compiler->slot_count;
    while (!compiler->failed && compiler->current.kind != TOK_RBRACE &&
           compiler->current.kind != TOK_EOF) {
        parse_statement(compiler);
    }
    (void)consume(compiler, TOK_RBRACE, "expected '}' after block");
    compiler->symbol_count = symbol_base;
    compiler->slot_count = slot_base;
    compiler->depth--;
}

static void parse_if(Compiler *compiler) {
    Token token = consume(compiler, TOK_IF, "expected if");
    size_t false_jump;
    (void)consume(compiler, TOK_LPAREN, "expected '(' after if");
    parse_expression(compiler);
    (void)consume(compiler, TOK_RPAREN, "expected ')' after condition");
    false_jump = emit_jump(compiler, OP_JZ, token);
    parse_statement(compiler);
    if (match(compiler, TOK_ELSE)) {
        size_t end_jump = emit_jump(compiler, OP_JMP, token);
        patch_jump(compiler, false_jump);
        parse_statement(compiler);
        patch_jump(compiler, end_jump);
    } else {
        patch_jump(compiler, false_jump);
    }
}

static void parse_while(Compiler *compiler) {
    Token token = consume(compiler, TOK_WHILE, "expected while");
    size_t loop_start = compiler->program->count;
    size_t exit_jump;
    (void)consume(compiler, TOK_LPAREN, "expected '(' after while");
    parse_expression(compiler);
    (void)consume(compiler, TOK_RPAREN, "expected ')' after condition");
    exit_jump = emit_jump(compiler, OP_JZ, token);
    parse_statement(compiler);
    (void)emit_with_operand(compiler, OP_JMP, (int64_t)loop_start, token);
    patch_jump(compiler, exit_jump);
}

static void parse_return(Compiler *compiler) {
    Token token = consume(compiler, TOK_RETURN, "expected return");
    parse_expression(compiler);
    (void)consume(compiler, TOK_SEMICOLON, "expected ';' after return");
    emit_op(compiler, OP_RETURN, token);
}

static void parse_print(Compiler *compiler) {
    Token token = consume(compiler, TOK_PRINT, "expected print");
    (void)consume(compiler, TOK_LPAREN, "expected '(' after print");
    parse_expression(compiler);
    (void)consume(compiler, TOK_RPAREN, "expected ')' after print value");
    (void)consume(compiler, TOK_SEMICOLON, "expected ';' after print");
    emit_op(compiler, OP_PRINT, token);
}

static void parse_store(Compiler *compiler) {
    Token token = consume(compiler, TOK_STORE, "expected store");
    (void)consume(compiler, TOK_LPAREN, "expected '(' after store");
    parse_expression(compiler);
    (void)consume(compiler, TOK_COMMA, "expected ',' between store operands");
    parse_expression(compiler);
    (void)consume(compiler, TOK_RPAREN, "expected ')' after store operands");
    (void)consume(compiler, TOK_SEMICOLON, "expected ';' after store");
    emit_op(compiler, OP_HSTORE, token);
}

static void parse_statement(Compiler *compiler) {
    switch (compiler->current.kind) {
    case TOK_LBRACE:
        parse_block(compiler);
        break;
    case TOK_INT:
        parse_declaration(compiler);
        break;
    case TOK_IDENTIFIER:
        parse_assignment(compiler);
        break;
    case TOK_IF:
        parse_if(compiler);
        break;
    case TOK_WHILE:
        parse_while(compiler);
        break;
    case TOK_RETURN:
        parse_return(compiler);
        break;
    case TOK_PRINT:
        parse_print(compiler);
        break;
    case TOK_STORE:
        parse_store(compiler);
        break;
    default:
        fail_at(compiler, compiler->current, "expected statement");
        break;
    }
}

int ember_compile(const char *path, const char *source, size_t length,
                  EmberProgram *program, char *error, size_t error_size) {
    Compiler compiler;
    Token final_site;
    memset(&compiler, 0, sizeof(compiler));
    memset(program, 0, sizeof(*program));
    compiler.path = path;
    compiler.program = program;
    compiler.error = error;
    compiler.error_size = error_size;
    lexer_init(&compiler.lexer, source, length);
    advance_token(&compiler);

    (void)consume(&compiler, TOK_INT, "program must begin with int");
    (void)consume(&compiler, TOK_MAIN, "expected main after int");
    (void)consume(&compiler, TOK_LPAREN, "expected '(' after main");
    (void)consume(&compiler, TOK_RPAREN, "expected ')' after main(");
    parse_block(&compiler);
    if (!compiler.failed && compiler.current.kind != TOK_EOF) {
        fail_at(&compiler, compiler.current, "unexpected token after main");
    }
    if (compiler.failed) {
        return 1;
    }

    final_site = compiler.current;
    (void)emit_with_operand(&compiler, OP_PUSH, 0, final_site);
    emit_op(&compiler, OP_RETURN, final_site);
    program->local_count = compiler.max_slots;
    return compiler.failed ? 1 : 0;
}
