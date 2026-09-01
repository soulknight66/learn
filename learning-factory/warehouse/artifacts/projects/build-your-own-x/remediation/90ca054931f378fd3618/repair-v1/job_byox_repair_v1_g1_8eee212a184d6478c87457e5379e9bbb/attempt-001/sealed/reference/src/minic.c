#include <ctype.h>
#include <errno.h>
#include <inttypes.h>
#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum {
    EXIT_USAGE_ERROR = 64,
    EXIT_SOURCE_ERROR = 65,
    EXIT_INPUT_ERROR = 66,
    EXIT_RUNTIME_ERROR = 70
};

enum {
    MAX_SOURCE_BYTES = 1048576,
    MAX_TOKENS = 65536,
    MAX_CODE = 65536,
    MAX_FUNCTIONS = 128,
    MAX_PARAMS = 32,
    MAX_LOCALS = 256,
    MAX_NAME = 63,
    MAX_PATCHES = 4096,
    MAX_VALUES = 8192,
    MAX_FRAMES = 256,
    MAX_EXPRESSION_NESTING = 512,
    MAX_STATEMENT_LEVELS = 512
};

typedef struct {
    char *bytes;
    size_t length;
    const char *path;
} Source;

typedef enum {
    TOK_EOF = 256,
    TOK_INTEGER,
    TOK_IDENT,
    TOK_INT,
    TOK_IF,
    TOK_ELSE,
    TOK_WHILE,
    TOK_RETURN,
    TOK_PRINT,
    TOK_EQ,
    TOK_NE,
    TOK_LE,
    TOK_GE,
    TOK_AND,
    TOK_OR
} TokenKind;

typedef struct {
    int kind;
    uint32_t start;
    uint32_t length;
    uint32_t line;
    int64_t value;
} Token;

typedef enum {
    OP_CONST,
    OP_LOAD,
    OP_STORE,
    OP_ADD,
    OP_SUB,
    OP_MUL,
    OP_DIV,
    OP_MOD,
    OP_NEG,
    OP_NOT,
    OP_BOOL,
    OP_EQ,
    OP_NE,
    OP_LT,
    OP_LE,
    OP_GT,
    OP_GE,
    OP_JZ,
    OP_JNZ,
    OP_JMP,
    OP_CALL,
    OP_RET,
    OP_POP,
    OP_PRINT
} OpCode;

typedef struct {
    int op;
    int arg;
    int64_t value;
    uint32_t line;
} Instruction;

typedef struct {
    char name[MAX_NAME + 1];
    int start;
    int arity;
    int local_count;
    uint32_t line;
} Function;

typedef struct {
    char name[MAX_NAME + 1];
    int slot;
} Local;

typedef struct {
    char name[MAX_NAME + 1];
    int instruction;
    int argument_count;
    uint32_t line;
} CallPatch;

typedef struct {
    const Source *source;
    Token tokens[MAX_TOKENS + 1];
    size_t token_count;
    size_t current;
    Instruction code[MAX_CODE];
    int code_count;
    Function functions[MAX_FUNCTIONS];
    int function_count;
    Local locals[MAX_LOCALS];
    int local_count;
    CallPatch patches[MAX_PATCHES];
    int patch_count;
    int expression_nesting;
    int statement_level;
    int failed;
} Compiler;

static void source_diagnostic(const Source *source, uint32_t line,
                              const char *message) {
    fprintf(stderr, "%s:%" PRIu32 ": %s\n", source->path, line, message);
}

static int load_source(const char *path, Source *source) {
    FILE *file = fopen(path, "rb");
    long length;
    size_t received;
    char *bytes;

    if (file == NULL) {
        fprintf(stderr, "%s: cannot open input (error %d)\n", path, errno);
        return EXIT_INPUT_ERROR;
    }
    if (fseek(file, 0, SEEK_END) != 0 || (length = ftell(file)) < 0 ||
        fseek(file, 0, SEEK_SET) != 0) {
        fprintf(stderr, "%s: cannot measure input\n", path);
        fclose(file);
        return EXIT_INPUT_ERROR;
    }
    if ((unsigned long)length > (unsigned long)MAX_SOURCE_BYTES) {
        fprintf(stderr, "%s: input exceeds %d bytes\n", path, MAX_SOURCE_BYTES);
        fclose(file);
        return EXIT_INPUT_ERROR;
    }
    bytes = (char *)malloc((size_t)length + 1);
    if (bytes == NULL) {
        fprintf(stderr, "%s: cannot allocate input buffer\n", path);
        fclose(file);
        return EXIT_INPUT_ERROR;
    }
    received = fread(bytes, 1, (size_t)length, file);
    if (received != (size_t)length || ferror(file)) {
        fprintf(stderr, "%s: cannot read input\n", path);
        free(bytes);
        fclose(file);
        return EXIT_INPUT_ERROR;
    }
    if (fclose(file) != 0) {
        fprintf(stderr, "%s: cannot close input after reading\n", path);
        free(bytes);
        return EXIT_INPUT_ERROR;
    }
    bytes[received] = '\0';
    source->bytes = bytes;
    source->length = received;
    source->path = path;
    return 0;
}

