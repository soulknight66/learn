#include <inttypes.h>
#include <stdarg.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define SOURCE_LIMIT ((size_t)1048576)
#define NODE_LIMIT ((size_t)65536)
#define VARIABLE_LIMIT ((size_t)256)
#define DEPTH_LIMIT 128U
#define STEP_LIMIT UINT64_C(10000000)

typedef enum {
    TK_EOF,
    TK_INTEGER,
    TK_IDENTIFIER,
    TK_LET,
    TK_PRINT,
    TK_IF,
    TK_ELSE,
    TK_WHILE,
    TK_LPAREN,
    TK_RPAREN,
    TK_LBRACE,
    TK_RBRACE,
    TK_SEMICOLON,
    TK_PLUS,
    TK_MINUS,
    TK_STAR,
    TK_SLASH,
    TK_PERCENT,
    TK_ASSIGN,
    TK_EQUAL_EQUAL,
    TK_BANG_EQUAL,
    TK_LESS,
    TK_LESS_EQUAL,
    TK_GREATER,
    TK_GREATER_EQUAL
} TokenKind;

typedef struct {
    TokenKind kind;
    const char *start;
    size_t length;
    size_t line;
    size_t column;
    uint64_t value;
} Token;

typedef struct {
    Token *items;
    size_t count;
    size_t capacity;
    char error[192];
} TokenList;

static const char *token_kind_name(TokenKind kind) {
    static const char *const names[] = {
        "EOF",          "INTEGER",       "IDENTIFIER", "LET",
        "PRINT",        "IF",            "ELSE",       "WHILE",
        "LPAREN",       "RPAREN",        "LBRACE",     "RBRACE",
        "SEMICOLON",    "PLUS",          "MINUS",      "STAR",
        "SLASH",        "PERCENT",       "ASSIGN",     "EQUAL_EQUAL",
        "BANG_EQUAL",   "LESS",          "LESS_EQUAL", "GREATER",
        "GREATER_EQUAL"
    };
    return names[(int)kind];
}

static bool ascii_alpha(unsigned char c) {
    return (c >= (unsigned char)'a' && c <= (unsigned char)'z') ||
           (c >= (unsigned char)'A' && c <= (unsigned char)'Z') || c == '_';
}

static bool ascii_digit(unsigned char c) {
    return c >= (unsigned char)'0' && c <= (unsigned char)'9';
}

static bool token_list_push(TokenList *list, Token token) {
    Token *grown;
    size_t next_capacity;
    if (list->count < list->capacity) {
        list->items[list->count++] = token;
        return true;
    }
    next_capacity = list->capacity == 0 ? 128 : list->capacity * 2;
    grown = (Token *)realloc(list->items, next_capacity * sizeof(*grown));
    if (grown == NULL) {
        snprintf(list->error, sizeof(list->error), "out of memory while storing tokens");
        return false;
    }
    list->items = grown;
    list->capacity = next_capacity;
    list->items[list->count++] = token;
    return true;
}

static TokenKind identifier_kind(const char *text, size_t length) {
    if (length == 3 && memcmp(text, "let", 3) == 0) {
        return TK_LET;
    }
    if (length == 5 && memcmp(text, "print", 5) == 0) {
        return TK_PRINT;
    }
    if (length == 2 && memcmp(text, "if", 2) == 0) {
        return TK_IF;
    }
    if (length == 4 && memcmp(text, "else", 4) == 0) {
        return TK_ELSE;
    }
    if (length == 5 && memcmp(text, "while", 5) == 0) {
        return TK_WHILE;
    }
    return TK_IDENTIFIER;
}

