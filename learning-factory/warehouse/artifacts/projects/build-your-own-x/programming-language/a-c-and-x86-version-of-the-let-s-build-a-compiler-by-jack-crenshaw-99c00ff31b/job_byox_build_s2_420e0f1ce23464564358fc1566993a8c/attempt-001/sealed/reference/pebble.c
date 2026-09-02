#include "pebble.h"

#include <errno.h>
#include <inttypes.h>
#include <limits.h>
#include <stdarg.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define MAX_SOURCE_BYTES (1024u * 1024u)
#define MAX_VARIABLES 256u
#define MAX_NESTING 128u
#define DEFAULT_STEPS UINT64_C(1000000)

typedef struct {
    uint32_t line;
    uint32_t column;
} Location;

typedef enum {
    TOK_ERROR,
    TOK_EOF,
    TOK_INTEGER,
    TOK_IDENTIFIER,
    TOK_LET,
    TOK_PRINT,
    TOK_IF,
    TOK_ELSE,
    TOK_WHILE,
    TOK_LPAREN,
    TOK_RPAREN,
    TOK_LBRACE,
    TOK_RBRACE,
    TOK_SEMICOLON,
    TOK_ASSIGN,
    TOK_PLUS,
    TOK_MINUS,
    TOK_STAR,
    TOK_SLASH,
    TOK_PERCENT,
    TOK_BANG,
    TOK_EQUAL_EQUAL,
    TOK_BANG_EQUAL,
    TOK_LESS,
    TOK_LESS_EQUAL,
    TOK_GREATER,
    TOK_GREATER_EQUAL
} TokenKind;

typedef struct {
    TokenKind kind;
    const char *begin;
    size_t length;
    int64_t integer;
    Location location;
} Token;

typedef struct {
    const char *source;
    size_t length;
    size_t offset;
    uint32_t line;
    uint32_t column;
    char error[96];
} Lexer;

static bool ascii_letter(unsigned char byte) {
    return (byte >= 'a' && byte <= 'z') ||
           (byte >= 'A' && byte <= 'Z') || byte == '_';
}

static bool ascii_digit(unsigned char byte) {
    return byte >= '0' && byte <= '9';
}

static void lexer_advance(Lexer *lexer) {
    unsigned char byte = (unsigned char)lexer->source[lexer->offset++];
    if (byte == '\n') {
        lexer->line++;
        lexer->column = 1;
    } else {
        lexer->column++;
    }
}

static void lexer_init(Lexer *lexer, const char *source, size_t length) {
    lexer->source = source;
    lexer->length = length;
    lexer->offset = 0;
    lexer->line = 1;
    lexer->column = 1;
    lexer->error[0] = '\0';
}

static Token token_at(Lexer *lexer, TokenKind kind, size_t start,
                      Location location) {
    Token token;
    token.kind = kind;
    token.begin = lexer->source + start;
    token.length = lexer->offset - start;
    token.integer = 0;
    token.location = location;
    return token;
}

static bool token_text_is(const char *text, size_t length, const char *word) {
    return strlen(word) == length && memcmp(text, word, length) == 0;
}

static TokenKind identifier_kind(const char *text, size_t length) {
    if (token_text_is(text, length, "let")) {
        return TOK_LET;
    }
    if (token_text_is(text, length, "print")) {
        return TOK_PRINT;
    }
    if (token_text_is(text, length, "if")) {
        return TOK_IF;
    }
    if (token_text_is(text, length, "else")) {
        return TOK_ELSE;
    }
    if (token_text_is(text, length, "while")) {
        return TOK_WHILE;
    }
    return TOK_IDENTIFIER;
}

static Token lexer_next(Lexer *lexer) {
    size_t start;
    Location location;
    unsigned char byte;
    Token token;

    for (;;) {
        while (lexer->offset < lexer->length) {
            byte = (unsigned char)lexer->source[lexer->offset];
            if (byte == ' ' || byte == '\t' || byte == '\r' || byte == '\n') {
                lexer_advance(lexer);
            } else {
                break;
            }
        }
        if (lexer->offset < lexer->length && lexer->source[lexer->offset] == '#') {
            while (lexer->offset < lexer->length &&
                   lexer->source[lexer->offset] != '\n') {
                lexer_advance(lexer);
            }
            continue;
        }
        break;
    }

    start = lexer->offset;
    location.line = lexer->line;
    location.column = lexer->column;
    if (lexer->offset == lexer->length) {
        return token_at(lexer, TOK_EOF, start, location);
    }

    byte = (unsigned char)lexer->source[lexer->offset];
    if (ascii_letter(byte)) {
        lexer_advance(lexer);
        while (lexer->offset < lexer->length) {
            byte = (unsigned char)lexer->source[lexer->offset];
            if (!ascii_letter(byte) && !ascii_digit(byte)) {
                break;
            }
            lexer_advance(lexer);
        }
        token = token_at(lexer, TOK_IDENTIFIER, start, location);
        token.kind = identifier_kind(token.begin, token.length);
        return token;
    }

    if (ascii_digit(byte)) {
        uint64_t value = 0;
        bool overflow = false;
        do {
            unsigned digit = (unsigned)(lexer->source[lexer->offset] - '0');
            if (value > ((uint64_t)INT64_MAX - digit) / UINT64_C(10)) {
                overflow = true;
            } else if (!overflow) {
                value = value * UINT64_C(10) + digit;
            }
            lexer_advance(lexer);
        } while (lexer->offset < lexer->length &&
                 ascii_digit((unsigned char)lexer->source[lexer->offset]));
        token = token_at(lexer, overflow ? TOK_ERROR : TOK_INTEGER, start, location);
        token.integer = (int64_t)value;
        if (overflow) {
            snprintf(lexer->error, sizeof(lexer->error),
                     "integer literal exceeds signed 64-bit range");
        }
        return token;
    }

    lexer_advance(lexer);
    switch (byte) {
        case '(':
            return token_at(lexer, TOK_LPAREN, start, location);
        case ')':
            return token_at(lexer, TOK_RPAREN, start, location);
        case '{':
            return token_at(lexer, TOK_LBRACE, start, location);
        case '}':
            return token_at(lexer, TOK_RBRACE, start, location);
        case ';':
            return token_at(lexer, TOK_SEMICOLON, start, location);
        case '+':
            return token_at(lexer, TOK_PLUS, start, location);
        case '-':
            return token_at(lexer, TOK_MINUS, start, location);
        case '*':
            return token_at(lexer, TOK_STAR, start, location);
        case '/':
            return token_at(lexer, TOK_SLASH, start, location);
        case '%':
            return token_at(lexer, TOK_PERCENT, start, location);
        case '=':
            if (lexer->offset < lexer->length && lexer->source[lexer->offset] == '=') {
                lexer_advance(lexer);
                return token_at(lexer, TOK_EQUAL_EQUAL, start, location);
            }
            return token_at(lexer, TOK_ASSIGN, start, location);
        case '!':
            if (lexer->offset < lexer->length && lexer->source[lexer->offset] == '=') {
                lexer_advance(lexer);
                return token_at(lexer, TOK_BANG_EQUAL, start, location);
            }
            return token_at(lexer, TOK_BANG, start, location);
        case '<':
            if (lexer->offset < lexer->length && lexer->source[lexer->offset] == '=') {
                lexer_advance(lexer);
                return token_at(lexer, TOK_LESS_EQUAL, start, location);
            }
            return token_at(lexer, TOK_LESS, start, location);
        case '>':
            if (lexer->offset < lexer->length && lexer->source[lexer->offset] == '=') {
                lexer_advance(lexer);
                return token_at(lexer, TOK_GREATER_EQUAL, start, location);
            }
            return token_at(lexer, TOK_GREATER, start, location);
        default:
            snprintf(lexer->error, sizeof(lexer->error),
                     "unexpected byte 0x%02x", (unsigned)byte);
            return token_at(lexer, TOK_ERROR, start, location);
    }
}

