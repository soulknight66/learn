#include <ctype.h>
#include <stdlib.h>
#include <string.h>

#include "lexer.h"

void token_list_init(TokenList *tokens)
{
    tokens->items = NULL;
    tokens->length = 0U;
    tokens->capacity = 0U;
}

void token_list_destroy(TokenList *tokens)
{
    size_t index;

    if (tokens == NULL) {
        return;
    }
    for (index = 0U; index < tokens->length; ++index) {
        free(tokens->items[index].text);
    }
    free(tokens->items);
    token_list_init(tokens);
}

const char *token_kind_name(TokenKind kind)
{
    static const char *const names[] = {
        "WORD", "PIPE", "REDIRECT_IN", "REDIRECT_OUT",
        "REDIRECT_APPEND", "SEQUENCE", "BACKGROUND", "END"
    };

    if ((size_t)kind >= sizeof(names) / sizeof(names[0])) {
        return "UNKNOWN";
    }
    return names[kind];
}

static ShellResult append_end_token(TokenList *tokens, size_t offset,
                                    ShellError *error)
{
    Token *new_items = realloc(tokens->items, sizeof(*new_items));

    if (new_items == NULL) {
        shell_error_set(error, offset, "out of memory while storing token");
        return SHELL_RESULT_ERROR;
    }
    tokens->items = new_items;
    tokens->capacity = 1U;
    tokens->items[0].kind = TOKEN_END;
    tokens->items[0].text = NULL;
    tokens->items[0].offset = offset;
    tokens->length = 1U;
    return SHELL_RESULT_OK;
}

ShellResult lexer_tokenize(const char *line, TokenList *tokens,
                           ShellError *error)
{
    size_t offset;

    if (line == NULL || tokens == NULL || tokens->length != 0U) {
        shell_error_set(error, 0U, "invalid lexer input");
        return SHELL_RESULT_ERROR;
    }

    for (offset = 0U; line[offset] != '\0'; ++offset) {
        if (!isspace((unsigned char)line[offset])) {
            /* TODO: recognize words, operators, quoting, and escaping. */
            shell_error_set(error, offset, "tokenization is a TODO");
            return SHELL_RESULT_TODO;
        }
    }

    return append_end_token(tokens, strlen(line), error);
}
