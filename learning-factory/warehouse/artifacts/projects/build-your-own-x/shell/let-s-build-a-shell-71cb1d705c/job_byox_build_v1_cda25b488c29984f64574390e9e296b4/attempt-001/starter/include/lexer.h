#ifndef MINISH_LEXER_H
#define MINISH_LEXER_H

#include <stddef.h>

#include "shell.h"

typedef enum {
    TOKEN_WORD = 0,
    TOKEN_PIPE,
    TOKEN_REDIRECT_IN,
    TOKEN_REDIRECT_OUT,
    TOKEN_REDIRECT_APPEND,
    TOKEN_SEQUENCE,
    TOKEN_BACKGROUND,
    TOKEN_END
} TokenKind;

typedef struct {
    TokenKind kind;
    char *text;
    size_t offset;
} Token;

typedef struct {
    Token *items;
    size_t length;
    size_t capacity;
} TokenList;

void token_list_init(TokenList *tokens);
void token_list_destroy(TokenList *tokens);
const char *token_kind_name(TokenKind kind);

/*
 * Append tokens for line, including one TOKEN_END. The list must have been
 * initialized by token_list_init. Token text, when present, belongs to list.
 */
ShellResult lexer_tokenize(const char *line, TokenList *tokens,
                           ShellError *error);

#endif
