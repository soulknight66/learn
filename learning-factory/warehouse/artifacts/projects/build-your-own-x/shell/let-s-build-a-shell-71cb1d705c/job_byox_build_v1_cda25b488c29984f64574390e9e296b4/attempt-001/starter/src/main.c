#include <stdio.h>
#include <string.h>
#include <unistd.h>

#include "shell.h"

static void print_usage(FILE *stream, const char *program)
{
    fprintf(stream,
            "Usage: %s [-c COMMAND]\n"
            "       %s --help\n"
            "\n"
            "Run COMMAND, or read commands from standard input.\n",
            program, program);
}

int main(int argc, char **argv)
{
    ShellState state;
    int status;

    shell_state_init(&state);

    if (argc == 2 && strcmp(argv[1], "--help") == 0) {
        print_usage(stdout, argv[0]);
        status = 0;
        goto done;
    }

    if (argc == 3 && strcmp(argv[1], "-c") == 0) {
        status = shell_run_command_string(argv[2], &state, stderr);
        goto done;
    }

    if (argc != 1) {
        print_usage(stderr, argv[0]);
        status = 2;
        goto done;
    }

    status = shell_repl(stdin, stdout, stderr,
                        isatty(STDIN_FILENO) && isatty(STDOUT_FILENO), &state);

done:
    shell_state_destroy(&state);
    return status;
}
