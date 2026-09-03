#include "ember.h"

#include <ctype.h>
#include <limits.h>
#include <string.h>

static int at_end(const Lexer *lexer) {
    return lexer->offset >= lexer->length;
}

static char peek(const Lexer *lexer) {
    return at_end(lexer) ? '\0' : lexer->source[lexer->offset];
}

static char peek_next(const Lexer *lexer) {
    return lexer->offset + 1U >= lexer->length
               ? '\0'
               : lexer->source[lexer->offset + 1U];
}

static char advance(Lexer *lexer) {
    char value = lexer->source[lexer->offset++];
    if (value == '\n') {
        lexer->line++;
        lexer->column = 1U;
    } else {
        lexer->column++;
    }
    return value;
}

static Token make_token(TokenKind kind, const char *start, size_t length,
                        size_t line, size_t column) {
    Token token;
    token.kind = kind;
    token.start = start;
    token.length = length;
    token.line = line;
    token.column = column;
    token.integer = 0;
    token.message = NULL;
    return token;
}

static Token error_token(const char *start, size_t length, size_t line,
                         size_t column, const char *message) {
    Token token = make_token(TOK_ERROR, start, length, line, column);
    token.message = message;
    return token;
}

void lexer_init(Lexer *lexer, const char *source, size_t length) {
    lexer->source = source;
    lexer->length = length;
    lexer->offset = 0U;
    lexer->line = 1U;
    lexer->column = 1U;
}

static TokenKind keyword_kind(const char *start, size_t length) {
    struct Keyword {
        const char *text;
        size_t length;
        TokenKind kind;
    };
    static const struct Keyword keywords[] = {
        {"int", 3U, TOK_INT},       {"main", 4U, TOK_MAIN},
        {"if", 2U, TOK_IF},         {"else", 4U, TOK_ELSE},
        {"while", 5U, TOK_WHILE},   {"return", 6U, TOK_RETURN},
        {"print", 5U, TOK_PRINT},   {"arg", 3U, TOK_ARG},
        {"load", 4U, TOK_LOAD},     {"store", 5U, TOK_STORE},
    };
    size_t index;
    for (index = 0U; index < sizeof(keywords) / sizeof(keywords[0]); index++) {
        if (length == keywords[index].length &&
            memcmp(start, keywords[index].text, length) == 0) {
            return keywords[index].kind;
        }
    }
    return TOK_IDENTIFIER;
}

static Token scan_identifier(Lexer *lexer, const char *start, size_t line,
                             size_t column) {
    while (isalnum((unsigned char)peek(lexer)) || peek(lexer) == '_') {
        advance(lexer);
    }
    size_t length = (size_t)(&lexer->source[lexer->offset] - start);
    if (length > EMBER_IDENT_MAX) {
        return error_token(start, length, line, column,
                           "identifier exceeds 63 bytes");
    }
    return make_token(keyword_kind(start, length), start, length, line, column);
}

static Token scan_integer(Lexer *lexer, const char *start, size_t line,
                          size_t column) {
    uint64_t value = 0U;
    int overflow = 0;
    while (isdigit((unsigned char)peek(lexer))) {
        unsigned digit = (unsigned)(advance(lexer) - '0');
        if (value > ((uint64_t)INT64_MAX - digit) / 10U) {
            overflow = 1;
        } else if (!overflow) {
            value = value * 10U + digit;
        }
    }
    size_t length = (size_t)(&lexer->source[lexer->offset] - start);
    if (overflow) {
        return error_token(start, length, line, column,
                           "integer literal exceeds INT64_MAX");
    }
    Token token = make_token(TOK_INTEGER, start, length, line, column);
    token.integer = (int64_t)value;
    return token;
}