static bool lex_source(const char *source, size_t length, TokenList *out) {
    size_t at = 0;
    size_t line = 1;
    size_t column = 1;

    while (at < length) {
        unsigned char c = (unsigned char)source[at];
        Token token;
        size_t begin;
        size_t begin_column;

        if (c == ' ' || c == '\t' || c == '\r') {
            ++at;
            ++column;
            continue;
        }
        if (c == '\n') {
            ++at;
            ++line;
            column = 1;
            continue;
        }
        if (c == '/' && at + 1 < length && source[at + 1] == '/') {
            at += 2;
            column += 2;
            while (at < length && source[at] != '\n') {
                ++at;
                ++column;
            }
            continue;
        }

        memset(&token, 0, sizeof(token));
        token.start = source + at;
        token.length = 1;
        token.line = line;
        token.column = column;

        if (ascii_alpha(c)) {
            begin = at;
            begin_column = column;
            do {
                ++at;
                ++column;
            } while (at < length &&
                     (ascii_alpha((unsigned char)source[at]) ||
                      ascii_digit((unsigned char)source[at])));
            token.start = source + begin;
            token.length = at - begin;
            token.column = begin_column;
            token.kind = identifier_kind(token.start, token.length);
            if (!token_list_push(out, token)) {
                return false;
            }
            continue;
        }

        if (ascii_digit(c)) {
            uint64_t value = 0;
            begin = at;
            begin_column = column;
            while (at < length && ascii_digit((unsigned char)source[at])) {
                unsigned digit = (unsigned)(source[at] - '0');
                if (value > (UINT64_C(9223372036854775807) - digit) / 10) {
                    snprintf(out->error, sizeof(out->error),
                             "%zu:%zu: integer literal is outside signed 64-bit range",
                             line, begin_column);
                    return false;
                }
                value = value * 10 + digit;
                ++at;
                ++column;
            }
            token.kind = TK_INTEGER;
            token.start = source + begin;
            token.length = at - begin;
            token.column = begin_column;
            token.value = value;
            if (!token_list_push(out, token)) {
                return false;
            }
            continue;
        }

        ++at;
        ++column;
        switch (c) {
            case '(':
                token.kind = TK_LPAREN;
                break;
            case ')':
                token.kind = TK_RPAREN;
                break;
            case '{':
                token.kind = TK_LBRACE;
                break;
            case '}':
                token.kind = TK_RBRACE;
                break;
            case ';':
                token.kind = TK_SEMICOLON;
                break;
            case '+':
                token.kind = TK_PLUS;
                break;
            case '-':
                token.kind = TK_MINUS;
                break;
            case '*':
                token.kind = TK_STAR;
                break;
            case '/':
                token.kind = TK_SLASH;
                break;
            case '%':
                token.kind = TK_PERCENT;
                break;
            case '=':
                if (at < length && source[at] == '=') {
                    ++at;
                    ++column;
                    token.kind = TK_EQUAL_EQUAL;
                    token.length = 2;
                } else {
                    token.kind = TK_ASSIGN;
                }
                break;
            case '!':
                if (at < length && source[at] == '=') {
                    ++at;
                    ++column;
                    token.kind = TK_BANG_EQUAL;
                    token.length = 2;
                } else {
                    snprintf(out->error, sizeof(out->error),
                             "%zu:%zu: unexpected '!' (only '!=' is valid)", line,
                             token.column);
                    return false;
                }
                break;
            case '<':
                if (at < length && source[at] == '=') {
                    ++at;
                    ++column;
                    token.kind = TK_LESS_EQUAL;
                    token.length = 2;
                } else {
                    token.kind = TK_LESS;
                }
                break;
            case '>':
                if (at < length && source[at] == '=') {
                    ++at;
                    ++column;
                    token.kind = TK_GREATER_EQUAL;
                    token.length = 2;
                } else {
                    token.kind = TK_GREATER;
                }
                break;
            default:
                snprintf(out->error, sizeof(out->error),
                         "%zu:%zu: unexpected byte 0x%02x", line, token.column,
                         (unsigned)c);
                return false;
        }
        if (!token_list_push(out, token)) {
            return false;
        }
    }

    {
        Token eof;
        memset(&eof, 0, sizeof(eof));
        eof.kind = TK_EOF;
        eof.start = source + length;
        eof.line = line;
        eof.column = column;
        return token_list_push(out, eof);
    }
}

typedef enum {
    NODE_INTEGER,
    NODE_VARIABLE,
    NODE_UNARY,
    NODE_BINARY,
    NODE_LET,
    NODE_ASSIGN,
    NODE_PRINT,
    NODE_IF,
    NODE_WHILE
} NodeKind;

typedef struct Node Node;
struct Node {
    NodeKind kind;
    Token token;
    TokenKind operation;
    uint64_t value;
    int slot;
    Node *a;
    Node *b;
    Node *c;
    Node *next;
};

typedef struct {
    const TokenList *tokens;
    size_t at;
    Node *arena;
    size_t count;
    unsigned depth;
    char error[192];
} Parser;

static const Token *parser_current(const Parser *parser) {
    return &parser->tokens->items[parser->at];
}

static bool parser_check(const Parser *parser, TokenKind kind) {
    return parser_current(parser)->kind == kind;
}

static const Token *parser_advance(Parser *parser) {
    const Token *token = parser_current(parser);
    if (token->kind != TK_EOF) {
        ++parser->at;
    }
    return token;
}

static void parser_fail(Parser *parser, const Token *token, const char *message) {
    if (parser->error[0] == '\0') {
        snprintf(parser->error, sizeof(parser->error), "%zu:%zu: %s", token->line,
                 token->column, message);
    }
}

static const Token *parser_consume(Parser *parser, TokenKind kind,
                                   const char *message) {
    if (parser_check(parser, kind)) {
        return parser_advance(parser);
    }
    parser_fail(parser, parser_current(parser), message);
    return NULL;
}

static bool parser_enter(Parser *parser, const Token *token) {
    if (parser->depth >= DEPTH_LIMIT) {
        parser_fail(parser, token, "nesting limit exceeded");
        return false;
    }
    ++parser->depth;
    return true;
}

static Node *parser_node(Parser *parser, NodeKind kind, Token token) {
    Node *node;
    if (parser->count >= NODE_LIMIT) {
        parser_fail(parser, &token, "AST node limit exceeded");
        return NULL;
    }
    node = &parser->arena[parser->count++];
    memset(node, 0, sizeof(*node));
    node->kind = kind;
    node->token = token;
    node->slot = -1;
    return node;
}

static Node *parse_expression(Parser *parser);
static Node *parse_statement(Parser *parser);

