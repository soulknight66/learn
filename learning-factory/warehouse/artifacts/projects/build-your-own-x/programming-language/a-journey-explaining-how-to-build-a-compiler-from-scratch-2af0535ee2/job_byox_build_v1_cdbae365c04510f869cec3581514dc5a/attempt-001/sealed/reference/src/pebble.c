#include "pebble.h"

#include <inttypes.h>
#include <limits.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

typedef enum {
    TOK_EOF,
    TOK_ERROR,
    TOK_INTEGER,
    TOK_IDENTIFIER,
    TOK_LET,
    TOK_PRINT,
    TOK_IF,
    TOK_ELSE,
    TOK_WHILE,
    TOK_LEFT_PAREN,
    TOK_RIGHT_PAREN,
    TOK_LEFT_BRACE,
    TOK_RIGHT_BRACE,
    TOK_SEMICOLON,
    TOK_PLUS,
    TOK_MINUS,
    TOK_STAR,
    TOK_SLASH,
    TOK_PERCENT,
    TOK_BANG,
    TOK_BANG_EQUAL,
    TOK_EQUAL,
    TOK_EQUAL_EQUAL,
    TOK_LESS,
    TOK_LESS_EQUAL,
    TOK_GREATER,
    TOK_GREATER_EQUAL,
    TOK_AND_AND,
    TOK_OR_OR
} TokenType;

typedef struct {
    TokenType type;
    const char *start;
    size_t length;
    size_t line;
    size_t column;
    int64_t integer;
    const char *error;
} Token;

typedef struct {
    const char *source;
    size_t start;
    size_t current;
    size_t line;
    size_t column;
    size_t token_line;
    size_t token_column;
} Scanner;

typedef enum {
    OP_CONSTANT,
    OP_LOAD,
    OP_STORE,
    OP_NEGATE,
    OP_NOT,
    OP_ADD,
    OP_SUBTRACT,
    OP_MULTIPLY,
    OP_DIVIDE,
    OP_REMAINDER,
    OP_EQUAL,
    OP_NOT_EQUAL,
    OP_LESS,
    OP_LESS_EQUAL,
    OP_GREATER,
    OP_GREATER_EQUAL,
    OP_JUMP,
    OP_JUMP_IF_FALSE,
    OP_PRINT,
    OP_HALT
} OpCode;

typedef struct {
    unsigned char opcode;
    size_t operand;
    size_t line;
    size_t column;
} Instruction;

struct PebbleProgram {
    Instruction *code;
    size_t code_count;
    size_t code_capacity;
    int64_t *constants;
    size_t constant_count;
    size_t constant_capacity;
    size_t slots;
};

typedef struct {
    const char *name;
    size_t length;
    size_t depth;
    size_t slot;
} Symbol;

typedef struct {
    Scanner scanner;
    Token previous;
    Token current;
    PebbleProgram *program;
    PebbleOptions options;
    FILE *diagnostics;
    PebbleResult result;
    Symbol *symbols;
    size_t symbol_count;
    size_t symbol_capacity;
    size_t scope_depth;
    size_t next_slot;
    size_t stack_depth;
} Compiler;

static void expression(Compiler *compiler);
static void declaration(Compiler *compiler);

PebbleOptions pebble_default_options(void) {
    PebbleOptions options;
    options.max_code = 65536;
    options.max_constants = 4096;
    options.max_symbols = 1024;
    options.max_stack = 1024;
    options.max_steps = UINT64_C(1000000);
    return options;
}

static PebbleOptions normalized_options(const PebbleOptions *provided) {
    PebbleOptions result = pebble_default_options();
    if (provided != NULL) {
        if (provided->max_code != 0) result.max_code = provided->max_code;
        if (provided->max_constants != 0) result.max_constants = provided->max_constants;
        if (provided->max_symbols != 0) result.max_symbols = provided->max_symbols;
        if (provided->max_stack != 0) result.max_stack = provided->max_stack;
        if (provided->max_steps != 0) result.max_steps = provided->max_steps;
    }
    return result;
}

static void scanner_init(Scanner *scanner, const char *source) {
    scanner->source = source;
    scanner->start = 0;
    scanner->current = 0;
    scanner->line = 1;
    scanner->column = 1;
    scanner->token_line = 1;
    scanner->token_column = 1;
}

static char scanner_peek(const Scanner *scanner) {
    return scanner->source[scanner->current];
}

static char scanner_peek_next(const Scanner *scanner) {
    if (scanner_peek(scanner) == '\0') return '\0';
    return scanner->source[scanner->current + 1];
}

static char scanner_advance(Scanner *scanner) {
    char value = scanner->source[scanner->current++];
    if (value == '\n') {
        scanner->line++;
        scanner->column = 1;
    } else {
        scanner->column++;
    }
    return value;
}

static bool scanner_match(Scanner *scanner, char expected) {
    if (scanner_peek(scanner) != expected) return false;
    (void)scanner_advance(scanner);
    return true;
}

static Token make_token(const Scanner *scanner, TokenType type) {
    Token token;
    token.type = type;
    token.start = scanner->source + scanner->start;
    token.length = scanner->current - scanner->start;
    token.line = scanner->token_line;
    token.column = scanner->token_column;
    token.integer = 0;
    token.error = NULL;
    return token;
}

