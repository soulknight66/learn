#ifndef PEBBLE_LEXER_H
#define PEBBLE_LEXER_H

#include <stddef.h>
#include <stdint.h>

enum token_kind {
    TOKEN_ERROR,
    TOKEN_EOF,
    TOKEN_INTEGER,
    TOKEN_IDENTIFIER,
    TOKEN_LET,
    TOKEN_PRINT,
    TOKEN_IF,
    TOKEN_ELSE,
    TOKEN_WHILE,
    TOKEN_LPAREN,
    TOKEN_RPAREN,
    TOKEN_LBRACE,
    TOKEN_RBRACE,
    TOKEN_SEMICOLON,
    TOKEN_ASSIGN,
    TOKEN_PLUS,
    TOKEN_MINUS,
    TOKEN_STAR,
    TOKEN_SLASH,
    TOKEN_PERCENT,
    TOKEN_BANG,
    TOKEN_EQUAL_EQUAL,
    TOKEN_BANG_EQUAL,
    TOKEN_LESS,
    TOKEN_LESS_EQUAL,
    TOKEN_GREATER,
    TOKEN_GREATER_EQUAL
};

struct token {
    enum token_kind kind;
    const char *begin;
    size_t length;
    uint32_t line;
    uint32_t column;
    int64_t integer;
};

struct lexer {
    const char *source;
    size_t length;
    size_t offset;
    uint32_t line;
    uint32_t column;
};

void lexer_init(struct lexer *lexer, const char *source, size_t length);
struct token lexer_next(struct lexer *lexer);

#endif