static Node *parse_primary(Parser *parser) {
    const Token *token;
    Node *node;
    if (parser_check(parser, TK_INTEGER)) {
        token = parser_advance(parser);
        node = parser_node(parser, NODE_INTEGER, *token);
        if (node != NULL) {
            node->value = token->value;
        }
        return node;
    }
    if (parser_check(parser, TK_IDENTIFIER)) {
        token = parser_advance(parser);
        return parser_node(parser, NODE_VARIABLE, *token);
    }
    if (parser_check(parser, TK_LPAREN)) {
        const Token *opening = parser_advance(parser);
        if (!parser_enter(parser, opening)) {
            return NULL;
        }
        node = parse_expression(parser);
        if (node != NULL) {
            (void)parser_consume(parser, TK_RPAREN, "expected ')' after expression");
        }
        --parser->depth;
        return parser->error[0] == '\0' ? node : NULL;
    }
    parser_fail(parser, parser_current(parser), "expected expression");
    return NULL;
}

static Node *parse_unary(Parser *parser) {
    if (parser_check(parser, TK_PLUS) || parser_check(parser, TK_MINUS)) {
        const Token *operation = parser_advance(parser);
        Node *operand;
        Node *node;
        if (!parser_enter(parser, operation)) {
            return NULL;
        }
        operand = parse_unary(parser);
        --parser->depth;
        if (operand == NULL) {
            return NULL;
        }
        node = parser_node(parser, NODE_UNARY, *operation);
        if (node != NULL) {
            node->operation = operation->kind;
            node->a = operand;
        }
        return node;
    }
    return parse_primary(parser);
}

typedef Node *(*ParseLevel)(Parser *parser);

static bool kind_in(TokenKind kind, const TokenKind *kinds, size_t count) {
    size_t i;
    for (i = 0; i < count; ++i) {
        if (kind == kinds[i]) {
            return true;
        }
    }
    return false;
}

static Node *parse_left_associative(Parser *parser, ParseLevel tighter,
                                    const TokenKind *operators,
                                    size_t operator_count) {
    Node *left = tighter(parser);
    while (left != NULL &&
           kind_in(parser_current(parser)->kind, operators, operator_count)) {
        const Token *operation = parser_advance(parser);
        Node *right = tighter(parser);
        Node *combined;
        if (right == NULL) {
            return NULL;
        }
        combined = parser_node(parser, NODE_BINARY, *operation);
        if (combined == NULL) {
            return NULL;
        }
        combined->operation = operation->kind;
        combined->a = left;
        combined->b = right;
        left = combined;
    }
    return left;
}

static Node *parse_factor(Parser *parser) {
    static const TokenKind operators[] = {TK_STAR, TK_SLASH, TK_PERCENT};
    return parse_left_associative(parser, parse_unary, operators,
                                  sizeof(operators) / sizeof(operators[0]));
}

static Node *parse_term(Parser *parser) {
    static const TokenKind operators[] = {TK_PLUS, TK_MINUS};
    return parse_left_associative(parser, parse_factor, operators,
                                  sizeof(operators) / sizeof(operators[0]));
}

static Node *parse_comparison(Parser *parser) {
    static const TokenKind operators[] = {TK_LESS, TK_LESS_EQUAL, TK_GREATER,
                                           TK_GREATER_EQUAL};
    return parse_left_associative(parser, parse_term, operators,
                                  sizeof(operators) / sizeof(operators[0]));
}

static Node *parse_equality(Parser *parser) {
    static const TokenKind operators[] = {TK_EQUAL_EQUAL, TK_BANG_EQUAL};
    return parse_left_associative(parser, parse_comparison, operators,
                                  sizeof(operators) / sizeof(operators[0]));
}

static Node *parse_expression(Parser *parser) {
    return parse_equality(parser);
}

static Node *parse_block(Parser *parser) {
    const Token *opening = parser_consume(parser, TK_LBRACE, "expected '{'");
    Node *head = NULL;
    Node *tail = NULL;
    if (opening == NULL || !parser_enter(parser, opening)) {
        return NULL;
    }
    while (!parser_check(parser, TK_RBRACE) && !parser_check(parser, TK_EOF) &&
           parser->error[0] == '\0') {
        Node *statement = parse_statement(parser);
        if (statement == NULL) {
            break;
        }
        if (tail == NULL) {
            head = statement;
        } else {
            tail->next = statement;
        }
        tail = statement;
    }
    if (parser->error[0] == '\0') {
        (void)parser_consume(parser, TK_RBRACE, "expected '}' after block");
    }
    --parser->depth;
    return parser->error[0] == '\0' ? head : NULL;
}