static Token error_token(const Scanner *scanner, const char *message) {
    Token token = make_token(scanner, TOK_ERROR);
    token.error = message;
    return token;
}

static bool ascii_alpha(char value) {
    return (value >= 'a' && value <= 'z') || (value >= 'A' && value <= 'Z') || value == '_';
}

static bool ascii_digit(char value) {
    return value >= '0' && value <= '9';
}

static bool token_spells(const Token *token, const char *word) {
    size_t length = strlen(word);
    return token->length == length && memcmp(token->start, word, length) == 0;
}

static TokenType identifier_type(const Token *token) {
    if (token_spells(token, "let")) return TOK_LET;
    if (token_spells(token, "print")) return TOK_PRINT;
    if (token_spells(token, "if")) return TOK_IF;
    if (token_spells(token, "else")) return TOK_ELSE;
    if (token_spells(token, "while")) return TOK_WHILE;
    return TOK_IDENTIFIER;
}

static void scanner_skip_ignored(Scanner *scanner) {
    for (;;) {
        char value = scanner_peek(scanner);
        if (value == ' ' || value == '\t' || value == '\r' || value == '\n') {
            (void)scanner_advance(scanner);
        } else if (value == '/' && scanner_peek_next(scanner) == '/') {
            while (scanner_peek(scanner) != '\n' && scanner_peek(scanner) != '\0') {
                (void)scanner_advance(scanner);
            }
        } else {
            return;
        }
    }
}

static Token scan_number(Scanner *scanner) {
    uint64_t value = (uint64_t)(scanner->source[scanner->start] - '0');
    bool overflow = false;
    Token token;
    while (ascii_digit(scanner_peek(scanner))) {
        unsigned int digit = (unsigned int)(scanner_peek(scanner) - '0');
        if (value > ((uint64_t)INT64_MAX - digit) / UINT64_C(10)) {
            overflow = true;
        } else if (!overflow) {
            value = value * UINT64_C(10) + digit;
        }
        (void)scanner_advance(scanner);
    }
    if (overflow) return error_token(scanner, "integer literal is out of range");
    token = make_token(scanner, TOK_INTEGER);
    token.integer = (int64_t)value;
    return token;
}

static Token scan_identifier(Scanner *scanner) {
    Token token;
    while (ascii_alpha(scanner_peek(scanner)) || ascii_digit(scanner_peek(scanner))) {
        (void)scanner_advance(scanner);
    }
    token = make_token(scanner, TOK_IDENTIFIER);
    token.type = identifier_type(&token);
    return token;
}

static Token scan_token(Scanner *scanner) {
    char value;
    scanner_skip_ignored(scanner);
    scanner->start = scanner->current;
    scanner->token_line = scanner->line;
    scanner->token_column = scanner->column;
    if (scanner_peek(scanner) == '\0') return make_token(scanner, TOK_EOF);
    value = scanner_advance(scanner);
    if (ascii_digit(value)) return scan_number(scanner);
    if (ascii_alpha(value)) return scan_identifier(scanner);
    switch (value) {
        case '(': return make_token(scanner, TOK_LEFT_PAREN);
        case ')': return make_token(scanner, TOK_RIGHT_PAREN);
        case '{': return make_token(scanner, TOK_LEFT_BRACE);
        case '}': return make_token(scanner, TOK_RIGHT_BRACE);
        case ';': return make_token(scanner, TOK_SEMICOLON);
        case '+': return make_token(scanner, TOK_PLUS);
        case '-': return make_token(scanner, TOK_MINUS);
        case '*': return make_token(scanner, TOK_STAR);
        case '/': return make_token(scanner, TOK_SLASH);
        case '%': return make_token(scanner, TOK_PERCENT);
        case '!': return make_token(scanner, scanner_match(scanner, '=') ? TOK_BANG_EQUAL : TOK_BANG);
        case '=': return make_token(scanner, scanner_match(scanner, '=') ? TOK_EQUAL_EQUAL : TOK_EQUAL);
        case '<': return make_token(scanner, scanner_match(scanner, '=') ? TOK_LESS_EQUAL : TOK_LESS);
        case '>': return make_token(scanner, scanner_match(scanner, '=') ? TOK_GREATER_EQUAL : TOK_GREATER);
        case '&':
            if (scanner_match(scanner, '&')) return make_token(scanner, TOK_AND_AND);
            return error_token(scanner, "expected '&' after '&'");
        case '|':
            if (scanner_match(scanner, '|')) return make_token(scanner, TOK_OR_OR);
            return error_token(scanner, "expected '|' after '|'");
        default: return error_token(scanner, "unexpected byte");
    }
}

static void compiler_fail(Compiler *compiler, PebbleResult result, const Token *token,
                          const char *message) {
    if (compiler->result != PEBBLE_OK) return;
    compiler->result = result;
    fprintf(compiler->diagnostics, "%zu:%zu: %s\n", token->line, token->column, message);
}

