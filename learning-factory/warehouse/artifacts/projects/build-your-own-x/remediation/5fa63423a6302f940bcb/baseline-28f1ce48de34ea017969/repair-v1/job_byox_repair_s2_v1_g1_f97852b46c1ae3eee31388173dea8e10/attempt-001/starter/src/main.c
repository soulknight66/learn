#include "minish.h"

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int main(void)
{
    char *line = NULL;
    size_t capacity = 0;
    int last_status = 0;
    const bool interactive = isatty(STDIN_FILENO) != 0;
    const ShellContext context = {
        .interactive = interactive,
        .terminal_fd = STDIN_FILENO,
        .shell_pgid = getpgrp(),
    };

    for (;;) {
        TokenList tokens = {0};
        Pipeline pipeline = {0};
        char error[160] = {0};
        ssize_t length;

        (void)shell_reap_background();
        if (interactive) {
            (void)fputs("minish$ ", stdout);
            (void)fflush(stdout);
        }
        errno = 0;
        length = getline(&line, &capacity, stdin);
        if (length < 0) {
            if (errno == EINTR) {
                clearerr(stdin);
                continue;
            }
            break;
        }
        if (lex_line(line, &tokens, error, sizeof(error)) != 0) {
            (void)fprintf(stderr, "minish: %s\n", error);
            token_list_free(&tokens);
            pipeline_free(&pipeline);
            last_status = 2;
            continue;
        }
        if (parse_pipeline(&tokens, &pipeline, error, sizeof(error)) != 0) {
            (void)fprintf(stderr, "minish: %s\n", error);
            token_list_free(&tokens);
            pipeline_free(&pipeline);
            last_status = 2;
            continue;
        }
        token_list_free(&tokens);

        /* TODO: dispatch cd and exit in the parent before this call. */
        last_status = execute_pipeline(&pipeline, &context);
        pipeline_free(&pipeline);
    }

    free(line);
    return last_status;
}