typedef union ArenaHeader ArenaHeader;
union ArenaHeader {
    struct {
        ArenaHeader *next;
    } link;
    max_align_t alignment;
};

typedef struct {
    ArenaHeader *head;
} Arena;

static void out_of_memory(void) {
    fprintf(stderr, "fatal: out of memory\n");
    exit(PEBBLE_RUNTIME_ERROR);
}

static void *arena_alloc(Arena *arena, size_t size) {
    ArenaHeader *header = malloc(sizeof(*header) + size);
    if (header == NULL) {
        out_of_memory();
    }
    header->link.next = arena->head;
    arena->head = header;
    return header + 1;
}

static char *arena_copy(Arena *arena, const char *text, size_t length) {
    char *copy = arena_alloc(arena, length + 1);
    memcpy(copy, text, length);
    copy[length] = '\0';
    return copy;
}

static void arena_destroy(Arena *arena) {
    ArenaHeader *header = arena->head;
    while (header != NULL) {
        ArenaHeader *next = header->link.next;
        free(header);
        header = next;
    }
    arena->head = NULL;
}

typedef struct Expr Expr;
typedef struct Stmt Stmt;

typedef enum {
    EXPR_INTEGER,
    EXPR_VARIABLE,
    EXPR_UNARY,
    EXPR_BINARY
} ExprKind;

struct Expr {
    ExprKind kind;
    Location location;
    union {
        int64_t integer;
        struct {
            char *name;
            size_t slot;
        } variable;
        struct {
            TokenKind operation;
            Expr *operand;
        } unary;
        struct {
            TokenKind operation;
            Expr *left;
            Expr *right;
        } binary;
    } as;
};

typedef struct {
    Stmt **items;
    size_t count;
    size_t capacity;
} StmtList;

typedef enum {
    STMT_LET,
    STMT_ASSIGN,
    STMT_PRINT,
    STMT_IF,
    STMT_WHILE
} StmtKind;

struct Stmt {
    StmtKind kind;
    Location location;
    union {
        struct {
            char *name;
            size_t slot;
            Expr *value;
        } binding;
        Expr *print_value;
        struct {
            Expr *condition;
            StmtList consequent;
            StmtList alternative;
        } conditional;
        struct {
            Expr *condition;
            StmtList body;
        } loop;
    } as;
};

typedef struct {
    StmtList statements;
} Program;

static void list_push(StmtList *list, Stmt *statement) {
    if (list->count == list->capacity) {
        size_t new_capacity = list->capacity == 0 ? 8 : list->capacity * 2;
        Stmt **new_items = realloc(list->items, new_capacity * sizeof(*new_items));
        if (new_items == NULL) {
            out_of_memory();
        }
        list->items = new_items;
        list->capacity = new_capacity;
    }
    list->items[list->count++] = statement;
}

static void free_statement_lists(StmtList *list) {
    size_t index;
    for (index = 0; index < list->count; index++) {
        Stmt *statement = list->items[index];
        if (statement->kind == STMT_IF) {
            free_statement_lists(&statement->as.conditional.consequent);
            free_statement_lists(&statement->as.conditional.alternative);
        } else if (statement->kind == STMT_WHILE) {
            free_statement_lists(&statement->as.loop.body);
        }
    }
    free(list->items);
    list->items = NULL;
    list->count = 0;
    list->capacity = 0;
}

typedef struct {
    Lexer lexer;
    Token current;
    Arena *arena;
    bool failed;
    unsigned expression_depth;
    unsigned block_depth;
} Parser;

static void parser_error(Parser *parser, Location location, const char *format, ...) {
    va_list arguments;
    if (parser->failed) {
        return;
    }
    parser->failed = true;
    fprintf(stderr, "%" PRIu32 ":%" PRIu32 ": ", location.line, location.column);
    va_start(arguments, format);
    vfprintf(stderr, format, arguments);
    va_end(arguments);
    fputc('\n', stderr);
}