static void compiler_fail_name(Compiler *compiler, const Token *token, const char *prefix) {
    if (compiler->result != PEBBLE_OK) return;
    compiler->result = PEBBLE_COMPILE_ERROR;
    fprintf(compiler->diagnostics, "%zu:%zu: %s '%.*s'\n", token->line, token->column,
            prefix, (int)token->length, token->start);
}

static void advance_token(Compiler *compiler) {
    compiler->previous = compiler->current;
    compiler->current = scan_token(&compiler->scanner);
    if (compiler->current.type == TOK_ERROR) {
        compiler_fail(compiler, PEBBLE_COMPILE_ERROR, &compiler->current,
                      compiler->current.error);
    }
}

static bool check(const Compiler *compiler, TokenType type) {
    return compiler->current.type == type;
}

static bool match(Compiler *compiler, TokenType type) {
    if (!check(compiler, type)) return false;
    advance_token(compiler);
    return true;
}

static bool consume(Compiler *compiler, TokenType type, const char *message) {
    if (check(compiler, type)) {
        advance_token(compiler);
        return true;
    }
    compiler_fail(compiler, PEBBLE_COMPILE_ERROR, &compiler->current, message);
    return false;
}

static bool grow_array(void **array, size_t *capacity, size_t needed, size_t item_size,
                       size_t limit) {
    size_t next;
    void *grown;
    if (needed <= *capacity) return true;
    next = *capacity == 0 ? 8 : *capacity;
    if (next > limit) next = limit;
    while (next < needed) {
        if (next > limit / 2) {
            next = limit;
            break;
        }
        next *= 2;
    }
    if (next < needed || next > SIZE_MAX / item_size) return false;
    grown = realloc(*array, next * item_size);
    if (grown == NULL) return false;
    *array = grown;
    *capacity = next;
    return true;
}

static bool apply_stack_effect(Compiler *compiler, OpCode opcode, const Token *where) {
    size_t required = 0;
    size_t pushed = 0;
    switch (opcode) {
        case OP_CONSTANT:
        case OP_LOAD:
            pushed = 1;
            break;
        case OP_STORE:
        case OP_JUMP_IF_FALSE:
        case OP_PRINT:
            required = 1;
            break;
        case OP_ADD:
        case OP_SUBTRACT:
        case OP_MULTIPLY:
        case OP_DIVIDE:
        case OP_REMAINDER:
        case OP_EQUAL:
        case OP_NOT_EQUAL:
        case OP_LESS:
        case OP_LESS_EQUAL:
        case OP_GREATER:
        case OP_GREATER_EQUAL:
            required = 2;
            pushed = 1;
            break;
        case OP_NEGATE:
        case OP_NOT:
            required = 1;
            pushed = 1;
            break;
        case OP_JUMP:
        case OP_HALT:
            break;
    }
    if (compiler->stack_depth < required) {
        compiler_fail(compiler, PEBBLE_SYSTEM_ERROR, where, "internal compiler stack mismatch");
        return false;
    }
    compiler->stack_depth -= required;
    if (compiler->stack_depth > compiler->options.max_stack ||
        pushed > compiler->options.max_stack - compiler->stack_depth) {
        compiler_fail(compiler, PEBBLE_LIMIT_ERROR, where, "compile-time stack limit exceeded");
        return false;
    }
    compiler->stack_depth += pushed;
    return true;
}

static size_t emit_instruction(Compiler *compiler, OpCode opcode, size_t operand,
                               const Token *where) {
    Instruction *instruction;
    size_t index;
    if (compiler->result != PEBBLE_OK) return SIZE_MAX;
    if (compiler->program->code_count >= compiler->options.max_code) {
        compiler_fail(compiler, PEBBLE_LIMIT_ERROR, where, "bytecode instruction limit exceeded");
        return SIZE_MAX;
    }
    if (!apply_stack_effect(compiler, opcode, where)) return SIZE_MAX;
    if (!grow_array((void **)&compiler->program->code, &compiler->program->code_capacity,
                    compiler->program->code_count + 1, sizeof(Instruction),
                    compiler->options.max_code)) {
        compiler_fail(compiler, PEBBLE_SYSTEM_ERROR, where, "allocation failed while emitting code");
        return SIZE_MAX;
    }
    index = compiler->program->code_count++;
    instruction = &compiler->program->code[index];
    instruction->opcode = (unsigned char)opcode;
    instruction->operand = operand;
    instruction->line = where->line;
    instruction->column = where->column;
    return index;
}

static void patch_jump(Compiler *compiler, size_t index, size_t target, const Token *where) {
    if (compiler->result != PEBBLE_OK) return;
    if (index >= compiler->program->code_count || target > compiler->program->code_count) {
        compiler_fail(compiler, PEBBLE_SYSTEM_ERROR, where, "invalid internal jump patch");
        return;
    }
    compiler->program->code[index].operand = target;
}

static size_t add_constant(Compiler *compiler, int64_t value, const Token *where) {
    size_t index;
    if (compiler->result != PEBBLE_OK) return SIZE_MAX;
    if (compiler->program->constant_count >= compiler->options.max_constants) {
        compiler_fail(compiler, PEBBLE_LIMIT_ERROR, where, "constant pool limit exceeded");
        return SIZE_MAX;
    }
    if (!grow_array((void **)&compiler->program->constants,
                    &compiler->program->constant_capacity,
                    compiler->program->constant_count + 1, sizeof(int64_t),
                    compiler->options.max_constants)) {
        compiler_fail(compiler, PEBBLE_SYSTEM_ERROR, where,
                      "allocation failed while emitting constants");
        return SIZE_MAX;
    }
    index = compiler->program->constant_count++;
    compiler->program->constants[index] = value;
    return index;
}