static int token_text_is(const Compiler *compiler, uint32_t start,
                         uint32_t length, const char *text) {
    size_t wanted = strlen(text);
    return wanted == length &&
           memcmp(compiler->source->bytes + start, text, length) == 0;
}

static int push_token(Compiler *compiler, int kind, size_t start, size_t length,
                      uint32_t line, int64_t value) {
    Token *token;
    if ((kind != TOK_EOF && compiler->token_count >= MAX_TOKENS) ||
        compiler->token_count > MAX_TOKENS) {
        source_diagnostic(compiler->source, line, "too many tokens");
        compiler->failed = 1;
        return 0;
    }
    token = &compiler->tokens[compiler->token_count++];
    token->kind = kind;
    token->start = (uint32_t)start;
    token->length = (uint32_t)length;
    token->line = line;
    token->value = value;
    return 1;
}

static int keyword_kind(const Compiler *compiler, size_t start, size_t length) {
    if (token_text_is(compiler, (uint32_t)start, (uint32_t)length, "int")) {
        return TOK_INT;
    }
    if (token_text_is(compiler, (uint32_t)start, (uint32_t)length, "if")) {
        return TOK_IF;
    }
    if (token_text_is(compiler, (uint32_t)start, (uint32_t)length, "else")) {
        return TOK_ELSE;
    }
    if (token_text_is(compiler, (uint32_t)start, (uint32_t)length, "while")) {
        return TOK_WHILE;
    }
    if (token_text_is(compiler, (uint32_t)start, (uint32_t)length, "return")) {
        return TOK_RETURN;
    }
    if (token_text_is(compiler, (uint32_t)start, (uint32_t)length, "print")) {
        return TOK_PRINT;
    }
    return TOK_IDENT;
}

static int lex_source(Compiler *compiler) {
    const char *bytes = compiler->source->bytes;
    size_t length = compiler->source->length;
    size_t pos = 0;
    uint32_t line = 1;

    while (pos < length) {
        unsigned char ch = (unsigned char)bytes[pos];
        size_t start;
        uint32_t start_line;

        if (ch == ' ' || ch == '\t' || ch == '\r' || ch == '\f' || ch == '\v') {
            pos++;
            continue;
        }
        if (ch == '\n') {
            line++;
            pos++;
            continue;
        }
        if (ch == '/' && pos + 1 < length && bytes[pos + 1] == '/') {
            pos += 2;
            while (pos < length && bytes[pos] != '\n') {
                pos++;
            }
            continue;
        }
        if (ch == '/' && pos + 1 < length && bytes[pos + 1] == '*') {
            start_line = line;
            pos += 2;
            while (pos + 1 < length && !(bytes[pos] == '*' && bytes[pos + 1] == '/')) {
                if (bytes[pos] == '\n') {
                    line++;
                }
                pos++;
            }
            if (pos + 1 >= length) {
                source_diagnostic(compiler->source, start_line,
                                  "unterminated block comment");
                compiler->failed = 1;
                return 0;
            }
            pos += 2;
            continue;
        }
        if (isalpha(ch) || ch == '_') {
            int kind;
            start = pos++;
            while (pos < length) {
                unsigned char next = (unsigned char)bytes[pos];
                if (!isalnum(next) && next != '_') {
                    break;
                }
                pos++;
            }
            if (pos - start > MAX_NAME) {
                source_diagnostic(compiler->source, line, "identifier exceeds 63 bytes");
                compiler->failed = 1;
                return 0;
            }
            kind = keyword_kind(compiler, start, pos - start);
            if (!push_token(compiler, kind, start, pos - start, line, 0)) {
                return 0;
            }
            continue;
        }
        if (isdigit(ch)) {
            uint64_t value = 0;
            start = pos;
            while (pos < length && isdigit((unsigned char)bytes[pos])) {
                unsigned digit = (unsigned)(bytes[pos] - '0');
                if (value > ((uint64_t)INT64_MAX - digit) / 10U) {
                    source_diagnostic(compiler->source, line,
                                      "integer literal exceeds INT64_MAX");
                    compiler->failed = 1;
                    return 0;
                }
                value = value * 10U + digit;
                pos++;
            }
            if (!push_token(compiler, TOK_INTEGER, start, pos - start, line,
                            (int64_t)value)) {
                return 0;
            }
            continue;
        }

        start = pos;
        if (pos + 1 < length) {
            int kind = 0;
            if (ch == '=' && bytes[pos + 1] == '=') kind = TOK_EQ;
            else if (ch == '!' && bytes[pos + 1] == '=') kind = TOK_NE;
            else if (ch == '<' && bytes[pos + 1] == '=') kind = TOK_LE;
            else if (ch == '>' && bytes[pos + 1] == '=') kind = TOK_GE;
            else if (ch == '&' && bytes[pos + 1] == '&') kind = TOK_AND;
            else if (ch == '|' && bytes[pos + 1] == '|') kind = TOK_OR;
            if (kind != 0) {
                pos += 2;
                if (!push_token(compiler, kind, start, 2, line, 0)) return 0;
                continue;
            }
        }
        if (strchr("+-*/%!=<>(){},;", (int)ch) != NULL) {
            pos++;
            if (!push_token(compiler, (int)ch, start, 1, line, 0)) return 0;
            continue;
        }
        {
            char message[80];
            snprintf(message, sizeof(message), "unexpected byte 0x%02x", (unsigned)ch);
            source_diagnostic(compiler->source, line, message);
        }
        compiler->failed = 1;
        return 0;
    }
    return push_token(compiler, TOK_EOF, length, 0, line, 0);
}