static void parser_advance(Parser *parser) {
    if (parser->failed) {
        return;
    }
    parser->current = lexer_next(&parser->lexer);
    if (parser->current.kind == TOK_ERROR) {
        parser_error(parser, parser->current.location, "%s", parser->lexer.error);
    }
}

static void parser_init(Parser *parser, Arena *arena, const char *source,
                        size_t length) {
    lexer_init(&parser->lexer, source, length);
    parser->arena = arena;
    parser->failed = false;
    parser->expression_depth = 0;
    parser->block_depth = 0;
    parser_advance(parser);
}

static bool parser_match(Parser *parser, TokenKind kind) {
    if (!parser->failed && parser->current.kind == kind) {
        parser_advance(parser);
        return true;
    }
    return false;
}

static bool parser_expect(Parser *parser, TokenKind kind, const char *message) {
    if (parser_match(parser, kind)) {
        return true;
    }
    if (!parser->failed) {
        parser_error(parser, parser->current.location, "%s", message);
    }
    return false;
}

static Expr *new_expr(Parser *parser, ExprKind kind, Location location) {
    Expr *expression = arena_alloc(parser->arena, sizeof(*expression));
    memset(expression, 0, sizeof(*expression));
    expression->kind = kind;
    expression->location = location;
    return expression;
}

static Stmt *new_stmt(Parser *parser, StmtKind kind, Location location) {
    Stmt *statement = arena_alloc(parser->arena, sizeof(*statement));
    memset(statement, 0, sizeof(*statement));
    statement->kind = kind;
    statement->location = location;
    return statement;
}

static Expr *parse_expression(Parser *parser);

static bool enter_expression_nesting(Parser *parser, Location location) {
    if (parser->expression_depth >= MAX_NESTING) {
        parser_error(parser, location, "expression nesting exceeds %u", MAX_NESTING);
        return false;
    }
    parser->expression_depth++;
    return true;
}

static Expr *parse_primary(Parser *parser) {
    Token token = parser->current;
    Expr *expression;

    if (parser_match(parser, TOK_INTEGER)) {
        expression = new_expr(parser, EXPR_INTEGER, token.location);
        expression->as.integer = token.integer;
        return expression;
    }
    if (parser_match(parser, TOK_IDENTIFIER)) {
        expression = new_expr(parser, EXPR_VARIABLE, token.location);
        expression->as.variable.name =
            arena_copy(parser->arena, token.begin, token.length);
        return expression;
    }
    if (parser_match(parser, TOK_LPAREN)) {
        if (!enter_expression_nesting(parser, token.location)) {
            return NULL;
        }
        expression = parse_expression(parser);
        parser_expect(parser, TOK_RPAREN, "expected ')' after expression");
        parser->expression_depth--;
        return expression;
    }
    if (!parser->failed) {
        parser_error(parser, token.location, "expected an expression");
    }
    return NULL;
}

static Expr *parse_unary(Parser *parser) {
    Token token = parser->current;
    if (token.kind == TOK_MINUS || token.kind == TOK_BANG) {
        Expr *expression;
        Expr *operand;
        parser_advance(parser);
        if (!enter_expression_nesting(parser, token.location)) {
            return NULL;
        }
        operand = parse_unary(parser);
        parser->expression_depth--;
        if (operand == NULL) {
            return NULL;
        }
        expression = new_expr(parser, EXPR_UNARY, token.location);
        expression->as.unary.operation = token.kind;
        expression->as.unary.operand = operand;
        return expression;
    }
    return parse_primary(parser);
}

static Expr *make_binary(Parser *parser, Expr *left, Token operation, Expr *right) {
    Expr *expression;
    if (left == NULL || right == NULL) {
        return NULL;
    }
    expression = new_expr(parser, EXPR_BINARY, operation.location);
    expression->as.binary.operation = operation.kind;
    expression->as.binary.left = left;
    expression->as.binary.right = right;
    return expression;
}

static Expr *parse_factor(Parser *parser) {
    Expr *left = parse_unary(parser);
    while (!parser->failed && (parser->current.kind == TOK_STAR ||
           parser->current.kind == TOK_SLASH || parser->current.kind == TOK_PERCENT)) {
        Token operation = parser->current;
        parser_advance(parser);
        left = make_binary(parser, left, operation, parse_unary(parser));
    }
    return left;
}

static Expr *parse_term(Parser *parser) {
    Expr *left = parse_factor(parser);
    while (!parser->failed &&
           (parser->current.kind == TOK_PLUS || parser->current.kind == TOK_MINUS)) {
        Token operation = parser->current;
        parser_advance(parser);
        left = make_binary(parser, left, operation, parse_factor(parser));
    }
    return left;
}

static Expr *parse_comparison(Parser *parser) {
    Expr *left = parse_term(parser);
    while (!parser->failed && (parser->current.kind == TOK_LESS ||
           parser->current.kind == TOK_LESS_EQUAL ||
           parser->current.kind == TOK_GREATER ||
           parser->current.kind == TOK_GREATER_EQUAL)) {
        Token operation = parser->current;
        parser_advance(parser);
        left = make_binary(parser, left, operation, parse_term(parser));
    }
    return left;
}

static Expr *parse_equality(Parser *parser) {
    Expr *left = parse_comparison(parser);
    while (!parser->failed && (parser->current.kind == TOK_EQUAL_EQUAL ||
           parser->current.kind == TOK_BANG_EQUAL)) {
        Token operation = parser->current;
        parser_advance(parser);
        left = make_binary(parser, left, operation, parse_comparison(parser));
    }
    return left;
}

static Expr *parse_expression(Parser *parser) {
    return parse_equality(parser);
}

static Stmt *parse_statement(Parser *parser);