static void emit_constant(Compiler *compiler, int64_t value, const Token *where) {
    size_t index = add_constant(compiler, value, where);
    if (index != SIZE_MAX) (void)emit_instruction(compiler, OP_CONSTANT, index, where);
}

static bool names_equal(const Symbol *symbol, const Token *name) {
    return symbol->length == name->length && memcmp(symbol->name, name->start, name->length) == 0;
}

static bool resolve_symbol(Compiler *compiler, const Token *name, size_t *slot) {
    size_t index = compiler->symbol_count;
    while (index > 0) {
        index--;
        if (names_equal(&compiler->symbols[index], name)) {
            *slot = compiler->symbols[index].slot;
            return true;
        }
    }
    compiler_fail_name(compiler, name, "undefined name");
    return false;
}

static bool add_symbol(Compiler *compiler, const Token *name, size_t *slot) {
    size_t index = compiler->symbol_count;
    Symbol *symbol;
    while (index > 0 && compiler->symbols[index - 1].depth == compiler->scope_depth) {
        index--;
        if (names_equal(&compiler->symbols[index], name)) {
            compiler_fail_name(compiler, name, "duplicate declaration of");
            return false;
        }
    }
    if (compiler->next_slot >= compiler->options.max_symbols) {
        compiler_fail(compiler, PEBBLE_LIMIT_ERROR, name, "symbol slot limit exceeded");
        return false;
    }
    if (!grow_array((void **)&compiler->symbols, &compiler->symbol_capacity,
                    compiler->symbol_count + 1, sizeof(Symbol),
                    compiler->options.max_symbols)) {
        compiler_fail(compiler, PEBBLE_SYSTEM_ERROR, name,
                      "allocation failed while adding a symbol");
        return false;
    }
    symbol = &compiler->symbols[compiler->symbol_count++];
    symbol->name = name->start;
    symbol->length = name->length;
    symbol->depth = compiler->scope_depth;
    symbol->slot = compiler->next_slot++;
    *slot = symbol->slot;
    return true;
}

static void end_scope(Compiler *compiler) {
    while (compiler->symbol_count > 0 &&
           compiler->symbols[compiler->symbol_count - 1].depth == compiler->scope_depth) {
        compiler->symbol_count--;
    }
    if (compiler->scope_depth > 0) compiler->scope_depth--;
}

static void primary(Compiler *compiler) {
    Token token;
    size_t slot;
    if (match(compiler, TOK_INTEGER)) {
        token = compiler->previous;
        emit_constant(compiler, token.integer, &token);
    } else if (match(compiler, TOK_IDENTIFIER)) {
        token = compiler->previous;
        if (resolve_symbol(compiler, &token, &slot)) {
            (void)emit_instruction(compiler, OP_LOAD, slot, &token);
        }
    } else if (match(compiler, TOK_LEFT_PAREN)) {
        expression(compiler);
        (void)consume(compiler, TOK_RIGHT_PAREN, "expected ')' after expression");
    } else {
        compiler_fail(compiler, PEBBLE_COMPILE_ERROR, &compiler->current,
                      "expected an expression");
    }
}

static void unary(Compiler *compiler) {
    if (match(compiler, TOK_BANG)) {
        Token operator_token = compiler->previous;
        unary(compiler);
        (void)emit_instruction(compiler, OP_NOT, 0, &operator_token);
    } else if (match(compiler, TOK_MINUS)) {
        Token operator_token = compiler->previous;
        unary(compiler);
        (void)emit_instruction(compiler, OP_NEGATE, 0, &operator_token);
    } else {
        primary(compiler);
    }
}

static void factor(Compiler *compiler) {
    unary(compiler);
    while (check(compiler, TOK_STAR) || check(compiler, TOK_SLASH) ||
           check(compiler, TOK_PERCENT)) {
        Token operator_token;
        TokenType type = compiler->current.type;
        advance_token(compiler);
        operator_token = compiler->previous;
        unary(compiler);
        if (type == TOK_STAR) (void)emit_instruction(compiler, OP_MULTIPLY, 0, &operator_token);
        else if (type == TOK_SLASH) (void)emit_instruction(compiler, OP_DIVIDE, 0, &operator_token);
        else (void)emit_instruction(compiler, OP_REMAINDER, 0, &operator_token);
    }
}

static void term(Compiler *compiler) {
    factor(compiler);
    while (check(compiler, TOK_PLUS) || check(compiler, TOK_MINUS)) {
        Token operator_token;
        TokenType type = compiler->current.type;
        advance_token(compiler);
        operator_token = compiler->previous;
        factor(compiler);
        (void)emit_instruction(compiler, type == TOK_PLUS ? OP_ADD : OP_SUBTRACT,
                               0, &operator_token);
    }
}

