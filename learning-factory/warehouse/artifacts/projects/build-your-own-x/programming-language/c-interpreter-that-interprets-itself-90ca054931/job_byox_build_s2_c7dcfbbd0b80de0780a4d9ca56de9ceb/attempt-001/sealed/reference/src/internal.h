#ifndef SEALED_INTERNAL_H
#define SEALED_INTERNAL_H

#include "ember.h"

typedef enum {
    TOK_EOF = 0,
    TOK_ERROR,
    TOK_INTEGER,
    TOK_IDENTIFIER,
    TOK_INT,
    TOK_MAIN,
    TOK_IF,
    TOK_ELSE,
    TOK_WHILE,
    TOK_RETURN,
    TOK_PRINT,
    TOK_ARG,
    TOK_LOAD,
    TOK_STORE,
    TOK_LPAREN,
    TOK_RPAREN,
    TOK_LBRACE,
    TOK_RBRACE,
    TOK_SEMICOLON,
    TOK_COMMA,
    TOK_ASSIGN,
    TOK_PLUS,
    TOK_MINUS,
    TOK_STAR,
    TOK_SLASH,
    TOK_PERCENT,
    TOK_BANG,
    TOK_EQ,
    TOK_NE,
    TOK_LT,
    TOK_LE,
    TOK_GT,
    TOK_GE,
    TOK_AND,
    TOK_OR
} TokenKind;

typedef struct {
    TokenKind kind;
    const char *start;
    size_t length;
    size_t line;
    size_t column;
    int64_t integer;
    const char *message;
} Token;

typedef struct {
    const char *source;
    size_t length;
    size_t offset;
    size_t line;
    size_t column;
} Lexer;

void lexer_init(Lexer *lexer, const char *source, size_t length);
Token lexer_next(Lexer *lexer);
const char *token_kind_name(TokenKind kind);

#endif