static StmtList parse_block(Parser *parser) {
    StmtList list = {0};
    Location start = parser->current.location;

    if (!parser_expect(parser, TOK_LBRACE, "expected '{' to begin block")) {
        return list;
    }
    if (parser->block_depth >= MAX_NESTING) {
        parser_error(parser, start, "block nesting exceeds %u", MAX_NESTING);
        return list;
    }
    parser->block_depth++;
    while (!parser->failed && parser->current.kind != TOK_RBRACE &&
           parser->current.kind != TOK_EOF) {
        Stmt *statement;
        if (parser->current.kind == TOK_LET) {
            parser_error(parser, parser->current.location,
                         "declarations are allowed only at program start");
            break;
        }
        statement = parse_statement(parser);
        if (statement != NULL) {
            list_push(&list, statement);
        }
    }
    parser_expect(parser, TOK_RBRACE, "expected '}' after block");
    parser->block_depth--;
    return list;
}

static Stmt *parse_declaration(Parser *parser) {
    Location location = parser->current.location;
    Token name;
    Expr *value;
    Stmt *statement;

    parser_advance(parser);
    if (parser->current.kind != TOK_IDENTIFIER) {
        parser_error(parser, parser->current.location,
                     "expected identifier after 'let'");
        return NULL;
    }
    name = parser->current;
    parser_advance(parser);
    if (!parser_expect(parser, TOK_ASSIGN, "expected '=' after declaration name")) {
        return NULL;
    }
    value = parse_expression(parser);
    if (!parser_expect(parser, TOK_SEMICOLON, "expected ';' after declaration")) {
        return NULL;
    }
    statement = new_stmt(parser, STMT_LET, location);
    statement->as.binding.name = arena_copy(parser->arena, name.begin, name.length);
    statement->as.binding.value = value;
    return statement;
}

static Stmt *parse_statement(Parser *parser) {
    Token token = parser->current;
    Stmt *statement;
    Expr *value;

    if (token.kind == TOK_IDENTIFIER) {
        parser_advance(parser);
        if (!parser_expect(parser, TOK_ASSIGN, "expected '=' after assignment name")) {
            return NULL;
        }
        value = parse_expression(parser);
        if (!parser_expect(parser, TOK_SEMICOLON, "expected ';' after assignment")) {
            return NULL;
        }
        statement = new_stmt(parser, STMT_ASSIGN, token.location);
        statement->as.binding.name =
            arena_copy(parser->arena, token.begin, token.length);
        statement->as.binding.value = value;
        return statement;
    }

    if (parser_match(parser, TOK_PRINT)) {
        value = parse_expression(parser);
        if (!parser_expect(parser, TOK_SEMICOLON, "expected ';' after print value")) {
            return NULL;
        }
        statement = new_stmt(parser, STMT_PRINT, token.location);
        statement->as.print_value = value;
        return statement;
    }

    if (parser_match(parser, TOK_IF)) {
        value = parse_expression(parser);
        statement = new_stmt(parser, STMT_IF, token.location);
        statement->as.conditional.condition = value;
        statement->as.conditional.consequent = parse_block(parser);
        if (parser_match(parser, TOK_ELSE)) {
            statement->as.conditional.alternative = parse_block(parser);
        }
        if (parser->failed) {
            free_statement_lists(&statement->as.conditional.consequent);
            free_statement_lists(&statement->as.conditional.alternative);
            return NULL;
        }
        return statement;
    }

    if (parser_match(parser, TOK_WHILE)) {
        value = parse_expression(parser);
        statement = new_stmt(parser, STMT_WHILE, token.location);
        statement->as.loop.condition = value;
        statement->as.loop.body = parse_block(parser);
        if (parser->failed) {
            free_statement_lists(&statement->as.loop.body);
            return NULL;
        }
        return statement;
    }

    if (!parser->failed) {
        parser_error(parser, token.location, "expected a statement");
    }
    return NULL;
}

static Program parse_program(Parser *parser) {
    Program program = {0};

    while (!parser->failed && parser->current.kind == TOK_LET) {
        Stmt *declaration = parse_declaration(parser);
        if (declaration != NULL) {
            list_push(&program.statements, declaration);
        }
    }
    while (!parser->failed && parser->current.kind != TOK_EOF) {
        Stmt *statement;
        if (parser->current.kind == TOK_LET) {
            parser_error(parser, parser->current.location,
                         "declarations are allowed only at program start");
            break;
        }
        statement = parse_statement(parser);
        if (statement != NULL) {
            list_push(&program.statements, statement);
        }
    }
    return program;
}

typedef struct {
    const char *name;
    size_t slot;
} Symbol;

typedef struct {
    Symbol symbols[MAX_VARIABLES];
    size_t count;
    bool failed;
} Resolver;

static void resolver_error(Resolver *resolver, Location location,
                           const char *format, ...) {
    va_list arguments;
    if (resolver->failed) {
        return;
    }
    resolver->failed = true;
    fprintf(stderr, "%" PRIu32 ":%" PRIu32 ": ", location.line, location.column);
    va_start(arguments, format);
    vfprintf(stderr, format, arguments);
    va_end(arguments);
    fputc('\n', stderr);
}

static bool resolver_lookup(const Resolver *resolver, const char *name,
                            size_t *slot) {
    size_t index;
    for (index = 0; index < resolver->count; index++) {
        if (strcmp(resolver->symbols[index].name, name) == 0) {
            *slot = resolver->symbols[index].slot;
            return true;
        }
    }
    return false;
}

static void resolve_expression(Resolver *resolver, Expr *expression,
                               unsigned depth) {
    size_t slot;
    if (resolver->failed || expression == NULL) {
        return;
    }
    if (depth > MAX_NESTING) {
        resolver_error(resolver, expression->location,
                       "expression tree exceeds %u levels", MAX_NESTING);
        return;
    }
    switch (expression->kind) {
        case EXPR_INTEGER:
            break;
        case EXPR_VARIABLE:
            if (!resolver_lookup(resolver, expression->as.variable.name, &slot)) {
                resolver_error(resolver, expression->location,
                               "unknown variable '%s'",
                               expression->as.variable.name);
            } else {
                expression->as.variable.slot = slot;
            }
            break;
        case EXPR_UNARY:
            resolve_expression(resolver, expression->as.unary.operand, depth + 1);
            break;
        case EXPR_BINARY:
            resolve_expression(resolver, expression->as.binary.left, depth + 1);
            resolve_expression(resolver, expression->as.binary.right, depth + 1);
            break;
    }
}