static void comparison(Compiler *compiler) {
    term(compiler);
    while (check(compiler, TOK_LESS) || check(compiler, TOK_LESS_EQUAL) ||
           check(compiler, TOK_GREATER) || check(compiler, TOK_GREATER_EQUAL)) {
        Token operator_token;
        TokenType type = compiler->current.type;
        OpCode opcode;
        advance_token(compiler);
        operator_token = compiler->previous;
        term(compiler);
        if (type == TOK_LESS) opcode = OP_LESS;
        else if (type == TOK_LESS_EQUAL) opcode = OP_LESS_EQUAL;
        else if (type == TOK_GREATER) opcode = OP_GREATER;
        else opcode = OP_GREATER_EQUAL;
        (void)emit_instruction(compiler, opcode, 0, &operator_token);
    }
}

static void equality(Compiler *compiler) {
    comparison(compiler);
    while (check(compiler, TOK_EQUAL_EQUAL) || check(compiler, TOK_BANG_EQUAL)) {
        Token operator_token;
        TokenType type = compiler->current.type;
        advance_token(compiler);
        operator_token = compiler->previous;
        comparison(compiler);
        (void)emit_instruction(compiler, type == TOK_EQUAL_EQUAL ? OP_EQUAL : OP_NOT_EQUAL,
                               0, &operator_token);
    }
}

static void logical_and(Compiler *compiler) {
    equality(compiler);
    while (match(compiler, TOK_AND_AND)) {
        Token operator_token = compiler->previous;
        size_t base = compiler->stack_depth > 0 ? compiler->stack_depth - 1 : 0;
        size_t left_false = emit_instruction(compiler, OP_JUMP_IF_FALSE, 0, &operator_token);
        size_t right_false;
        size_t end_jump;
        equality(compiler);
        right_false = emit_instruction(compiler, OP_JUMP_IF_FALSE, 0, &operator_token);
        emit_constant(compiler, 1, &operator_token);
        end_jump = emit_instruction(compiler, OP_JUMP, 0, &operator_token);
        compiler->stack_depth = base;
        patch_jump(compiler, left_false, compiler->program->code_count, &operator_token);
        patch_jump(compiler, right_false, compiler->program->code_count, &operator_token);
        emit_constant(compiler, 0, &operator_token);
        patch_jump(compiler, end_jump, compiler->program->code_count, &operator_token);
    }
}

static void logical_or(Compiler *compiler) {
    logical_and(compiler);
    while (match(compiler, TOK_OR_OR)) {
        Token operator_token = compiler->previous;
        size_t base = compiler->stack_depth > 0 ? compiler->stack_depth - 1 : 0;
        size_t evaluate_right = emit_instruction(compiler, OP_JUMP_IF_FALSE, 0, &operator_token);
        size_t first_end;
        size_t right_false;
        size_t second_end;
        emit_constant(compiler, 1, &operator_token);
        first_end = emit_instruction(compiler, OP_JUMP, 0, &operator_token);
        compiler->stack_depth = base;
        patch_jump(compiler, evaluate_right, compiler->program->code_count, &operator_token);
        logical_and(compiler);
        right_false = emit_instruction(compiler, OP_JUMP_IF_FALSE, 0, &operator_token);
        emit_constant(compiler, 1, &operator_token);
        second_end = emit_instruction(compiler, OP_JUMP, 0, &operator_token);
        compiler->stack_depth = base;
        patch_jump(compiler, right_false, compiler->program->code_count, &operator_token);
        emit_constant(compiler, 0, &operator_token);
        patch_jump(compiler, first_end, compiler->program->code_count, &operator_token);
        patch_jump(compiler, second_end, compiler->program->code_count, &operator_token);
    }
}

static void expression(Compiler *compiler) {
    logical_or(compiler);
}

static void block_body(Compiler *compiler) {
    compiler->scope_depth++;
    while (!check(compiler, TOK_RIGHT_BRACE) && !check(compiler, TOK_EOF) &&
           compiler->result == PEBBLE_OK) {
        declaration(compiler);
    }
    (void)consume(compiler, TOK_RIGHT_BRACE, "expected '}' after block");
    end_scope(compiler);
}

static void require_block(Compiler *compiler, const char *message) {
    if (consume(compiler, TOK_LEFT_BRACE, message)) block_body(compiler);
}

static void print_statement(Compiler *compiler, const Token *keyword) {
    expression(compiler);
    (void)consume(compiler, TOK_SEMICOLON, "expected ';' after printed expression");
    (void)emit_instruction(compiler, OP_PRINT, 0, keyword);
}

static void assignment_statement(Compiler *compiler) {
    Token name = compiler->current;
    size_t slot;
    advance_token(compiler);
    (void)consume(compiler, TOK_EQUAL, "expected '=' after assignment name");
    expression(compiler);
    (void)consume(compiler, TOK_SEMICOLON, "expected ';' after assignment");
    if (resolve_symbol(compiler, &name, &slot)) {
        (void)emit_instruction(compiler, OP_STORE, slot, &name);
    }
}