static Node *parse_statement(Parser *parser) {
    const Token *keyword;
    const Token *name;
    Node *expression;
    Node *node;

    if (parser_check(parser, TK_LET)) {
        keyword = parser_advance(parser);
        (void)keyword;
        name = parser_consume(parser, TK_IDENTIFIER,
                              "expected identifier after 'let'");
        if (name == NULL ||
            parser_consume(parser, TK_ASSIGN, "expected '=' after identifier") ==
                NULL) {
            return NULL;
        }
        expression = parse_expression(parser);
        if (expression == NULL ||
            parser_consume(parser, TK_SEMICOLON,
                           "expected ';' after declaration") == NULL) {
            return NULL;
        }
        node = parser_node(parser, NODE_LET, *name);
        if (node != NULL) {
            node->a = expression;
        }
        return node;
    }

    if (parser_check(parser, TK_IDENTIFIER)) {
        name = parser_advance(parser);
        if (parser_consume(parser, TK_ASSIGN,
                           "expected '=' after assignment name") == NULL) {
            return NULL;
        }
        expression = parse_expression(parser);
        if (expression == NULL ||
            parser_consume(parser, TK_SEMICOLON,
                           "expected ';' after assignment") == NULL) {
            return NULL;
        }
        node = parser_node(parser, NODE_ASSIGN, *name);
        if (node != NULL) {
            node->a = expression;
        }
        return node;
    }

    if (parser_check(parser, TK_PRINT)) {
        keyword = parser_advance(parser);
        expression = parse_expression(parser);
        if (expression == NULL ||
            parser_consume(parser, TK_SEMICOLON, "expected ';' after print") ==
                NULL) {
            return NULL;
        }
        node = parser_node(parser, NODE_PRINT, *keyword);
        if (node != NULL) {
            node->a = expression;
        }
        return node;
    }

    if (parser_check(parser, TK_IF)) {
        Node *condition;
        Node *then_branch;
        Node *else_branch = NULL;
        keyword = parser_advance(parser);
        if (parser_consume(parser, TK_LPAREN, "expected '(' after 'if'") == NULL) {
            return NULL;
        }
        condition = parse_expression(parser);
        if (condition == NULL ||
            parser_consume(parser, TK_RPAREN,
                           "expected ')' after if condition") == NULL) {
            return NULL;
        }
        then_branch = parse_block(parser);
        if (parser->error[0] != '\0') {
            return NULL;
        }
        if (parser_check(parser, TK_ELSE)) {
            (void)parser_advance(parser);
            else_branch = parse_block(parser);
            if (parser->error[0] != '\0') {
                return NULL;
            }
        }
        node = parser_node(parser, NODE_IF, *keyword);
        if (node != NULL) {
            node->a = condition;
            node->b = then_branch;
            node->c = else_branch;
        }
        return node;
    }

    if (parser_check(parser, TK_WHILE)) {
        Node *condition;
        Node *body;
        keyword = parser_advance(parser);
        if (parser_consume(parser, TK_LPAREN,
                           "expected '(' after 'while'") == NULL) {
            return NULL;
        }
        condition = parse_expression(parser);
        if (condition == NULL ||
            parser_consume(parser, TK_RPAREN,
                           "expected ')' after while condition") == NULL) {
            return NULL;
        }
        body = parse_block(parser);
        if (parser->error[0] != '\0') {
            return NULL;
        }
        node = parser_node(parser, NODE_WHILE, *keyword);
        if (node != NULL) {
            node->a = condition;
            node->b = body;
        }
        return node;
    }

    parser_fail(parser, parser_current(parser), "expected statement");
    return NULL;
}

static Node *parse_program(Parser *parser) {
    Node *head = NULL;
    Node *tail = NULL;
    while (!parser_check(parser, TK_EOF) && parser->error[0] == '\0') {
        Node *statement = parse_statement(parser);
        if (statement == NULL) {
            return NULL;
        }
        if (tail == NULL) {
            head = statement;
        } else {
            tail->next = statement;
        }
        tail = statement;
    }
    return parser->error[0] == '\0' ? head : NULL;
}

typedef struct {
    Token names[VARIABLE_LIMIT];
    size_t count;
    char error[192];
} Validator;

static bool same_name(Token a, Token b) {
    return a.length == b.length && memcmp(a.start, b.start, a.length) == 0;
}

static int validator_find(const Validator *validator, Token name) {
    size_t i;
    for (i = 0; i < validator->count; ++i) {
        if (same_name(validator->names[i], name)) {
            return (int)i;
        }
    }
    return -1;
}

static void validation_fail(Validator *validator, Token token, const char *format,
                            ...) {
    char detail[112];
    va_list arguments;
    if (validator->error[0] != '\0') {
        return;
    }
    va_start(arguments, format);
    (void)vsnprintf(detail, sizeof(detail), format, arguments);
    va_end(arguments);
    snprintf(validator->error, sizeof(validator->error), "%zu:%zu: %s", token.line,
             token.column, detail);
}

static bool validate_expression(Validator *validator, Node *node,
                                unsigned depth) {
    int slot;
    if (node == NULL) {
        return true;
    }
    if (depth > DEPTH_LIMIT) {
        validation_fail(validator, node->token,
                        "expression tree depth limit exceeded");
        return false;
    }
    switch (node->kind) {
        case NODE_INTEGER:
            return true;
        case NODE_VARIABLE:
            slot = validator_find(validator, node->token);
            if (slot < 0) {
                validation_fail(validator, node->token,
                                "name '%.*s' is not declared",
                                (int)node->token.length, node->token.start);
                return false;
            }
            node->slot = slot;
            return true;
        case NODE_UNARY:
            return validate_expression(validator, node->a, depth + 1);
        case NODE_BINARY:
            return validate_expression(validator, node->a, depth + 1) &&
                   validate_expression(validator, node->b, depth + 1);
        default:
            validation_fail(validator, node->token,
                            "internal node appeared where expression was expected");
            return false;
    }
}

