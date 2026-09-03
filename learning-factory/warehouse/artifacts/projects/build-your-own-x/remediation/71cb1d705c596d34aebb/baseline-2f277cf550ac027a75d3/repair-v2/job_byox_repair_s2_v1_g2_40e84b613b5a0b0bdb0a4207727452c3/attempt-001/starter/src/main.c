#define _POSIX_C_SOURCE 200809L

#include "msh.h"

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static int run_line(struct shell *shell, const char *line) {
    int status = execute_line(shell, line);
    shell->last_status = status;
    return status;
}

int main(int argc, char **argv) {
    struct shell shell = {0};

    if (argc == 3 && strcmp(argv[1], "-c") == 0) {
        int status = run_line(&shell, argv[2]);
        return shell.should_exit ? shell.exit_status : status;
    }
    if (argc != 1) {
        fprintf(stderr, "usage: msh [-c command]\n");
        return 2;
    }

    char *line = NULL;
    size_t capacity = 0;
    bool interactive = isatty(STDIN_FILENO) && isatty(STDERR_FILENO);
    while (!shell.should_exit) {
        if (interactive) {
            fputs("msh$ ", stderr);
            fflush(stderr);
        }
        errno = 0;
        ssize_t length = getline(&line, &capacity, stdin);
        if (length < 0) {
            if (errno == EINTR) {
                clearerr(stdin);
                continue;
            }
            if (ferror(stdin)) {
                fprintf(stderr, "msh: read: %s\n", strerror(errno));
                shell.last_status = 1;
            }
            break;
        }
        if (length > 0 && line[length - 1] == '\n') {
            line[length - 1] = '\0';
        }
        run_line(&shell, line);
    }
    free(line);
    return shell.should_exit ? shell.exit_status : shell.last_status;
}