static void resolve_list(Resolver *resolver, StmtList *list);

static void resolve_statement(Resolver *resolver, Stmt *statement) {
    size_t slot;
    if (resolver->failed) {
        return;
    }
    switch (statement->kind) {
        case STMT_LET:
            resolver_error(resolver, statement->location,
                           "internal declaration placement error");
            break;
        case STMT_ASSIGN:
            if (!resolver_lookup(resolver, statement->as.binding.name, &slot)) {
                resolver_error(resolver, statement->location,
                               "unknown variable '%s'",
                               statement->as.binding.name);
                return;
            }
            statement->as.binding.slot = slot;
            resolve_expression(resolver, statement->as.binding.value, 1);
            break;
        case STMT_PRINT:
            resolve_expression(resolver, statement->as.print_value, 1);
            break;
        case STMT_IF:
            resolve_expression(resolver, statement->as.conditional.condition, 1);
            resolve_list(resolver, &statement->as.conditional.consequent);
            resolve_list(resolver, &statement->as.conditional.alternative);
            break;
        case STMT_WHILE:
            resolve_expression(resolver, statement->as.loop.condition, 1);
            resolve_list(resolver, &statement->as.loop.body);
            break;
    }
}

static void resolve_list(Resolver *resolver, StmtList *list) {
    size_t index;
    for (index = 0; index < list->count && !resolver->failed; index++) {
        resolve_statement(resolver, list->items[index]);
    }
}

static bool resolve_program(Program *program, size_t *variable_count) {
    Resolver resolver = {0};
    size_t index;

    for (index = 0; index < program->statements.count && !resolver.failed; index++) {
        Stmt *statement = program->statements.items[index];
        if (statement->kind == STMT_LET) {
            size_t ignored;
            resolve_expression(&resolver, statement->as.binding.value, 1);
            if (resolver.failed) {
                break;
            }
            if (resolver_lookup(&resolver, statement->as.binding.name, &ignored)) {
                resolver_error(&resolver, statement->location,
                               "duplicate variable '%s'",
                               statement->as.binding.name);
                break;
            }
            if (resolver.count == MAX_VARIABLES) {
                resolver_error(&resolver, statement->location,
                               "program exceeds %u variables", MAX_VARIABLES);
                break;
            }
            statement->as.binding.slot = resolver.count;
            resolver.symbols[resolver.count].name = statement->as.binding.name;
            resolver.symbols[resolver.count].slot = resolver.count;
            resolver.count++;
        } else {
            resolve_statement(&resolver, statement);
        }
    }
    *variable_count = resolver.count;
    return !resolver.failed;
}

typedef struct {
    int64_t variables[MAX_VARIABLES];
    uint64_t steps_left;
    bool failed;
} Executor;

static void runtime_error(Executor *executor, const char *message) {
    if (!executor->failed) {
        fprintf(stderr, "runtime error: %s\n", message);
        executor->failed = true;
    }
}

static bool consume_step(Executor *executor) {
    if (executor->steps_left == 0) {
        runtime_error(executor, "step limit exceeded");
        return false;
    }
    executor->steps_left--;
    return true;
}

static int64_t evaluate_expression(Executor *executor, const Expr *expression) {
    int64_t left;
    int64_t right;
    int64_t result = 0;

    if (executor->failed) {
        return 0;
    }
    switch (expression->kind) {
        case EXPR_INTEGER:
            return expression->as.integer;
        case EXPR_VARIABLE:
            return executor->variables[expression->as.variable.slot];
        case EXPR_UNARY:
            left = evaluate_expression(executor, expression->as.unary.operand);
            if (executor->failed) {
                return 0;
            }
            if (expression->as.unary.operation == TOK_BANG) {
                return left == 0 ? 1 : 0;
            }
            if (__builtin_sub_overflow((int64_t)0, left, &result)) {
                runtime_error(executor, "arithmetic overflow");
                return 0;
            }
            return result;
        case EXPR_BINARY:
            left = evaluate_expression(executor, expression->as.binary.left);
            right = evaluate_expression(executor, expression->as.binary.right);
            if (executor->failed) {
                return 0;
            }
            switch (expression->as.binary.operation) {
                case TOK_PLUS:
                    if (__builtin_add_overflow(left, right, &result)) {
                        runtime_error(executor, "arithmetic overflow");
                    }
                    break;
                case TOK_MINUS:
                    if (__builtin_sub_overflow(left, right, &result)) {
                        runtime_error(executor, "arithmetic overflow");
                    }
                    break;
                case TOK_STAR:
                    if (__builtin_mul_overflow(left, right, &result)) {
                        runtime_error(executor, "arithmetic overflow");
                    }
                    break;
                case TOK_SLASH:
                case TOK_PERCENT:
                    if (right == 0) {
                        runtime_error(executor, "division by zero");
                    } else if (left == INT64_MIN && right == -1) {
                        runtime_error(executor, "arithmetic overflow");
                    } else if (expression->as.binary.operation == TOK_SLASH) {
                        result = left / right;
                    } else {
                        result = left % right;
                    }
                    break;
                case TOK_EQUAL_EQUAL:
                    result = left == right;
                    break;
                case TOK_BANG_EQUAL:
                    result = left != right;
                    break;
                case TOK_LESS:
                    result = left < right;
                    break;
                case TOK_LESS_EQUAL:
                    result = left <= right;
                    break;
                case TOK_GREATER:
                    result = left > right;
                    break;
                case TOK_GREATER_EQUAL:
                    result = left >= right;
                    break;
                default:
                    runtime_error(executor, "invalid binary operation");
                    break;
            }
            return result;
    }
    runtime_error(executor, "invalid expression");
    return 0;
}

static void execute_list(Executor *executor, const StmtList *list);