static bool validate_statements(Validator *validator, Node *statement) {
    for (; statement != NULL; statement = statement->next) {
        int slot;
        switch (statement->kind) {
            case NODE_LET:
                if (!validate_expression(validator, statement->a, 1)) {
                    return false;
                }
                if (validator_find(validator, statement->token) >= 0) {
                    validation_fail(validator, statement->token,
                                    "name '%.*s' is already declared",
                                    (int)statement->token.length,
                                    statement->token.start);
                    return false;
                }
                if (validator->count >= VARIABLE_LIMIT) {
                    validation_fail(validator, statement->token,
                                    "variable limit exceeded");
                    return false;
                }
                validator->names[validator->count] = statement->token;
                statement->slot = (int)validator->count;
                ++validator->count;
                break;
            case NODE_ASSIGN:
                slot = validator_find(validator, statement->token);
                if (slot < 0) {
                    validation_fail(validator, statement->token,
                                    "name '%.*s' is not declared",
                                    (int)statement->token.length,
                                    statement->token.start);
                    return false;
                }
                statement->slot = slot;
                if (!validate_expression(validator, statement->a, 1)) {
                    return false;
                }
                break;
            case NODE_PRINT:
                if (!validate_expression(validator, statement->a, 1)) {
                    return false;
                }
                break;
            case NODE_IF:
                if (!validate_expression(validator, statement->a, 1) ||
                    !validate_statements(validator, statement->b) ||
                    !validate_statements(validator, statement->c)) {
                    return false;
                }
                break;
            case NODE_WHILE:
                if (!validate_expression(validator, statement->a, 1) ||
                    !validate_statements(validator, statement->b)) {
                    return false;
                }
                break;
            default:
                validation_fail(validator, statement->token,
                                "internal expression appeared as statement");
                return false;
        }
    }
    return true;
}

static int64_t bits_to_signed(uint64_t bits) {
    int64_t value;
    memcpy(&value, &bits, sizeof(value));
    return value;
}

static uint64_t signed_to_bits(int64_t value) {
    uint64_t bits;
    memcpy(&bits, &value, sizeof(bits));
    return bits;
}

typedef struct {
    uint64_t variables[VARIABLE_LIMIT];
    uint64_t steps;
    char error[192];
} Interpreter;

static void runtime_fail(Interpreter *interpreter, Token token,
                         const char *message) {
    if (interpreter->error[0] == '\0') {
        snprintf(interpreter->error, sizeof(interpreter->error), "%zu:%zu: %s",
                 token.line, token.column, message);
    }
}

static uint64_t evaluate(Interpreter *interpreter, const Node *node) {
    uint64_t left;
    uint64_t right;
    int64_t signed_left;
    int64_t signed_right;

    switch (node->kind) {
        case NODE_INTEGER:
            return node->value;
        case NODE_VARIABLE:
            return interpreter->variables[node->slot];
        case NODE_UNARY:
            left = evaluate(interpreter, node->a);
            if (interpreter->error[0] != '\0') {
                return 0;
            }
            return node->operation == TK_MINUS ? UINT64_C(0) - left : left;
        case NODE_BINARY:
            left = evaluate(interpreter, node->a);
            if (interpreter->error[0] != '\0') {
                return 0;
            }
            right = evaluate(interpreter, node->b);
            if (interpreter->error[0] != '\0') {
                return 0;
            }
            signed_left = bits_to_signed(left);
            signed_right = bits_to_signed(right);
            switch (node->operation) {
                case TK_PLUS:
                    return left + right;
                case TK_MINUS:
                    return left - right;
                case TK_STAR:
                    return left * right;
                case TK_SLASH:
                    if (right == 0) {
                        runtime_fail(interpreter, node->token, "division by zero");
                        return 0;
                    }
                    if (signed_left == INT64_MIN && signed_right == -1) {
                        return signed_to_bits(INT64_MIN);
                    }
                    return signed_to_bits(signed_left / signed_right);
                case TK_PERCENT:
                    if (right == 0) {
                        runtime_fail(interpreter, node->token, "division by zero");
                        return 0;
                    }
                    if (signed_left == INT64_MIN && signed_right == -1) {
                        return 0;
                    }
                    return signed_to_bits(signed_left % signed_right);
                case TK_EQUAL_EQUAL:
                    return left == right ? 1 : 0;
                case TK_BANG_EQUAL:
                    return left != right ? 1 : 0;
                case TK_LESS:
                    return signed_left < signed_right ? 1 : 0;
                case TK_LESS_EQUAL:
                    return signed_left <= signed_right ? 1 : 0;
                case TK_GREATER:
                    return signed_left > signed_right ? 1 : 0;
                case TK_GREATER_EQUAL:
                    return signed_left >= signed_right ? 1 : 0;
                default:
                    runtime_fail(interpreter, node->token,
                                 "unknown binary operation");
                    return 0;
            }
        default:
            runtime_fail(interpreter, node->token,
                         "statement node used as expression");
            return 0;
    }
}

static bool execute_statements(Interpreter *interpreter, const Node *statement);

static bool execution_tick(Interpreter *interpreter, Token token) {
    ++interpreter->steps;
    if (interpreter->steps > STEP_LIMIT) {
        runtime_fail(interpreter, token, "execution step limit exceeded");
        return false;
    }
    return true;
}