static Token *current_token(Compiler *compiler) {
    return &compiler->tokens[compiler->current];
}

static Token *previous_token(Compiler *compiler) {
    return &compiler->tokens[compiler->current - 1];
}

static int check(Compiler *compiler, int kind) {
    return current_token(compiler)->kind == kind;
}

static int check_next(Compiler *compiler, int kind) {
    if (compiler->current + 1 >= compiler->token_count) return 0;
    return compiler->tokens[compiler->current + 1].kind == kind;
}

static int match(Compiler *compiler, int kind) {
    if (!check(compiler, kind)) return 0;
    compiler->current++;
    return 1;
}

static void parser_error(Compiler *compiler, const Token *token, const char *message) {
    if (!compiler->failed) {
        source_diagnostic(compiler->source, token->line, message);
    }
    compiler->failed = 1;
}

static Token *expect(Compiler *compiler, int kind, const char *message) {
    Token *token = current_token(compiler);
    if (token->kind != kind) {
        parser_error(compiler, token, message);
        return token;
    }
    compiler->current++;
    return token;
}

static void copy_token_name(const Compiler *compiler, const Token *token,
                            char output[MAX_NAME + 1]) {
    memcpy(output, compiler->source->bytes + token->start, token->length);
    output[token->length] = '\0';
}

static int names_equal_token(const Compiler *compiler, const char *name,
                             const Token *token) {
    size_t length = strlen(name);
    return length == token->length &&
           memcmp(name, compiler->source->bytes + token->start, length) == 0;
}

static int emit(Compiler *compiler, int op, int arg, int64_t value, uint32_t line) {
    Instruction *instruction;
    if (compiler->code_count >= MAX_CODE) {
        source_diagnostic(compiler->source, line, "too many bytecode instructions");
        compiler->failed = 1;
        return -1;
    }
    instruction = &compiler->code[compiler->code_count];
    instruction->op = op;
    instruction->arg = arg;
    instruction->value = value;
    instruction->line = line;
    return compiler->code_count++;
}

static void patch_jump(Compiler *compiler, int instruction, int target) {
    if (instruction >= 0 && instruction < compiler->code_count) {
        compiler->code[instruction].arg = target;
    }
}

static int find_local(const Compiler *compiler, const Token *name) {
    int i;
    for (i = compiler->local_count - 1; i >= 0; i--) {
        if (names_equal_token(compiler, compiler->locals[i].name, name)) {
            return compiler->locals[i].slot;
        }
    }
    return -1;
}

static int add_local(Compiler *compiler, const Token *name) {
    Local *local;
    if (find_local(compiler, name) >= 0) {
        parser_error(compiler, name, "duplicate local or parameter name");
        return -1;
    }
    if (compiler->local_count >= MAX_LOCALS) {
        parser_error(compiler, name, "too many locals in function");
        return -1;
    }
    local = &compiler->locals[compiler->local_count];
    copy_token_name(compiler, name, local->name);
    local->slot = compiler->local_count;
    compiler->local_count++;
    return local->slot;
}

static void parse_expression(Compiler *compiler);
static void parse_statement(Compiler *compiler);

static int enter_expression_nesting(Compiler *compiler, const Token *token) {
    if (compiler->expression_nesting >= MAX_EXPRESSION_NESTING) {
        parser_error(compiler, token, "expression nesting exceeds 512");
        return 0;
    }
    compiler->expression_nesting++;
    return 1;
}

static void add_call_patch(Compiler *compiler, const Token *name,
                           int instruction, int argument_count) {
    CallPatch *patch;
    if (compiler->patch_count >= MAX_PATCHES) {
        parser_error(compiler, name, "too many function calls");
        return;
    }
    patch = &compiler->patches[compiler->patch_count++];
    copy_token_name(compiler, name, patch->name);
    patch->instruction = instruction;
    patch->argument_count = argument_count;
    patch->line = name->line;
}