static void execute_statement(Executor *executor, const Stmt *statement) {
    int64_t value;
    if (executor->failed) {
        return;
    }

    if (statement->kind == STMT_WHILE) {
        for (;;) {
            if (!consume_step(executor)) {
                return;
            }
            value = evaluate_expression(executor, statement->as.loop.condition);
            if (executor->failed || value == 0) {
                return;
            }
            execute_list(executor, &statement->as.loop.body);
            if (executor->failed) {
                return;
            }
        }
    }

    if (!consume_step(executor)) {
        return;
    }
    switch (statement->kind) {
        case STMT_LET:
        case STMT_ASSIGN:
            value = evaluate_expression(executor, statement->as.binding.value);
            if (!executor->failed) {
                executor->variables[statement->as.binding.slot] = value;
            }
            break;
        case STMT_PRINT:
            value = evaluate_expression(executor, statement->as.print_value);
            if (!executor->failed) {
                printf("%" PRId64 "\n", value);
            }
            break;
        case STMT_IF:
            value = evaluate_expression(executor,
                                        statement->as.conditional.condition);
            if (!executor->failed) {
                execute_list(executor, value != 0
                    ? &statement->as.conditional.consequent
                    : &statement->as.conditional.alternative);
            }
            break;
        case STMT_WHILE:
            break;
    }
}

static void execute_list(Executor *executor, const StmtList *list) {
    size_t index;
    for (index = 0; index < list->count && !executor->failed; index++) {
        execute_statement(executor, list->items[index]);
    }
}

typedef struct {
    FILE *output;
    size_t variable_count;
    unsigned next_label;
    bool failed;
} Codegen;

static void emitf(Codegen *codegen, const char *format, ...) {
    va_list arguments;
    int result;
    if (codegen->failed) {
        return;
    }
    va_start(arguments, format);
    result = vfprintf(codegen->output, format, arguments);
    va_end(arguments);
    if (result < 0) {
        codegen->failed = true;
    }
}

static int variable_offset(size_t slot) {
    return -(int)((slot + 1) * sizeof(int64_t));
}

static int step_offset(const Codegen *codegen) {
    return -(int)((codegen->variable_count + 1) * sizeof(int64_t));
}

static unsigned fresh_label(Codegen *codegen) {
    return codegen->next_label++;
}

static void emit_expression(Codegen *codegen, const Expr *expression) {
    unsigned safe_division;
    TokenKind operation = TOK_ERROR;

    switch (expression->kind) {
        case EXPR_INTEGER:
            emitf(codegen, "    movabsq $%" PRId64 ", %%rax\n",
                  expression->as.integer);
            return;
        case EXPR_VARIABLE:
            emitf(codegen, "    movq %d(%%rbp), %%rax\n",
                  variable_offset(expression->as.variable.slot));
            return;
        case EXPR_UNARY:
            emit_expression(codegen, expression->as.unary.operand);
            if (expression->as.unary.operation == TOK_MINUS) {
                emitf(codegen, "    negq %%rax\n");
                emitf(codegen, "    jo .Loverflow\n");
            } else {
                emitf(codegen, "    testq %%rax, %%rax\n");
                emitf(codegen, "    sete %%al\n");
                emitf(codegen, "    movzbq %%al, %%rax\n");
            }
            return;
        case EXPR_BINARY:
            operation = expression->as.binary.operation;
            emit_expression(codegen, expression->as.binary.left);
            emitf(codegen, "    pushq %%rax\n");
            emit_expression(codegen, expression->as.binary.right);
            emitf(codegen, "    movq %%rax, %%rcx\n");
            emitf(codegen, "    popq %%rax\n");
            break;
    }

    switch (operation) {
        case TOK_PLUS:
            emitf(codegen, "    addq %%rcx, %%rax\n");
            emitf(codegen, "    jo .Loverflow\n");
            break;
        case TOK_MINUS:
            emitf(codegen, "    subq %%rcx, %%rax\n");
            emitf(codegen, "    jo .Loverflow\n");
            break;
        case TOK_STAR:
            emitf(codegen, "    imulq %%rcx, %%rax\n");
            emitf(codegen, "    jo .Loverflow\n");
            break;
        case TOK_SLASH:
        case TOK_PERCENT:
            safe_division = fresh_label(codegen);
            emitf(codegen, "    testq %%rcx, %%rcx\n");
            emitf(codegen, "    je .Ldivision_zero\n");
            emitf(codegen, "    cmpq $-1, %%rcx\n");
            emitf(codegen, "    jne .Lsafe_division_%u\n", safe_division);
            emitf(codegen, "    movabsq $-9223372036854775808, %%rdx\n");
            emitf(codegen, "    cmpq %%rdx, %%rax\n");
            emitf(codegen, "    je .Loverflow\n");
            emitf(codegen, ".Lsafe_division_%u:\n", safe_division);
            emitf(codegen, "    cqto\n");
            emitf(codegen, "    idivq %%rcx\n");
            if (operation == TOK_PERCENT) {
                emitf(codegen, "    movq %%rdx, %%rax\n");
            }
            break;
        case TOK_EQUAL_EQUAL:
            emitf(codegen, "    cmpq %%rcx, %%rax\n");
            emitf(codegen, "    sete %%al\n");
            emitf(codegen, "    movzbq %%al, %%rax\n");
            break;
        case TOK_BANG_EQUAL:
            emitf(codegen, "    cmpq %%rcx, %%rax\n");
            emitf(codegen, "    setne %%al\n");
            emitf(codegen, "    movzbq %%al, %%rax\n");
            break;
        case TOK_LESS:
            emitf(codegen, "    cmpq %%rcx, %%rax\n");
            emitf(codegen, "    setl %%al\n");
            emitf(codegen, "    movzbq %%al, %%rax\n");
            break;
        case TOK_LESS_EQUAL:
            emitf(codegen, "    cmpq %%rcx, %%rax\n");
            emitf(codegen, "    setle %%al\n");
            emitf(codegen, "    movzbq %%al, %%rax\n");
            break;
        case TOK_GREATER:
            emitf(codegen, "    cmpq %%rcx, %%rax\n");
            emitf(codegen, "    setg %%al\n");
            emitf(codegen, "    movzbq %%al, %%rax\n");
            break;
        case TOK_GREATER_EQUAL:
            emitf(codegen, "    cmpq %%rcx, %%rax\n");
            emitf(codegen, "    setge %%al\n");
            emitf(codegen, "    movzbq %%al, %%rax\n");
            break;
        default:
            codegen->failed = true;
            break;
    }
}