static bool execute_statement(Interpreter *interpreter, const Node *statement) {
    uint64_t value;
    if (!execution_tick(interpreter, statement->token)) {
        return false;
    }
    switch (statement->kind) {
        case NODE_LET:
        case NODE_ASSIGN:
            value = evaluate(interpreter, statement->a);
            if (interpreter->error[0] != '\0') {
                return false;
            }
            interpreter->variables[statement->slot] = value;
            return true;
        case NODE_PRINT:
            value = evaluate(interpreter, statement->a);
            if (interpreter->error[0] != '\0') {
                return false;
            }
            if (printf("%" PRId64 "\n", bits_to_signed(value)) < 0) {
                runtime_fail(interpreter, statement->token,
                             "could not write program output");
                return false;
            }
            return true;
        case NODE_IF:
            value = evaluate(interpreter, statement->a);
            if (interpreter->error[0] != '\0') {
                return false;
            }
            return execute_statements(interpreter, value != 0 ? statement->b
                                                               : statement->c);
        case NODE_WHILE:
            for (;;) {
                value = evaluate(interpreter, statement->a);
                if (interpreter->error[0] != '\0') {
                    return false;
                }
                if (value == 0) {
                    return true;
                }
                if (!execute_statements(interpreter, statement->b)) {
                    return false;
                }
                if (!execution_tick(interpreter, statement->token)) {
                    return false;
                }
            }
        default:
            runtime_fail(interpreter, statement->token,
                         "expression node used as statement");
            return false;
    }
}

static bool execute_statements(Interpreter *interpreter, const Node *statement) {
    for (; statement != NULL; statement = statement->next) {
        if (!execute_statement(interpreter, statement)) {
            return false;
        }
    }
    return true;
}

typedef struct {
    FILE *output;
    unsigned next_label;
    bool failed;
} Emitter;

static void emit(Emitter *emitter, const char *format, ...) {
    va_list arguments;
    if (emitter->failed) {
        return;
    }
    va_start(arguments, format);
    if (vfprintf(emitter->output, format, arguments) < 0) {
        emitter->failed = true;
    }
    va_end(arguments);
}

static unsigned fresh_label(Emitter *emitter) {
    return emitter->next_label++;
}

static void emit_expression(Emitter *emitter, const Node *node) {
    unsigned normal_label;
    unsigned end_label;
    switch (node->kind) {
        case NODE_INTEGER:
            emit(emitter, "    movabsq $0x%016" PRIx64 ", %%rax\n", node->value);
            return;
        case NODE_VARIABLE:
            emit(emitter, "    movq -%d(%%rbp), %%rax\n", 8 * (node->slot + 1));
            return;
        case NODE_UNARY:
            emit_expression(emitter, node->a);
            if (node->operation == TK_MINUS) {
                emit(emitter, "    negq %%rax\n");
            }
            return;
        case NODE_BINARY:
            emit_expression(emitter, node->a);
            emit(emitter, "    pushq %%rax\n");
            emit_expression(emitter, node->b);
            emit(emitter, "    movq %%rax, %%rcx\n    popq %%rax\n");
            switch (node->operation) {
                case TK_PLUS:
                    emit(emitter, "    addq %%rcx, %%rax\n");
                    return;
                case TK_MINUS:
                    emit(emitter, "    subq %%rcx, %%rax\n");
                    return;
                case TK_STAR:
                    emit(emitter, "    imulq %%rcx, %%rax\n");
                    return;
                case TK_SLASH:
                case TK_PERCENT:
                    normal_label = fresh_label(emitter);
                    end_label = fresh_label(emitter);
                    emit(emitter,
                         "    testq %%rcx, %%rcx\n"
                         "    je .Lmica_divzero\n"
                         "    movabsq $0x8000000000000000, %%rdx\n"
                         "    cmpq %%rdx, %%rax\n"
                         "    jne .L%u\n"
                         "    cmpq $-1, %%rcx\n"
                         "    jne .L%u\n",
                         normal_label, normal_label);
                    if (node->operation == TK_PERCENT) {
                        emit(emitter, "    xorl %%eax, %%eax\n");
                    }
                    emit(emitter, "    jmp .L%u\n.L%u:\n", end_label,
                         normal_label);
                    emit(emitter, "    cqto\n    idivq %%rcx\n");
                    if (node->operation == TK_PERCENT) {
                        emit(emitter, "    movq %%rdx, %%rax\n");
                    }
                    emit(emitter, ".L%u:\n", end_label);
                    return;
                case TK_EQUAL_EQUAL:
                    emit(emitter,
                         "    cmpq %%rcx, %%rax\n    sete %%al\n"
                         "    movzbq %%al, %%rax\n");
                    return;
                case TK_BANG_EQUAL:
                    emit(emitter,
                         "    cmpq %%rcx, %%rax\n    setne %%al\n"
                         "    movzbq %%al, %%rax\n");
                    return;
                case TK_LESS:
                    emit(emitter,
                         "    cmpq %%rcx, %%rax\n    setl %%al\n"
                         "    movzbq %%al, %%rax\n");
                    return;
                case TK_LESS_EQUAL:
                    emit(emitter,
                         "    cmpq %%rcx, %%rax\n    setle %%al\n"
                         "    movzbq %%al, %%rax\n");
                    return;
                case TK_GREATER:
                    emit(emitter,
                         "    cmpq %%rcx, %%rax\n    setg %%al\n"
                         "    movzbq %%al, %%rax\n");
                    return;
                case TK_GREATER_EQUAL:
                    emit(emitter,
                         "    cmpq %%rcx, %%rax\n    setge %%al\n"
                         "    movzbq %%al, %%rax\n");
                    return;
                default:
                    emitter->failed = true;
                    return;
            }
        default:
            emitter->failed = true;
            return;
    }
}