static void parse_primary(Compiler *compiler) {
    if (match(compiler, TOK_INTEGER)) {
        Token *literal = previous_token(compiler);
        (void)emit(compiler, OP_CONST, 0, literal->value, literal->line);
        return;
    }
    if (match(compiler, TOK_IDENT)) {
        Token *name = previous_token(compiler);
        if (match(compiler, '(')) {
            int argument_count = 0;
            int instruction;
            if (!check(compiler, ')')) {
                do {
                    if (argument_count >= MAX_PARAMS) {
                        parser_error(compiler, current_token(compiler),
                                     "too many call arguments");
                        return;
                    }
                    if (!enter_expression_nesting(compiler, current_token(compiler))) {
                        return;
                    }
                    parse_expression(compiler);
                    compiler->expression_nesting--;
                    argument_count++;
                } while (match(compiler, ','));
            }
            (void)expect(compiler, ')', "expected ')' after arguments");
            instruction = emit(compiler, OP_CALL, -1, 0, name->line);
            add_call_patch(compiler, name, instruction, argument_count);
            return;
        }
        {
            int slot = find_local(compiler, name);
            if (slot < 0) {
                parser_error(compiler, name, "undefined local name");
                return;
            }
            (void)emit(compiler, OP_LOAD, slot, 0, name->line);
            return;
        }
    }
    if (match(compiler, '(')) {
        Token *opening = previous_token(compiler);
        if (!enter_expression_nesting(compiler, opening)) {
            return;
        }
        parse_expression(compiler);
        compiler->expression_nesting--;
        (void)expect(compiler, ')', "expected ')' after expression");
        return;
    }
    parser_error(compiler, current_token(compiler), "expected expression");
    if (!check(compiler, TOK_EOF)) compiler->current++;
}

static void parse_unary(Compiler *compiler) {
    size_t first = compiler->current;
    size_t after_prefix;
    size_t index;

    while (match(compiler, '!') || match(compiler, '-')) {
        /* Prefix operators are emitted in reverse after their primary. */
    }
    after_prefix = compiler->current;
    parse_primary(compiler);
    for (index = after_prefix; index > first; index--) {
        Token *operator_token = &compiler->tokens[index - 1];
        int op = operator_token->kind == '!' ? OP_NOT : OP_NEG;
        (void)emit(compiler, op, 0, 0, operator_token->line);
    }
}

static void parse_factor(Compiler *compiler) {
    parse_unary(compiler);
    while (check(compiler, '*') || check(compiler, '/') || check(compiler, '%')) {
        int kind = current_token(compiler)->kind;
        uint32_t line = current_token(compiler)->line;
        compiler->current++;
        parse_unary(compiler);
        if (kind == '*') (void)emit(compiler, OP_MUL, 0, 0, line);
        else if (kind == '/') (void)emit(compiler, OP_DIV, 0, 0, line);
        else (void)emit(compiler, OP_MOD, 0, 0, line);
    }
}

static void parse_term(Compiler *compiler) {
    parse_factor(compiler);
    while (check(compiler, '+') || check(compiler, '-')) {
        int kind = current_token(compiler)->kind;
        uint32_t line = current_token(compiler)->line;
        compiler->current++;
        parse_factor(compiler);
        (void)emit(compiler, kind == '+' ? OP_ADD : OP_SUB, 0, 0, line);
    }
}

static void parse_comparison(Compiler *compiler) {
    parse_term(compiler);
    while (check(compiler, '<') || check(compiler, TOK_LE) ||
           check(compiler, '>') || check(compiler, TOK_GE)) {
        int kind = current_token(compiler)->kind;
        uint32_t line = current_token(compiler)->line;
        int op;
        compiler->current++;
        parse_term(compiler);
        if (kind == '<') op = OP_LT;
        else if (kind == TOK_LE) op = OP_LE;
        else if (kind == '>') op = OP_GT;
        else op = OP_GE;
        (void)emit(compiler, op, 0, 0, line);
    }
}

static void parse_equality(Compiler *compiler) {
    parse_comparison(compiler);
    while (check(compiler, TOK_EQ) || check(compiler, TOK_NE)) {
        int kind = current_token(compiler)->kind;
        uint32_t line = current_token(compiler)->line;
        compiler->current++;
        parse_comparison(compiler);
        (void)emit(compiler, kind == TOK_EQ ? OP_EQ : OP_NE, 0, 0, line);
    }
}

static void parse_logical_and(Compiler *compiler) {
    parse_equality(compiler);
    while (match(compiler, TOK_AND)) {
        uint32_t line = previous_token(compiler)->line;
        int false_jump = emit(compiler, OP_JZ, -1, 0, line);
        int end_jump;
        parse_equality(compiler);
        (void)emit(compiler, OP_BOOL, 0, 0, line);
        end_jump = emit(compiler, OP_JMP, -1, 0, line);
        patch_jump(compiler, false_jump, compiler->code_count);
        (void)emit(compiler, OP_CONST, 0, 0, line);
        patch_jump(compiler, end_jump, compiler->code_count);
    }
}

static void parse_logical_or(Compiler *compiler) {
    parse_logical_and(compiler);
    while (match(compiler, TOK_OR)) {
        uint32_t line = previous_token(compiler)->line;
        int true_jump = emit(compiler, OP_JNZ, -1, 0, line);
        int end_jump;
        parse_logical_and(compiler);
        (void)emit(compiler, OP_BOOL, 0, 0, line);
        end_jump = emit(compiler, OP_JMP, -1, 0, line);
        patch_jump(compiler, true_jump, compiler->code_count);
        (void)emit(compiler, OP_CONST, 0, 1, line);
        patch_jump(compiler, end_jump, compiler->code_count);
    }
}

static void parse_expression(Compiler *compiler) {
    parse_logical_or(compiler);
}