static void if_statement(Compiler *compiler, const Token *keyword) {
    size_t false_jump;
    size_t end_jump;
    (void)consume(compiler, TOK_LEFT_PAREN, "expected '(' after 'if'");
    expression(compiler);
    (void)consume(compiler, TOK_RIGHT_PAREN, "expected ')' after condition");
    false_jump = emit_instruction(compiler, OP_JUMP_IF_FALSE, 0, keyword);
    require_block(compiler, "expected '{' before if branch");
    end_jump = emit_instruction(compiler, OP_JUMP, 0, keyword);
    patch_jump(compiler, false_jump, compiler->program->code_count, keyword);
    if (match(compiler, TOK_ELSE)) {
        require_block(compiler, "expected '{' before else branch");
    }
    patch_jump(compiler, end_jump, compiler->program->code_count, keyword);
}

static void while_statement(Compiler *compiler, const Token *keyword) {
    size_t loop_start = compiler->program->code_count;
    size_t exit_jump;
    (void)consume(compiler, TOK_LEFT_PAREN, "expected '(' after 'while'");
    expression(compiler);
    (void)consume(compiler, TOK_RIGHT_PAREN, "expected ')' after condition");
    exit_jump = emit_instruction(compiler, OP_JUMP_IF_FALSE, 0, keyword);
    require_block(compiler, "expected '{' before while body");
    (void)emit_instruction(compiler, OP_JUMP, loop_start, keyword);
    patch_jump(compiler, exit_jump, compiler->program->code_count, keyword);
}

static void statement(Compiler *compiler) {
    if (match(compiler, TOK_PRINT)) {
        Token keyword = compiler->previous;
        print_statement(compiler, &keyword);
    } else if (match(compiler, TOK_IF)) {
        Token keyword = compiler->previous;
        if_statement(compiler, &keyword);
    } else if (match(compiler, TOK_WHILE)) {
        Token keyword = compiler->previous;
        while_statement(compiler, &keyword);
    } else if (match(compiler, TOK_LEFT_BRACE)) {
        block_body(compiler);
    } else if (check(compiler, TOK_IDENTIFIER)) {
        assignment_statement(compiler);
    } else {
        compiler_fail(compiler, PEBBLE_COMPILE_ERROR, &compiler->current,
                      "expected a declaration or statement");
    }
}

static void let_declaration(Compiler *compiler) {
    Token name;
    size_t slot;
    if (!consume(compiler, TOK_IDENTIFIER, "expected a name after 'let'")) return;
    name = compiler->previous;
    (void)consume(compiler, TOK_EQUAL, "expected '=' after declaration name");
    expression(compiler);
    (void)consume(compiler, TOK_SEMICOLON, "expected ';' after declaration");
    if (add_symbol(compiler, &name, &slot)) {
        (void)emit_instruction(compiler, OP_STORE, slot, &name);
    }
}

static void declaration(Compiler *compiler) {
    if (match(compiler, TOK_LET)) let_declaration(compiler);
    else statement(compiler);
}

void pebble_program_free(PebbleProgram *program) {
    if (program == NULL) return;
    free(program->code);
    free(program->constants);
    free(program);
}

PebbleResult pebble_compile(const char *source, const PebbleOptions *options,
                            PebbleProgram **out_program, FILE *diagnostics) {
    Compiler compiler;
    Token eof_token;
    if (out_program != NULL) *out_program = NULL;
    if (source == NULL || out_program == NULL || diagnostics == NULL) {
        return PEBBLE_SYSTEM_ERROR;
    }
    memset(&compiler, 0, sizeof(compiler));
    compiler.options = normalized_options(options);
    compiler.diagnostics = diagnostics;
    compiler.result = PEBBLE_OK;
    compiler.program = calloc(1, sizeof(*compiler.program));
    if (compiler.program == NULL) {
        fputs("system: allocation failed\n", diagnostics);
        return PEBBLE_SYSTEM_ERROR;
    }
    scanner_init(&compiler.scanner, source);
    advance_token(&compiler);
    while (!check(&compiler, TOK_EOF) && compiler.result == PEBBLE_OK) {
        declaration(&compiler);
    }
    eof_token = compiler.current;
    if (compiler.result == PEBBLE_OK && compiler.stack_depth != 0) {
        compiler_fail(&compiler, PEBBLE_SYSTEM_ERROR, &eof_token,
                      "internal compiler stack mismatch at end of program");
    }
    if (compiler.result == PEBBLE_OK) {
        (void)emit_instruction(&compiler, OP_HALT, 0, &eof_token);
    }
    compiler.program->slots = compiler.next_slot;
    free(compiler.symbols);
    if (compiler.result != PEBBLE_OK) {
        PebbleResult result = compiler.result;
        pebble_program_free(compiler.program);
        return result;
    }
    *out_program = compiler.program;
    return PEBBLE_OK;
}

static void vm_message(FILE *diagnostics, const Instruction *instruction, const char *message) {
    fprintf(diagnostics, "%zu:%zu: %s\n", instruction->line, instruction->column, message);
}

static bool checked_add(int64_t left, int64_t right, int64_t *result) {
    if ((right > 0 && left > INT64_MAX - right) ||
        (right < 0 && left < INT64_MIN - right)) return false;
    *result = left + right;
    return true;
}

static bool checked_subtract(int64_t left, int64_t right, int64_t *result) {
    if ((right > 0 && left < INT64_MIN + right) ||
        (right < 0 && left > INT64_MAX + right)) return false;
    *result = left - right;
    return true;
}