static void emit_step_tick(Emitter *emitter, size_t step_offset) {
    emit(emitter,
         "    addq $1, -%zu(%%rbp)\n"
         "    cmpq $10000000, -%zu(%%rbp)\n"
         "    ja .Lmica_step_limit\n",
         step_offset, step_offset);
}

static void emit_statements(Emitter *emitter, const Node *statement,
                            size_t step_offset) {
    for (; statement != NULL; statement = statement->next) {
        unsigned first_label;
        unsigned second_label;
        if (statement->kind == NODE_WHILE) {
            first_label = fresh_label(emitter);
            second_label = fresh_label(emitter);
            emit(emitter, ".L%u:\n", first_label);
            emit_step_tick(emitter, step_offset);
            emit_expression(emitter, statement->a);
            emit(emitter, "    testq %%rax, %%rax\n    je .L%u\n",
                 second_label);
            emit_statements(emitter, statement->b, step_offset);
            emit(emitter, "    jmp .L%u\n.L%u:\n", first_label,
                 second_label);
            continue;
        }
        emit_step_tick(emitter, step_offset);
        switch (statement->kind) {
            case NODE_LET:
            case NODE_ASSIGN:
                emit_expression(emitter, statement->a);
                emit(emitter, "    movq %%rax, -%d(%%rbp)\n",
                     8 * (statement->slot + 1));
                break;
            case NODE_PRINT:
                emit_expression(emitter, statement->a);
                emit(emitter,
                     "    movq %%rax, %%rsi\n"
                     "    leaq .Lmica_format(%%rip), %%rdi\n"
                     "    xorl %%eax, %%eax\n"
                     "    call printf@PLT\n");
                break;
            case NODE_IF:
                first_label = fresh_label(emitter);
                second_label = fresh_label(emitter);
                emit_expression(emitter, statement->a);
                emit(emitter, "    testq %%rax, %%rax\n    je .L%u\n",
                     first_label);
                emit_statements(emitter, statement->b, step_offset);
                emit(emitter, "    jmp .L%u\n.L%u:\n", second_label,
                     first_label);
                emit_statements(emitter, statement->c, step_offset);
                emit(emitter, ".L%u:\n", second_label);
                break;
            default:
                emitter->failed = true;
                return;
        }
    }
}

static bool emit_program(FILE *output, const Node *program, size_t variable_count) {
    Emitter emitter;
    size_t slot;
    size_t step_offset = (variable_count + 1) * 8;
    size_t frame_size = ((step_offset + 15) / 16) * 16;
    memset(&emitter, 0, sizeof(emitter));
    emitter.output = output;

    emit(&emitter,
         ".section .rodata\n"
         ".Lmica_format:\n"
         "    .asciz \"%%ld\\n\"\n"
         ".Lmica_division_message:\n"
         "    .asciz \"mica: runtime error: division by zero\\n\"\n"
         ".Lmica_step_message:\n"
         "    .asciz \"mica: runtime error: execution step limit exceeded\\n\"\n"
         ".text\n"
         ".globl main\n"
         ".type main, @function\n"
         "main:\n"
         "    pushq %%rbp\n"
         "    movq %%rsp, %%rbp\n");
    if (frame_size != 0) {
        emit(&emitter, "    subq $%zu, %%rsp\n", frame_size);
    }
    for (slot = 0; slot < variable_count; ++slot) {
        emit(&emitter, "    movq $0, -%zu(%%rbp)\n", 8 * (slot + 1));
    }
    emit(&emitter, "    movq $0, -%zu(%%rbp)\n", step_offset);
    emit_statements(&emitter, program, step_offset);
    emit(&emitter,
         "    xorl %%eax, %%eax\n"
         "    leave\n"
         "    ret\n"
         ".Lmica_divzero:\n"
         "    movq %%rbp, %%rsp\n"
         "    leaq .Lmica_division_message(%%rip), %%rdi\n"
         "    movq stderr(%%rip), %%rsi\n"
         "    call fputs@PLT\n"
         "    movl $1, %%eax\n"
         "    leave\n"
         "    ret\n"
         ".Lmica_step_limit:\n"
         "    movq %%rbp, %%rsp\n"
         "    leaq .Lmica_step_message(%%rip), %%rdi\n"
         "    movq stderr(%%rip), %%rsi\n"
         "    call fputs@PLT\n"
         "    movl $1, %%eax\n"
         "    leave\n"
         "    ret\n"
         ".size main, .-main\n"
         ".section .note.GNU-stack,\"\",@progbits\n");
    return !emitter.failed && !ferror(output);
}