static void parse_block_body(Compiler *compiler) {
    while (!check(compiler, '}') && !check(compiler, TOK_EOF) &&
           !compiler->failed) {
        parse_statement(compiler);
    }
    (void)expect(compiler, '}', "expected '}' after block");
}

static void parse_declaration(Compiler *compiler, uint32_t line) {
    Token *name = expect(compiler, TOK_IDENT, "expected local name after 'int'");
    int slot;
    if (compiler->failed) return;
    slot = add_local(compiler, name);
    if (match(compiler, '=')) {
        parse_expression(compiler);
    } else {
        (void)emit(compiler, OP_CONST, 0, 0, line);
    }
    (void)emit(compiler, OP_STORE, slot, 0, line);
    (void)expect(compiler, ';', "expected ';' after declaration");
}

static void parse_if_statement(Compiler *compiler, uint32_t line) {
    int false_jump;
    (void)expect(compiler, '(', "expected '(' after 'if'");
    parse_expression(compiler);
    (void)expect(compiler, ')', "expected ')' after if condition");
    false_jump = emit(compiler, OP_JZ, -1, 0, line);
    parse_statement(compiler);
    if (match(compiler, TOK_ELSE)) {
        int end_jump = emit(compiler, OP_JMP, -1, 0, line);
        patch_jump(compiler, false_jump, compiler->code_count);
        parse_statement(compiler);
        patch_jump(compiler, end_jump, compiler->code_count);
    } else {
        patch_jump(compiler, false_jump, compiler->code_count);
    }
}

static void parse_while_statement(Compiler *compiler, uint32_t line) {
    int loop_start = compiler->code_count;
    int exit_jump;
    (void)expect(compiler, '(', "expected '(' after 'while'");
    parse_expression(compiler);
    (void)expect(compiler, ')', "expected ')' after while condition");
    exit_jump = emit(compiler, OP_JZ, -1, 0, line);
    parse_statement(compiler);
    (void)emit(compiler, OP_JMP, loop_start, 0, line);
    patch_jump(compiler, exit_jump, compiler->code_count);
}

static void parse_statement_body(Compiler *compiler);

static void parse_statement(Compiler *compiler) {
    if (compiler->statement_level >= MAX_STATEMENT_LEVELS) {
        parser_error(compiler, current_token(compiler),
                     "statement nesting exceeds 512 levels");
        return;
    }
    compiler->statement_level++;
    parse_statement_body(compiler);
    compiler->statement_level--;
}

static void parse_statement_body(Compiler *compiler) {
    if (match(compiler, '{')) {
        parse_block_body(compiler);
        return;
    }
    if (match(compiler, TOK_INT)) {
        parse_declaration(compiler, previous_token(compiler)->line);
        return;
    }
    if (match(compiler, TOK_IF)) {
        parse_if_statement(compiler, previous_token(compiler)->line);
        return;
    }
    if (match(compiler, TOK_WHILE)) {
        parse_while_statement(compiler, previous_token(compiler)->line);
        return;
    }
    if (match(compiler, TOK_RETURN)) {
        uint32_t line = previous_token(compiler)->line;
        parse_expression(compiler);
        (void)expect(compiler, ';', "expected ';' after return value");
        (void)emit(compiler, OP_RET, 0, 0, line);
        return;
    }
    if (match(compiler, TOK_PRINT)) {
        uint32_t line = previous_token(compiler)->line;
        (void)expect(compiler, '(', "expected '(' after 'print'");
        parse_expression(compiler);
        (void)expect(compiler, ')', "expected ')' after print argument");
        (void)expect(compiler, ';', "expected ';' after print statement");
        (void)emit(compiler, OP_PRINT, 0, 0, line);
        return;
    }
    if (check(compiler, TOK_IDENT) && check_next(compiler, '=')) {
        Token *name = current_token(compiler);
        int slot = find_local(compiler, name);
        uint32_t line = name->line;
        compiler->current += 2;
        if (slot < 0) {
            parser_error(compiler, name, "assignment to undefined local");
            return;
        }
        parse_expression(compiler);
        (void)expect(compiler, ';', "expected ';' after assignment");
        (void)emit(compiler, OP_STORE, slot, 0, line);
        return;
    }
    {
        uint32_t line = current_token(compiler)->line;
        parse_expression(compiler);
        (void)expect(compiler, ';', "expected ';' after expression");
        (void)emit(compiler, OP_POP, 0, 0, line);
    }
}

static int find_function_by_token(const Compiler *compiler, const Token *name) {
    int i;
    for (i = 0; i < compiler->function_count; i++) {
        if (names_equal_token(compiler, compiler->functions[i].name, name)) return i;
    }
    return -1;
}

static int find_function_by_name(const Compiler *compiler, const char *name) {
    int i;
    for (i = 0; i < compiler->function_count; i++) {
        if (strcmp(compiler->functions[i].name, name) == 0) return i;
    }
    return -1;
}