static void emit_step_check(Codegen *codegen) {
    int offset = step_offset(codegen);
    emitf(codegen, "    cmpq $0, %d(%%rbp)\n", offset);
    emitf(codegen, "    je .Lstep_limit\n");
    emitf(codegen, "    subq $1, %d(%%rbp)\n", offset);
}

static void emit_statement_list(Codegen *codegen, const StmtList *list);

static void emit_statement(Codegen *codegen, const Stmt *statement) {
    unsigned false_label;
    unsigned end_label;
    unsigned loop_label;

    if (statement->kind == STMT_WHILE) {
        loop_label = fresh_label(codegen);
        end_label = fresh_label(codegen);
        emitf(codegen, ".Lloop_%u:\n", loop_label);
        emit_step_check(codegen);
        emit_expression(codegen, statement->as.loop.condition);
        emitf(codegen, "    testq %%rax, %%rax\n");
        emitf(codegen, "    je .Lend_loop_%u\n", end_label);
        emit_statement_list(codegen, &statement->as.loop.body);
        emitf(codegen, "    jmp .Lloop_%u\n", loop_label);
        emitf(codegen, ".Lend_loop_%u:\n", end_label);
        return;
    }

    emit_step_check(codegen);
    switch (statement->kind) {
        case STMT_LET:
        case STMT_ASSIGN:
            emit_expression(codegen, statement->as.binding.value);
            emitf(codegen, "    movq %%rax, %d(%%rbp)\n",
                  variable_offset(statement->as.binding.slot));
            break;
        case STMT_PRINT:
            emit_expression(codegen, statement->as.print_value);
            emitf(codegen, "    movq %%rax, %%rsi\n");
            emitf(codegen, "    leaq .Lprint_format(%%rip), %%rdi\n");
            emitf(codegen, "    xorl %%eax, %%eax\n");
            emitf(codegen, "    call printf@PLT\n");
            break;
        case STMT_IF:
            false_label = fresh_label(codegen);
            end_label = fresh_label(codegen);
            emit_expression(codegen, statement->as.conditional.condition);
            emitf(codegen, "    testq %%rax, %%rax\n");
            emitf(codegen, "    je .Lelse_%u\n", false_label);
            emit_statement_list(codegen,
                                &statement->as.conditional.consequent);
            emitf(codegen, "    jmp .Lend_if_%u\n", end_label);
            emitf(codegen, ".Lelse_%u:\n", false_label);
            emit_statement_list(codegen,
                                &statement->as.conditional.alternative);
            emitf(codegen, ".Lend_if_%u:\n", end_label);
            break;
        case STMT_WHILE:
            break;
    }
}

static void emit_statement_list(Codegen *codegen, const StmtList *list) {
    size_t index;
    for (index = 0; index < list->count; index++) {
        emit_statement(codegen, list->items[index]);
    }
}

static bool emit_program(FILE *output, const Program *program,
                         size_t variable_count) {
    Codegen codegen = {0};
    size_t raw_frame = (variable_count + 1) * sizeof(int64_t);
    size_t frame_size = (raw_frame + 15u) & ~(size_t)15u;

    codegen.output = output;
    codegen.variable_count = variable_count;

    emitf(&codegen, "    .section .rodata\n");
    emitf(&codegen, ".Lprint_format:\n");
    emitf(&codegen, "    .string \"%%ld\\n\"\n");
    emitf(&codegen, ".Lerror_overflow:\n");
    emitf(&codegen, "    .string \"runtime error: arithmetic overflow\\n\"\n");
    emitf(&codegen, ".Lerror_division_zero:\n");
    emitf(&codegen, "    .string \"runtime error: division by zero\\n\"\n");
    emitf(&codegen, ".Lerror_step_limit:\n");
    emitf(&codegen, "    .string \"runtime error: step limit exceeded\\n\"\n");
    emitf(&codegen, "    .text\n");
    emitf(&codegen, "    .globl main\n");
    emitf(&codegen, "    .type main, @function\n");
    emitf(&codegen, "main:\n");
    emitf(&codegen, "    pushq %%rbp\n");
    emitf(&codegen, "    movq %%rsp, %%rbp\n");
    emitf(&codegen, "    subq $%zu, %%rsp\n", frame_size);
    emitf(&codegen, "    movq $%" PRIu64 ", %d(%%rbp)\n",
          DEFAULT_STEPS, step_offset(&codegen));
    emit_statement_list(&codegen, &program->statements);
    emitf(&codegen, "    xorl %%eax, %%eax\n");
    emitf(&codegen, "    leave\n");
    emitf(&codegen, "    ret\n");

    emitf(&codegen, ".Loverflow:\n");
    emitf(&codegen, "    leaq .Lerror_overflow(%%rip), %%rdi\n");
    emitf(&codegen, "    jmp .Lruntime_error\n");
    emitf(&codegen, ".Ldivision_zero:\n");
    emitf(&codegen, "    leaq .Lerror_division_zero(%%rip), %%rdi\n");
    emitf(&codegen, "    jmp .Lruntime_error\n");
    emitf(&codegen, ".Lstep_limit:\n");
    emitf(&codegen, "    leaq .Lerror_step_limit(%%rip), %%rdi\n");
    emitf(&codegen, ".Lruntime_error:\n");
    /* Discard any expression temporaries before calling libc on an error path. */
    emitf(&codegen, "    movq %%rbp, %%rsp\n");
    emitf(&codegen, "    movq stderr(%%rip), %%rsi\n");
    emitf(&codegen, "    call fputs@PLT\n");
    emitf(&codegen, "    movl $70, %%eax\n");
    emitf(&codegen, "    leave\n");
    emitf(&codegen, "    ret\n");
    emitf(&codegen, "    .size main, .-main\n");
    emitf(&codegen, "    .section .note.GNU-stack,\"\",@progbits\n");

    return !codegen.failed && !ferror(output);
}

