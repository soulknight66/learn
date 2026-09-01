#include <stddef.h>

#include "executor.h"
#include "lexer.h"
#include "parser.h"
#include "shell.h"

int main(void)
{
    TokenList tokens;
    CommandList list;
    ShellState state;
    ShellError error;
    int failed = 0;

    token_list_init(&tokens);
    command_list_init(&list);
    shell_state_init(&state);
    shell_error_clear(&error);

    if (lexer_tokenize(" \t\n", &tokens, &error) != SHELL_RESULT_OK) {
        failed = 1;
    } else if (tokens.length != 1U || tokens.items[0].kind != TOKEN_END) {
        failed = 1;
    } else if (parser_parse_list(" \t\n", &tokens, &list, &error) !=
               SHELL_RESULT_OK) {
        failed = 1;
    } else if (executor_run_list(&list, &state, &error) != SHELL_RESULT_OK) {
        failed = 1;
    } else if (state.last_status != 0) {
        failed = 1;
    }

    command_list_destroy(&list);
    token_list_destroy(&tokens);
    shell_state_destroy(&state);
    return failed;
}