static void parse_function(Compiler *compiler) {
    Token *name;
    Function *function;
    int function_index;

    (void)expect(compiler, TOK_INT, "expected 'int' at function definition");
    name = expect(compiler, TOK_IDENT, "expected function name");
    if (compiler->failed) return;
    if (find_function_by_token(compiler, name) >= 0) {
        parser_error(compiler, name, "duplicate function definition");
        return;
    }
    if (compiler->function_count >= MAX_FUNCTIONS) {
        parser_error(compiler, name, "too many functions");
        return;
    }
    function_index = compiler->function_count++;
    function = &compiler->functions[function_index];
    copy_token_name(compiler, name, function->name);
    function->line = name->line;
    compiler->local_count = 0;

    (void)expect(compiler, '(', "expected '(' after function name");
    if (!check(compiler, ')')) {
        do {
            Token *parameter;
            if (compiler->local_count >= MAX_PARAMS) {
                parser_error(compiler, current_token(compiler),
                             "too many function parameters");
                return;
            }
            (void)expect(compiler, TOK_INT, "expected 'int' before parameter");
            parameter = expect(compiler, TOK_IDENT, "expected parameter name");
            if (compiler->failed) return;
            (void)add_local(compiler, parameter);
        } while (match(compiler, ','));
    }
    (void)expect(compiler, ')', "expected ')' after parameters");
    function->arity = compiler->local_count;
    function->start = compiler->code_count;
    (void)expect(compiler, '{', "expected '{' before function body");
    parse_block_body(compiler);
    (void)emit(compiler, OP_CONST, 0, 0, name->line);
    (void)emit(compiler, OP_RET, 0, 0, name->line);
    function->local_count = compiler->local_count;
}

static void resolve_calls(Compiler *compiler) {
    int i;
    for (i = 0; i < compiler->patch_count && !compiler->failed; i++) {
        CallPatch *patch = &compiler->patches[i];
        int function_index = find_function_by_name(compiler, patch->name);
        if (function_index < 0) {
            char message[128];
            snprintf(message, sizeof(message), "undefined function '%s'", patch->name);
            source_diagnostic(compiler->source, patch->line, message);
            compiler->failed = 1;
        } else if (compiler->functions[function_index].arity != patch->argument_count) {
            char message[160];
            snprintf(message, sizeof(message),
                     "function '%s' expects %d arguments but call has %d",
                     patch->name, compiler->functions[function_index].arity,
                     patch->argument_count);
            source_diagnostic(compiler->source, patch->line, message);
            compiler->failed = 1;
        } else if (patch->instruction >= 0 && patch->instruction < compiler->code_count) {
            compiler->code[patch->instruction].arg = function_index;
        }
    }
}

static int compile_source(Compiler *compiler) {
    int main_index;
    while (!check(compiler, TOK_EOF) && !compiler->failed) {
        parse_function(compiler);
    }
    if (compiler->failed) return 0;
    resolve_calls(compiler);
    if (compiler->failed) return 0;
    main_index = find_function_by_name(compiler, "main");
    if (main_index < 0) {
        source_diagnostic(compiler->source, 1, "missing function 'main'");
        compiler->failed = 1;
        return 0;
    }
    if (compiler->functions[main_index].arity != 0) {
        source_diagnostic(compiler->source, compiler->functions[main_index].line,
                          "function 'main' must have zero parameters");
        compiler->failed = 1;
        return 0;
    }
    return 1;
}

typedef struct {
    int function_index;
    int return_ip;
    int base_sp;
    int64_t locals[MAX_LOCALS];
} Frame;

typedef struct {
    const Compiler *compiler;
    int64_t values[MAX_VALUES];
    int value_count;
    Frame frames[MAX_FRAMES];
    int frame_count;
    int ip;
    uint64_t steps;
    uint64_t max_steps;
} Machine;

static int runtime_error(const Machine *machine, uint32_t line, const char *message) {
    source_diagnostic(machine->compiler->source, line, message);
    return EXIT_RUNTIME_ERROR;
}

static int push_value(Machine *machine, int64_t value, uint32_t line) {
    if (machine->value_count >= MAX_VALUES) {
        (void)runtime_error(machine, line, "operand stack capacity exceeded");
        return 0;
    }
    machine->values[machine->value_count++] = value;
    return 1;
}

static int pop_value(Machine *machine, int64_t *value, uint32_t line) {
    if (machine->value_count <= 0) {
        (void)runtime_error(machine, line, "operand stack underflow");
        return 0;
    }
    *value = machine->values[--machine->value_count];
    return 1;
}

static int checked_add(int64_t left, int64_t right, int64_t *result) {
    if ((right > 0 && left > INT64_MAX - right) ||
        (right < 0 && left < INT64_MIN - right)) return 0;
    *result = left + right;
    return 1;
}

static int checked_sub(int64_t left, int64_t right, int64_t *result) {
    if ((right > 0 && left < INT64_MIN + right) ||
        (right < 0 && left > INT64_MAX + right)) return 0;
    *result = left - right;
    return 1;
}

static int checked_mul(int64_t left, int64_t right, int64_t *result) {
    if (left > 0) {
        if (right > 0 && left > INT64_MAX / right) return 0;
        if (right < 0 && right < INT64_MIN / left) return 0;
    } else if (left < 0) {
        if (right > 0 && left < INT64_MIN / right) return 0;
        if (right < 0 && left < INT64_MAX / right) return 0;
    }
    *result = left * right;
    return 1;
}