static bool checked_multiply(int64_t left, int64_t right, int64_t *result) {
    if (left > 0) {
        if ((right > 0 && left > INT64_MAX / right) ||
            (right < 0 && right < INT64_MIN / left)) return false;
    } else if (left < 0) {
        if ((right > 0 && left < INT64_MIN / right) ||
            (right < 0 && right < INT64_MAX / left)) return false;
    }
    *result = left * right;
    return true;
}

static PebbleResult execute_binary(OpCode opcode, int64_t left, int64_t right,
                                   int64_t *result, FILE *diagnostics,
                                   const Instruction *instruction) {
    switch (opcode) {
        case OP_ADD:
            if (!checked_add(left, right, result)) {
                vm_message(diagnostics, instruction, "integer overflow in addition");
                return PEBBLE_RUNTIME_ERROR;
            }
            break;
        case OP_SUBTRACT:
            if (!checked_subtract(left, right, result)) {
                vm_message(diagnostics, instruction, "integer overflow in subtraction");
                return PEBBLE_RUNTIME_ERROR;
            }
            break;
        case OP_MULTIPLY:
            if (!checked_multiply(left, right, result)) {
                vm_message(diagnostics, instruction, "integer overflow in multiplication");
                return PEBBLE_RUNTIME_ERROR;
            }
            break;
        case OP_DIVIDE:
            if (right == 0) {
                vm_message(diagnostics, instruction, "division by zero");
                return PEBBLE_RUNTIME_ERROR;
            }
            if (left == INT64_MIN && right == -1) {
                vm_message(diagnostics, instruction, "integer overflow in division");
                return PEBBLE_RUNTIME_ERROR;
            }
            *result = left / right;
            break;
        case OP_REMAINDER:
            if (right == 0) {
                vm_message(diagnostics, instruction, "remainder by zero");
                return PEBBLE_RUNTIME_ERROR;
            }
            if (left == INT64_MIN && right == -1) {
                vm_message(diagnostics, instruction, "integer overflow in remainder");
                return PEBBLE_RUNTIME_ERROR;
            }
            *result = left % right;
            break;
        case OP_EQUAL: *result = left == right ? 1 : 0; break;
        case OP_NOT_EQUAL: *result = left != right ? 1 : 0; break;
        case OP_LESS: *result = left < right ? 1 : 0; break;
        case OP_LESS_EQUAL: *result = left <= right ? 1 : 0; break;
        case OP_GREATER: *result = left > right ? 1 : 0; break;
        case OP_GREATER_EQUAL: *result = left >= right ? 1 : 0; break;
        default:
            vm_message(diagnostics, instruction, "invalid internal binary opcode");
            return PEBBLE_RUNTIME_ERROR;
    }
    return PEBBLE_OK;
}

