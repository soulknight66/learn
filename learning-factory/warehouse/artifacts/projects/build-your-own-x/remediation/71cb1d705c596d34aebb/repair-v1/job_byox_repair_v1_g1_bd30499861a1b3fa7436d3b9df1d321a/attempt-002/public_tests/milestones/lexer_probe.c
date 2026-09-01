#include <stdio.h>
#include <string.h>

#include "lexer.h"

static int word_is(const Token *token, const char *text)
{
    return token->kind == TOKEN_WORD && token->text != NULL &&
           strcmp(token->text, text) == 0;
}

int main(void)
{
    static const TokenKind kinds[] = {
        TOKEN_WORD, TOKEN_WORD, TOKEN_WORD, TOKEN_REDIRECT_APPEND,
        TOKEN_WORD, TOKEN_BACKGROUND, TOKEN_END
    };
    TokenList tokens;
    ShellError error;
    size_t index;
    int failed = 0;

    token_list_init(&tokens);
    shell_error_clear(&error);
    if (lexer_tokenize("printf 'two words' a\\|b >> out &", &tokens,
                       &error) != SHELL_RESULT_OK) {
        fprintf(stderr, "lexer failed at byte %zu: %s\n", error.offset,
                error.message);
        failed = 1;
        goto done;
    }
    if (tokens.length != sizeof(kinds) / sizeof(kinds[0])) {
        fprintf(stderr, "expected 7 tokens, got %zu\n", tokens.length);
        failed = 1;
        goto done;
    }
    for (index = 0U; index < tokens.length; ++index) {
        if (tokens.items[index].kind != kinds[index]) {
            fprintf(stderr, "token %zu: expected %s, got %s\n", index,
                    token_kind_name(kinds[index]),
                    token_kind_name(tokens.items[index].kind));
            failed = 1;
        }
    }
    if (!word_is(&tokens.items[0], "printf") ||
        !word_is(&tokens.items[1], "two words") ||
        !word_is(&tokens.items[2], "a|b") ||
        !word_is(&tokens.items[4], "out")) {
        fputs("decoded word text did not match the public grammar\n", stderr);
        failed = 1;
    }

done:
    token_list_destroy(&tokens);
    return failed;
}