static int run_machine(const Compiler *compiler, int main_index, uint64_t max_steps) {
    Machine *machine = (Machine *)calloc(1, sizeof(*machine));
    int status = 0;
    if (machine == NULL) {
        fprintf(stderr, "%s:1: cannot allocate virtual machine\n",
                compiler->source->path);
        return EXIT_RUNTIME_ERROR;
    }
    machine->compiler = compiler;
    machine->frame_count = 1;
    machine->frames[0].function_index = main_index;
    machine->frames[0].return_ip = -1;
    machine->frames[0].base_sp = 0;
    machine->ip = compiler->functions[main_index].start;
    machine->max_steps = max_steps;

    for (;;) {
        Instruction instruction;
        Frame *frame;
        int64_t left = 0;
        int64_t right = 0;
        int64_t result = 0;

        if (machine->ip < 0 || machine->ip >= compiler->code_count) {
            status = runtime_error(machine, 1, "invalid instruction pointer");
            break;
        }
        instruction = compiler->code[machine->ip];
        if (machine->steps >= machine->max_steps) {
            status = runtime_error(machine, instruction.line, "step limit exceeded");
            break;
        }
        machine->steps++;
        machine->ip++;
        frame = &machine->frames[machine->frame_count - 1];

        switch (instruction.op) {
        case OP_CONST:
            if (!push_value(machine, instruction.value, instruction.line)) {
                status = EXIT_RUNTIME_ERROR;
            }
            break;
        case OP_LOAD:
            if (instruction.arg < 0 ||
                instruction.arg >= compiler->functions[frame->function_index].local_count) {
                status = runtime_error(machine, instruction.line, "invalid local load");
            } else if (!push_value(machine, frame->locals[instruction.arg], instruction.line)) {
                status = EXIT_RUNTIME_ERROR;
            }
            break;
        case OP_STORE:
            if (instruction.arg < 0 ||
                instruction.arg >= compiler->functions[frame->function_index].local_count) {
                status = runtime_error(machine, instruction.line, "invalid local store");
            } else if (!pop_value(machine, &result, instruction.line)) {
                status = EXIT_RUNTIME_ERROR;
            } else {
                frame->locals[instruction.arg] = result;
            }
            break;
        case OP_ADD:
        case OP_SUB:
        case OP_MUL:
        case OP_DIV:
        case OP_MOD:
            if (!pop_value(machine, &right, instruction.line) ||
                !pop_value(machine, &left, instruction.line)) {
                status = EXIT_RUNTIME_ERROR;
                break;
            }
            if (instruction.op == OP_ADD) {
                if (!checked_add(left, right, &result))
                    status = runtime_error(machine, instruction.line, "addition overflow");
            } else if (instruction.op == OP_SUB) {
                if (!checked_sub(left, right, &result))
                    status = runtime_error(machine, instruction.line, "subtraction overflow");
            } else if (instruction.op == OP_MUL) {
                if (!checked_mul(left, right, &result))
                    status = runtime_error(machine, instruction.line, "multiplication overflow");
            } else if (right == 0) {
                status = runtime_error(machine, instruction.line,
                                       instruction.op == OP_DIV ? "division by zero" :
                                                                  "remainder by zero");
            } else if (left == INT64_MIN && right == -1) {
                status = runtime_error(machine, instruction.line,
                                       instruction.op == OP_DIV ? "division overflow" :
                                                                  "remainder overflow");
            } else if (instruction.op == OP_DIV) {
                result = left / right;
            } else {
                result = left % right;
            }
            if (status == 0 && !push_value(machine, result, instruction.line))
                status = EXIT_RUNTIME_ERROR;
            break;
        case OP_NEG:
            if (!pop_value(machine, &left, instruction.line)) {
                status = EXIT_RUNTIME_ERROR;
            } else if (left == INT64_MIN) {
                status = runtime_error(machine, instruction.line, "negation overflow");
            } else if (!push_value(machine, -left, instruction.line)) {
                status = EXIT_RUNTIME_ERROR;
            }
            break;
        case OP_NOT:
        case OP_BOOL:
            if (!pop_value(machine, &left, instruction.line)) {
                status = EXIT_RUNTIME_ERROR;
            } else {
                result = instruction.op == OP_NOT ? (left == 0) : (left != 0);
                if (!push_value(machine, result, instruction.line))
                    status = EXIT_RUNTIME_ERROR;
            }
            break;
        case OP_EQ:
        case OP_NE:
        case OP_LT:
        case OP_LE:
        case OP_GT:
        case OP_GE:
            if (!pop_value(machine, &right, instruction.line) ||
                !pop_value(machine, &left, instruction.line)) {
                status = EXIT_RUNTIME_ERROR;
                break;
            }
            if (instruction.op == OP_EQ) result = left == right;
            else if (instruction.op == OP_NE) result = left != right;
            else if (instruction.op == OP_LT) result = left < right;
            else if (instruction.op == OP_LE) result = left <= right;
            else if (instruction.op == OP_GT) result = left > right;
            else result = left >= right;
            if (!push_value(machine, result, instruction.line)) status = EXIT_RUNTIME_ERROR;
            break;
        case OP_JZ:
        case OP_JNZ:
            if (!pop_value(machine, &left, instruction.line)) {
                status = EXIT_RUNTIME_ERROR;
            } else if ((instruction.op == OP_JZ && left == 0) ||
                       (instruction.op == OP_JNZ && left != 0)) {
                if (instruction.arg < 0 || instruction.arg >= compiler->code_count) {
                    status = runtime_error(machine, instruction.line, "invalid jump target");
                } else {
                    machine->ip = instruction.arg;
                }
            }
            break;
        case OP_JMP:
            if (instruction.arg < 0 || instruction.arg >= compiler->code_count) {
                status = runtime_error(machine, instruction.line, "invalid jump target");
            } else {
                machine->ip = instruction.arg;
            }
            break;
        case OP_CALL:
            if (instruction.arg < 0 || instruction.arg >= compiler->function_count) {
                status = runtime_error(machine, instruction.line, "invalid call target");
            } else {
                const Function *callee_function = &compiler->functions[instruction.arg];
                Frame *callee;
                int base;
                int i;
                if (machine->frame_count >= MAX_FRAMES) {
                    status = runtime_error(machine, instruction.line,
                                           "function frame capacity exceeded");
                    break;
                }
                if (machine->value_count < callee_function->arity) {
                    status = runtime_error(machine, instruction.line,
                                           "operand stack underflow at call");
                    break;
                }
                base = machine->value_count - callee_function->arity;
                callee = &machine->frames[machine->frame_count++];
                memset(callee, 0, sizeof(*callee));
                callee->function_index = instruction.arg;
                callee->return_ip = machine->ip;
                callee->base_sp = base;
                for (i = 0; i < callee_function->arity; i++) {
                    callee->locals[i] = machine->values[base + i];
                }
                machine->value_count = base;
                machine->ip = callee_function->start;
            }
            break;
        case OP_RET:
            if (!pop_value(machine, &result, instruction.line)) {
                status = EXIT_RUNTIME_ERROR;
            } else if (machine->frame_count == 1) {
                status = 0;
                goto finished;
            } else {
                int base = frame->base_sp;
                int return_ip = frame->return_ip;
                machine->frame_count--;
                machine->value_count = base;
                if (!push_value(machine, result, instruction.line)) {
                    status = EXIT_RUNTIME_ERROR;
                } else {
                    machine->ip = return_ip;
                }
            }
            break;
        case OP_POP:
            if (!pop_value(machine, &result, instruction.line)) status = EXIT_RUNTIME_ERROR;
            break;
        case OP_PRINT:
            if (!pop_value(machine, &result, instruction.line)) {
                status = EXIT_RUNTIME_ERROR;
            } else if (printf("%" PRId64 "\n", result) < 0) {
                status = runtime_error(machine, instruction.line, "cannot write output");
            }
            break;
        default:
            status = runtime_error(machine, instruction.line, "unknown bytecode opcode");
            break;
        }
        if (status != 0) break;
    }

finished:
    free(machine);
    return status;
}