typedef struct {
    char *source;
    Arena arena;
    Program program;
    size_t variable_count;
} LoadedProgram;

static int read_source(const char *path, char **source, size_t *length) {
    FILE *input;
    char *buffer;
    size_t count;

    input = fopen(path, "rb");
    if (input == NULL) {
        fprintf(stderr, "I/O error: cannot open '%s': %s\n", path,
                strerror(errno));
        return PEBBLE_IO_ERROR;
    }
    buffer = malloc((size_t)MAX_SOURCE_BYTES + 2u);
    if (buffer == NULL) {
        fclose(input);
        out_of_memory();
    }
    count = fread(buffer, 1, (size_t)MAX_SOURCE_BYTES + 1u, input);
    if (ferror(input)) {
        fprintf(stderr, "I/O error: cannot read '%s': %s\n", path,
                strerror(errno));
        free(buffer);
        fclose(input);
        return PEBBLE_IO_ERROR;
    }
    if (fclose(input) != 0) {
        fprintf(stderr, "I/O error: cannot close '%s': %s\n", path,
                strerror(errno));
        free(buffer);
        return PEBBLE_IO_ERROR;
    }
    if (count > MAX_SOURCE_BYTES) {
        fprintf(stderr, "1:1: source exceeds %u bytes\n", MAX_SOURCE_BYTES);
        free(buffer);
        return PEBBLE_SOURCE_ERROR;
    }
    buffer[count] = '\0';
    *source = buffer;
    *length = count;
    return PEBBLE_OK;
}

static void destroy_loaded_program(LoadedProgram *loaded) {
    free_statement_lists(&loaded->program.statements);
    arena_destroy(&loaded->arena);
    free(loaded->source);
    memset(loaded, 0, sizeof(*loaded));
}

static int load_program(const char *path, LoadedProgram *loaded) {
    size_t length = 0;
    Parser parser;
    int status;

    memset(loaded, 0, sizeof(*loaded));
    status = read_source(path, &loaded->source, &length);
    if (status != PEBBLE_OK) {
        return status;
    }
    parser_init(&parser, &loaded->arena, loaded->source, length);
    loaded->program = parse_program(&parser);
    if (parser.failed) {
        destroy_loaded_program(loaded);
        return PEBBLE_SOURCE_ERROR;
    }
    if (!resolve_program(&loaded->program, &loaded->variable_count)) {
        destroy_loaded_program(loaded);
        return PEBBLE_SOURCE_ERROR;
    }
    return PEBBLE_OK;
}

static int write_assembly_atomically(const char *path, const Program *program,
                                     size_t variable_count) {
    static const char suffix[] = ".tmp.XXXXXX";
    size_t path_length = strlen(path);
    char *temporary;
    int descriptor;
    FILE *output;
    bool generated;
    int saved_errno;

    if (path_length > SIZE_MAX - sizeof(suffix)) {
        fprintf(stderr, "I/O error: output path is too long\n");
        return PEBBLE_IO_ERROR;
    }
    temporary = malloc(path_length + sizeof(suffix));
    if (temporary == NULL) {
        out_of_memory();
    }
    memcpy(temporary, path, path_length);
    memcpy(temporary + path_length, suffix, sizeof(suffix));

    descriptor = mkstemp(temporary);
    if (descriptor < 0) {
        fprintf(stderr, "I/O error: cannot create output beside '%s': %s\n",
                path, strerror(errno));
        free(temporary);
        return PEBBLE_IO_ERROR;
    }
    output = fdopen(descriptor, "w");
    if (output == NULL) {
        saved_errno = errno;
        close(descriptor);
        unlink(temporary);
        fprintf(stderr, "I/O error: cannot open temporary output: %s\n",
                strerror(saved_errno));
        free(temporary);
        return PEBBLE_IO_ERROR;
    }

    generated = emit_program(output, program, variable_count);
    if (generated && fflush(output) != 0) {
        generated = false;
    }
    if (generated && fsync(fileno(output)) != 0) {
        generated = false;
    }
    if (fclose(output) != 0) {
        generated = false;
    }
    if (!generated) {
        saved_errno = errno;
        unlink(temporary);
        fprintf(stderr, "I/O error: cannot write assembly: %s\n",
                strerror(saved_errno));
        free(temporary);
        return PEBBLE_IO_ERROR;
    }
    if (rename(temporary, path) != 0) {
        saved_errno = errno;
        unlink(temporary);
        fprintf(stderr, "I/O error: cannot publish '%s': %s\n", path,
                strerror(saved_errno));
        free(temporary);
        return PEBBLE_IO_ERROR;
    }
    free(temporary);
    return PEBBLE_OK;
}

int pebble_eval_file(const char *path, uint64_t max_steps) {
    LoadedProgram loaded;
    Executor executor = {0};
    int status = load_program(path, &loaded);

    if (status != PEBBLE_OK) {
        return status;
    }
    executor.steps_left = max_steps;
    execute_list(&executor, &loaded.program.statements);
    status = executor.failed ? PEBBLE_RUNTIME_ERROR : PEBBLE_OK;
    destroy_loaded_program(&loaded);
    return status;
}

int pebble_compile_file(const char *input_path, const char *output_path) {
    LoadedProgram loaded;
    int status = load_program(input_path, &loaded);

    if (status != PEBBLE_OK) {
        return status;
    }
    status = write_assembly_atomically(output_path, &loaded.program,
                                       loaded.variable_count);
    destroy_loaded_program(&loaded);
    return status;
}