static bool read_source_file(const char *path, char **buffer_out, size_t *length_out,
                             char *error, size_t error_size) {
    FILE *input = fopen(path, "rb");
    char *buffer;
    size_t count;
    if (input == NULL) {
        snprintf(error, error_size, "cannot open input file");
        return false;
    }
    buffer = (char *)malloc(SOURCE_LIMIT + 2);
    if (buffer == NULL) {
        (void)fclose(input);
        snprintf(error, error_size, "out of memory while reading input");
        return false;
    }
    count = fread(buffer, 1, SOURCE_LIMIT + 1, input);
    if (ferror(input)) {
        free(buffer);
        (void)fclose(input);
        snprintf(error, error_size, "cannot read input file");
        return false;
    }
    if (count > SOURCE_LIMIT) {
        free(buffer);
        (void)fclose(input);
        snprintf(error, error_size, "source exceeds 1048576-byte limit");
        return false;
    }
    if (fclose(input) != 0) {
        free(buffer);
        snprintf(error, error_size, "cannot close input file");
        return false;
    }
    buffer[count] = '\0';
    *buffer_out = buffer;
    *length_out = count;
    return true;
}

static void report_error(const char *phase, const char *message) {
    fprintf(stderr, "mica: %s error: %s\n", phase, message);
}

static int show_tokens(const TokenList *tokens) {
    size_t i;
    for (i = 0; i < tokens->count; ++i) {
        const Token *token = &tokens->items[i];
        if (token->kind == TK_EOF) {
            printf("%zu:%zu %s -\n", token->line, token->column,
                   token_kind_name(token->kind));
        } else if (token->kind == TK_INTEGER) {
            printf("%zu:%zu %s %" PRIu64 "\n", token->line, token->column,
                   token_kind_name(token->kind), token->value);
        } else {
            printf("%zu:%zu %s %.*s\n", token->line, token->column,
                   token_kind_name(token->kind), (int)token->length,
                   token->start);
        }
    }
    if (ferror(stdout)) {
        report_error("I/O", "could not write token output");
        return 1;
    }
    return 0;
}

static void usage(void) {
    fprintf(stderr,
            "mica: usage error: expected 'mica tokens FILE', 'mica run FILE', "
            "or 'mica compile FILE -o OUTPUT.s'\n");
}

int main(int argc, char **argv) {
    enum { MODE_TOKENS, MODE_RUN, MODE_COMPILE } mode;
    const char *input_path;
    const char *output_path = NULL;
    char *source = NULL;
    size_t source_length = 0;
    char io_error[160];
    TokenList tokens;
    Parser parser;
    Validator validator;
    Node *program;
    int result = 1;

    if (argc == 3 && strcmp(argv[1], "tokens") == 0) {
        mode = MODE_TOKENS;
    } else if (argc == 3 && strcmp(argv[1], "run") == 0) {
        mode = MODE_RUN;
    } else if (argc == 5 && strcmp(argv[1], "compile") == 0 &&
               strcmp(argv[3], "-o") == 0) {
        mode = MODE_COMPILE;
        output_path = argv[4];
    } else {
        usage();
        return 2;
    }
    input_path = argv[2];

    memset(io_error, 0, sizeof(io_error));
    if (!read_source_file(input_path, &source, &source_length, io_error,
                          sizeof(io_error))) {
        report_error("I/O", io_error);
        return 1;
    }

    memset(&tokens, 0, sizeof(tokens));
    if (!lex_source(source, source_length, &tokens)) {
        report_error("lexical", tokens.error);
        goto cleanup_source;
    }
    if (mode == MODE_TOKENS) {
        result = show_tokens(&tokens);
        goto cleanup_tokens;
    }

    memset(&parser, 0, sizeof(parser));
    parser.tokens = &tokens;
    parser.arena = (Node *)calloc(NODE_LIMIT, sizeof(*parser.arena));
    if (parser.arena == NULL) {
        report_error("parse", "out of memory while allocating AST");
        goto cleanup_tokens;
    }
    program = parse_program(&parser);
    if (parser.error[0] != '\0') {
        report_error("parse", parser.error);
        goto cleanup_parser;
    }

    memset(&validator, 0, sizeof(validator));
    if (!validate_statements(&validator, program)) {
        report_error("validation", validator.error);
        goto cleanup_parser;
    }

    if (mode == MODE_RUN) {
        Interpreter interpreter;
        memset(&interpreter, 0, sizeof(interpreter));
        if (!execute_statements(&interpreter, program)) {
            report_error("runtime", interpreter.error);
            goto cleanup_parser;
        }
        result = 0;
    } else {
        FILE *output = fopen(output_path, "wb");
        bool emitted;
        if (output == NULL) {
            report_error("I/O", "cannot open assembly output file");
            goto cleanup_parser;
        }
        emitted = emit_program(output, program, validator.count);
        if (fclose(output) != 0) {
            emitted = false;
        }
        if (!emitted) {
            report_error("I/O", "could not write assembly output");
            goto cleanup_parser;
        }
        result = 0;
    }

cleanup_parser:
    free(parser.arena);
cleanup_tokens:
    free(tokens.items);
cleanup_source:
    free(source);
    return result;
}
