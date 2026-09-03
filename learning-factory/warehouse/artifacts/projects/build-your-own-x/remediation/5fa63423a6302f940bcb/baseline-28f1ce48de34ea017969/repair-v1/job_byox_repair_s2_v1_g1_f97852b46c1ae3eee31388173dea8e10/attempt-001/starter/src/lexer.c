#include "minish.h"

#include <stdio.h>
#include <stdlib.h>

void token_list_free(TokenList *tokens)
{
    size_t i;

    if (tokens == NULL) {
        return;
    }
    for (i = 0; i < tokens->len; ++i) {
        free(tokens->items[i].text);
    }
    free(tokens->items);
    *tokens = (TokenList){0};
}

int lex_line(const char *line, TokenList *out, char *error, size_t error_size)
{
    if (out != NULL) {
        *out = (TokenList){0};
    }
    if (error != NULL && error_size > 0) {
        (void)snprintf(error, error_size,
                       "lexer is not implemented (input begins with %.16s)",
                       line != NULL ? line : "<null>");
    }

    /* TODO: implement the state machine specified in REQUIREMENTS.md. */
    return -1;
}