PebbleResult pebble_execute(const PebbleProgram *program, const PebbleOptions *options,
                            FILE *output, FILE *diagnostics) {
    PebbleOptions limits;
    int64_t *stack;
    int64_t *locals = NULL;
    size_t stack_count = 0;
    size_t instruction_pointer = 0;
    uint64_t steps = 0;
    PebbleResult final_result = PEBBLE_OK;
    if (program == NULL || output == NULL || diagnostics == NULL) return PEBBLE_SYSTEM_ERROR;
    limits = normalized_options(options);
    if (program->code_count > limits.max_code || program->constant_count > limits.max_constants ||
        program->slots > limits.max_symbols) {
        fputs("limit: compiled program exceeds execution limits\n", diagnostics);
        return PEBBLE_LIMIT_ERROR;
    }
    if (limits.max_stack > SIZE_MAX / sizeof(int64_t) ||
        program->slots > SIZE_MAX / sizeof(int64_t)) {
        fputs("system: allocation size overflow\n", diagnostics);
        return PEBBLE_SYSTEM_ERROR;
    }
    stack = malloc(limits.max_stack * sizeof(*stack));
    if (stack == NULL) {
        fputs("system: stack allocation failed\n", diagnostics);
        return PEBBLE_SYSTEM_ERROR;
    }
    if (program->slots > 0) {
        locals = calloc(program->slots, sizeof(*locals));
        if (locals == NULL) {
            fputs("system: local allocation failed\n", diagnostics);
            free(stack);
            return PEBBLE_SYSTEM_ERROR;
        }
    }
    for (;;) {
        const Instruction *instruction;
        OpCode opcode;
        int64_t left;
        int64_t right;
        int64_t value;
        if (instruction_pointer >= program->code_count) {
            fputs("runtime: instruction pointer out of range\n", diagnostics);
            final_result = PEBBLE_RUNTIME_ERROR;
            break;
        }
        instruction = &program->code[instruction_pointer++];
        if (steps >= limits.max_steps) {
            vm_message(diagnostics, instruction, "execution step limit exceeded");
            final_result = PEBBLE_LIMIT_ERROR;
            break;
        }
        steps++;
        opcode = (OpCode)instruction->opcode;
        if (opcode == OP_HALT) {
            if (stack_count != 0) {
                vm_message(diagnostics, instruction, "nonempty stack at halt");
                final_result = PEBBLE_RUNTIME_ERROR;
            }
            break;
        }
        switch (opcode) {
            case OP_CONSTANT:
                if (instruction->operand >= program->constant_count) {
                    vm_message(diagnostics, instruction, "constant index out of range");
                    final_result = PEBBLE_RUNTIME_ERROR;
                    break;
                }
                if (stack_count >= limits.max_stack) {
                    vm_message(diagnostics, instruction, "runtime stack limit exceeded");
                    final_result = PEBBLE_LIMIT_ERROR;
                    break;
                }
                stack[stack_count++] = program->constants[instruction->operand];
                break;
            case OP_LOAD:
                if (instruction->operand >= program->slots) {
                    vm_message(diagnostics, instruction, "local index out of range");
                    final_result = PEBBLE_RUNTIME_ERROR;
                    break;
                }
                if (stack_count >= limits.max_stack) {
                    vm_message(diagnostics, instruction, "runtime stack limit exceeded");
                    final_result = PEBBLE_LIMIT_ERROR;
                    break;
                }
                stack[stack_count++] = locals[instruction->operand];
                break;
            case OP_STORE:
                if (instruction->operand >= program->slots || stack_count < 1) {
                    vm_message(diagnostics, instruction, "invalid local store");
                    final_result = PEBBLE_RUNTIME_ERROR;
                    break;
                }
                locals[instruction->operand] = stack[--stack_count];
                break;
            case OP_NEGATE:
                if (stack_count < 1) {
                    vm_message(diagnostics, instruction, "stack underflow in negation");
                    final_result = PEBBLE_RUNTIME_ERROR;
                    break;
                }
                if (stack[stack_count - 1] == INT64_MIN) {
                    vm_message(diagnostics, instruction, "integer overflow in negation");
                    final_result = PEBBLE_RUNTIME_ERROR;
                    break;
                }
                stack[stack_count - 1] = -stack[stack_count - 1];
                break;
            case OP_NOT:
                if (stack_count < 1) {
                    vm_message(diagnostics, instruction, "stack underflow in logical not");
                    final_result = PEBBLE_RUNTIME_ERROR;
                    break;
                }
                stack[stack_count - 1] = stack[stack_count - 1] == 0 ? 1 : 0;
                break;
            case OP_ADD:
            case OP_SUBTRACT:
            case OP_MULTIPLY:
            case OP_DIVIDE:
            case OP_REMAINDER:
            case OP_EQUAL:
            case OP_NOT_EQUAL:
            case OP_LESS:
            case OP_LESS_EQUAL:
            case OP_GREATER:
            case OP_GREATER_EQUAL:
                if (stack_count < 2) {
                    vm_message(diagnostics, instruction, "stack underflow in binary operation");
                    final_result = PEBBLE_RUNTIME_ERROR;
                    break;
                }
                right = stack[--stack_count];
                left = stack[--stack_count];
                final_result = execute_binary(opcode, left, right, &value,
                                              diagnostics, instruction);
                if (final_result != PEBBLE_OK) break;
                stack[stack_count++] = value;
                break;
            case OP_JUMP:
                if (instruction->operand >= program->code_count) {
                    vm_message(diagnostics, instruction, "jump target out of range");
                    final_result = PEBBLE_RUNTIME_ERROR;
                    break;
                }
                instruction_pointer = instruction->operand;
                break;
            case OP_JUMP_IF_FALSE:
                if (instruction->operand >= program->code_count) {
                    vm_message(diagnostics, instruction, "jump target out of range");
                    final_result = PEBBLE_RUNTIME_ERROR;
                    break;
                }
                if (stack_count < 1) {
                    vm_message(diagnostics, instruction, "stack underflow in conditional jump");
                    final_result = PEBBLE_RUNTIME_ERROR;
                    break;
                }
                value = stack[--stack_count];
                if (value == 0) {
                    instruction_pointer = instruction->operand;
                }
                break;
            case OP_PRINT:
                if (stack_count < 1) {
                    vm_message(diagnostics, instruction, "stack underflow in print");
                    final_result = PEBBLE_RUNTIME_ERROR;
                    break;
                }
                value = stack[--stack_count];
                if (fprintf(output, "%" PRId64 "\n", value) < 0) {
                    vm_message(diagnostics, instruction, "output write failed");
                    final_result = PEBBLE_SYSTEM_ERROR;
                }
                break;
            case OP_HALT:
            default:
                vm_message(diagnostics, instruction, "unknown opcode");
                final_result = PEBBLE_RUNTIME_ERROR;
                break;
        }
        if (final_result != PEBBLE_OK) break;
    }
    free(locals);
    free(stack);
    return final_result;
}

PebbleResult pebble_run(const char *source, const PebbleOptions *options,
                        FILE *output, FILE *diagnostics) {
    PebbleProgram *program = NULL;
    PebbleResult result;
    if (source == NULL || output == NULL || diagnostics == NULL) return PEBBLE_SYSTEM_ERROR;
    result = pebble_compile(source, options, &program, diagnostics);
    if (result == PEBBLE_OK) result = pebble_execute(program, options, output, diagnostics);
    pebble_program_free(program);
    return result;
}