static int parse_positive_u64(const char *text, uint64_t *result) {
    uint64_t value = 0;
    const unsigned char *cursor = (const unsigned char *)text;
    if (*cursor == '\0') return 0;
    while (*cursor != '\0') {
        unsigned digit;
        if (*cursor < '0' || *cursor > '9') return 0;
        digit = (unsigned)(*cursor - '0');
        if (value > (UINT64_MAX - digit) / UINT64_C(10)) return 0;
        value = value * UINT64_C(10) + digit;
        cursor++;
    }
    if (value == 0) return 0;
    *result = value;
    return 1;
}

static int usage(const char *program) {
    fprintf(stderr, "usage: %s [--max-steps N] SOURCE\n", program);
    return EXIT_USAGE_ERROR;
}

int main(int argc, char **argv) {
    uint64_t max_steps = UINT64_C(1000000);
    const char *path;
    Source source;
    Compiler *compiler;
    int main_index;
    int status;

    if (argc == 2 && strncmp(argv[1], "--", 2) != 0) {
        path = argv[1];
    } else if (argc == 4 && strcmp(argv[1], "--max-steps") == 0) {
        if (!parse_positive_u64(argv[2], &max_steps)) return usage(argv[0]);
        path = argv[3];
    } else {
        return usage(argv[0]);
    }

    status = load_source(path, &source);
    if (status != 0) return status;
    compiler = (Compiler *)calloc(1, sizeof(*compiler));
    if (compiler == NULL) {
        fprintf(stderr, "%s:1: cannot allocate compiler\n", path);
        free(source.bytes);
        return EXIT_INPUT_ERROR;
    }
    compiler->source = &source;
    if (!lex_source(compiler) || !compile_source(compiler)) {
        status = EXIT_SOURCE_ERROR;
    } else {
        main_index = find_function_by_name(compiler, "main");
        status = run_machine(compiler, main_index, max_steps);
    }
    free(compiler);
    free(source.bytes);
    return status;
}
