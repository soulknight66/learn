#include "sprig.h"

#include <ctype.h>
#include <inttypes.h>
#include <limits.h>
#include <stdio.h>
#include <string.h>

static int at_end(const Lexer *lexer) {
    return lexer->index >= lexer->length;
}

static unsigned char peek(const Lexer *lexer) {
    return at_end(lexer) ? 0u : lexer->source[lexer->index];
}

static unsigned char advance(Lexer *lexer) {
    unsigned char value = lexer->source[lexer->index++];
    if (value == (unsigned char)'\n') {
        lexer->line++;
        lexer->column = 1u;
    } else {
        lexer->column++;
    }
    return value;
}

static void fail(Lexer *lexer, size_t line, size_t column,
                 const char *message) {
    lexer->error_line = line;
    lexer->error_column = column;
    (void)snprintf(lexer->error, sizeof(lexer->error), "%s", message);
}

static void skip_ignored(Lexer *lexer) {
    for (;;) {
        unsigned char value = peek(lexer);
        if (value == (unsigned char)' ' || value == (unsigned char)'\t' ||
            value == (unsigned char)'\r' || value == (unsigned char)'\n') {
            (void)advance(lexer);
        } else if (value == (unsigned char)'#') {
            while (!at_end(lexer) && peek(lexer) != (unsigned char)'\n') {
                (void)advance(lexer);
            }
        } else {
            return;
        }
    }
}

void lexer_init(Lexer *lexer, const unsigned char *source, size_t length) {
    memset(lexer, 0, sizeof(*lexer));
    lexer->source = source;
    lexer->length = length;
    lexer->line = 1u;
    lexer->column = 1u;
}

static int scan_identifier(Lexer *lexer, Token *token, size_t start) {
    size_t width;

    while (isalnum((int)peek(lexer)) || peek(lexer) == (unsigned char)'_') {
        (void)advance(lexer);
    }
    width = lexer->index - start;
    if (width > SPRIG_MAX_NAME) {
        fail(lexer, token->line, token->column,
             "identifier exceeds 31 bytes");
        return 0;
    }
    memcpy(token->lexeme, lexer->source + start, width);
    token->lexeme[width] = '\0';
    if (strcmp(token->lexeme, "let") == 0) {
        token->kind = TOK_LET;
    } else if (strcmp(token->lexeme, "print") == 0) {
        token->kind = TOK_PRINT;
    } else {
        token->kind = TOK_IDENTIFIER;
    }
    return 1;
}

static int scan_integer(Lexer *lexer, Token *token) {
    int64_t value = 0;

    while (isdigit((int)peek(lexer))) {
        int digit = (int)(advance(lexer) - (unsigned char)'0');
        if (value > (INT64_MAX - digit) / 10) {
            fail(lexer, token->line, token->column,
                 "integer literal exceeds signed 64-bit range");
            return 0;
        }
        value = value * 10 + digit;
    }
    token->kind = TOK_INTEGER;
    token->integer = value;
    return 1;
}

int lexer_next(Lexer *lexer, Token *token) {
    unsigned char value;
    size_t start;

    memset(token, 0, sizeof(*token));
    skip_ignored(lexer);
    token->line = lexer->line;
    token->column = lexer->column;
    if (at_end(lexer)) {
        token->kind = TOK_EOF;
        return 1;
    }

    start = lexer->index;
    value = advance(lexer);
    if (isalpha((int)value) || value == (unsigned char)'_') {
        return scan_identifier(lexer, token, start);
    }
    if (isdigit((int)value)) {
        lexer->index = start;
        lexer->line = token->line;
        lexer->column = token->column;
        return scan_integer(lexer, token);
    }

    switch (value) {
        case '=': token->kind = TOK_EQUAL; break;
        case ';': token->kind = TOK_SEMICOLON; break;
        case '+': token->kind = TOK_PLUS; break;
        case '-': token->kind = TOK_MINUS; break;
        case '*': token->kind = TOK_STAR; break;
        case '/': token->kind = TOK_SLASH; break;
        case '(': token->kind = TOK_LEFT_PAREN; break;
        case ')': token->kind = TOK_RIGHT_PAREN; break;
        default: {
            char message[80];
            if (isprint((int)value)) {
                (void)snprintf(message, sizeof(message),
                               "unexpected byte '%c'", (int)value);
            } else {
                (void)snprintf(message, sizeof(message),
                               "unexpected byte 0x%02x", (unsigned int)value);
            }
            fail(lexer, token->line, token->column, message);
            return 0;
        }
    }
    return 1;
}

const char *token_kind_name(TokenKind kind) {
    static const char *const names[] = {
        "EOF", "INTEGER", "IDENTIFIER", "LET", "PRINT", "EQUAL",
        "SEMICOLON", "PLUS", "MINUS", "STAR", "SLASH", "LEFT_PAREN",
        "RIGHT_PAREN"
    };
    size_t index = (size_t)kind;
    if (index >= sizeof(names) / sizeof(names[0])) {
        return "UNKNOWN";
    }
    return names[index];
}