static Token skip_trivia(Lexer *lexer) {
    for (;;) {
        while (peek(lexer) == ' ' || peek(lexer) == '\t' ||
               peek(lexer) == '\r' || peek(lexer) == '\n' ||
               peek(lexer) == '\f' || peek(lexer) == '\v') {
            advance(lexer);
        }
        if (peek(lexer) == '/' && peek_next(lexer) == '/') {
            while (!at_end(lexer) && peek(lexer) != '\n') {
                advance(lexer);
            }
            continue;
        }
        if (peek(lexer) == '/' && peek_next(lexer) == '*') {
            const char *start = &lexer->source[lexer->offset];
            size_t line = lexer->line;
            size_t column = lexer->column;
            advance(lexer);
            advance(lexer);
            while (!at_end(lexer) &&
                   !(peek(lexer) == '*' && peek_next(lexer) == '/')) {
                advance(lexer);
            }
            if (at_end(lexer)) {
                return error_token(start, 2U, line, column,
                                   "unterminated block comment");
            }
            advance(lexer);
            advance(lexer);
            continue;
        }
        return make_token(TOK_EOF, &lexer->source[lexer->offset], 0U,
                          lexer->line, lexer->column);
    }
}

Token lexer_next(Lexer *lexer) {
    Token trivia = skip_trivia(lexer);
    if (trivia.kind == TOK_ERROR) {
        return trivia;
    }
    if (at_end(lexer)) {
        return trivia;
    }

    const char *start = &lexer->source[lexer->offset];
    size_t line = lexer->line;
    size_t column = lexer->column;
    char first = advance(lexer);

    if (isalpha((unsigned char)first) || first == '_') {
        return scan_identifier(lexer, start, line, column);
    }
    if (isdigit((unsigned char)first)) {
        lexer->offset--;
        lexer->column--;
        return scan_integer(lexer, start, line, column);
    }

#define ONE(kind) return make_token((kind), start, 1U, line, column)
#define PAIR(single_kind, second, pair_kind)                                  \
    do {                                                                       \
        if (peek(lexer) == (second)) {                                         \
            advance(lexer);                                                    \
            return make_token((pair_kind), start, 2U, line, column);          \
        }                                                                      \
        return make_token((single_kind), start, 1U, line, column);            \
    } while (0)

    switch (first) {
    case '(':
        ONE(TOK_LPAREN);
    case ')':
        ONE(TOK_RPAREN);
    case '{':
        ONE(TOK_LBRACE);
    case '}':
        ONE(TOK_RBRACE);
    case ';':
        ONE(TOK_SEMICOLON);
    case ',':
        ONE(TOK_COMMA);
    case '+':
        ONE(TOK_PLUS);
    case '-':
        ONE(TOK_MINUS);
    case '*':
        ONE(TOK_STAR);
    case '/':
        ONE(TOK_SLASH);
    case '%':
        ONE(TOK_PERCENT);
    case '=':
        PAIR(TOK_ASSIGN, '=', TOK_EQ);
    case '!':
        PAIR(TOK_BANG, '=', TOK_NE);
    case '<':
        PAIR(TOK_LT, '=', TOK_LE);
    case '>':
        PAIR(TOK_GT, '=', TOK_GE);
    case '&':
        if (peek(lexer) == '&') {
            advance(lexer);
            return make_token(TOK_AND, start, 2U, line, column);
        }
        return error_token(start, 1U, line, column,
                           "single '&' is not supported");
    case '|':
        if (peek(lexer) == '|') {
            advance(lexer);
            return make_token(TOK_OR, start, 2U, line, column);
        }
        return error_token(start, 1U, line, column,
                           "single '|' is not supported");
    default:
        return error_token(start, 1U, line, column, "unexpected byte");
    }
#undef ONE
#undef PAIR
}

const char *token_kind_name(TokenKind kind) {
    static const char *const names[] = {
        "EOF",       "ERROR",      "INTEGER", "IDENTIFIER", "INT",
        "MAIN",      "IF",         "ELSE",    "WHILE",      "RETURN",
        "PRINT",     "ARG",        "LOAD",    "STORE",      "LPAREN",
        "RPAREN",    "LBRACE",     "RBRACE",  "SEMICOLON",  "COMMA",
        "ASSIGN",    "PLUS",       "MINUS",   "STAR",       "SLASH",
        "PERCENT",   "BANG",       "EQ",      "NE",         "LT",
        "LE",        "GT",         "GE",      "AND",        "OR",
    };
    size_t count = sizeof(names) / sizeof(names[0]);
    return (size_t)kind < count ? names[kind] : "UNKNOWN";
}
