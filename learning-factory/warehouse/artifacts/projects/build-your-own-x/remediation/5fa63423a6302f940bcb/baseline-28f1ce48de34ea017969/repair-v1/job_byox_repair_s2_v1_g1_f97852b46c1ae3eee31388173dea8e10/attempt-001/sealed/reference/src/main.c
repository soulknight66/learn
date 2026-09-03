#include "minish.h"

#include <errno.h>
#include <limits.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static int is_builtin_name(const char *name)
{
    return strcmp(name, "cd") == 0 || strcmp(name, "exit") == 0;
}

static int is_parent_builtin(const Pipeline *pipeline)
{
    const Command *command;

    if (pipeline->count != 1 || pipeline->background) {
        return 0;
    }
    command = &pipeline->commands[0];
    return command->input_path == NULL && command->output_path == NULL &&
           is_builtin_name(command->argv[0]);
}

static int pipeline_contains_builtin(const Pipeline *pipeline)
{
    size_t i;

    for (i = 0; i < pipeline->count; ++i) {
        if (is_builtin_name(pipeline->commands[i].argv[0])) {
            return 1;
        }
    }
    return 0;
}

static int run_cd(const Command *command)
{
    const char *destination;

    if (command->argc > 2) {
        (void)fprintf(stderr, "minish: cd: too many arguments\n");
        return 2;
    }
    destination = command->argc == 2 ? command->argv[1] : getenv("HOME");
    if (destination == NULL || destination[0] == '\0') {
        (void)fprintf(stderr, "minish: cd: HOME is not set\n");
        return 1;
    }
    if (chdir(destination) < 0) {
        perror("minish: cd");
        return 1;
    }
    return 0;
}

static int parse_exit_status(const char *text, int *status)
{
    char *end = NULL;
    long value;

    errno = 0;
    value = strtol(text, &end, 10);
    if (errno != 0 || end == text || *end != '\0' || value < 0 ||
        value > UCHAR_MAX) {
        return -1;
    }
    *status = (int)value;
    return 0;
}

static void ignore_shell_signals(void)
{
    const int signals[] = {SIGINT, SIGQUIT, SIGTSTP, SIGTTIN, SIGTTOU};
    struct sigaction action = {.sa_handler = SIG_IGN};
    size_t i;

    (void)sigemptyset(&action.sa_mask);
    action.sa_flags = 0;
    for (i = 0; i < sizeof(signals) / sizeof(signals[0]); ++i) {
        (void)sigaction(signals[i], &action, NULL);
    }
}

static ShellContext initialize_shell(void)
{
    ShellContext context = {
        .interactive = isatty(STDIN_FILENO) != 0,
        .terminal_fd = STDIN_FILENO,
        .shell_pgid = getpgrp(),
    };

    ignore_shell_signals();
    if (context.interactive) {
        const pid_t self = getpid();

        if (setpgid(0, self) < 0 && errno != EACCES && errno != EPERM) {
            perror("minish: setpgid shell");
        }
        context.shell_pgid = getpgrp();
        if (tcsetpgrp(context.terminal_fd, context.shell_pgid) < 0) {
            perror("minish: tcsetpgrp shell");
        }
    }
    return context;
}

int main(void)
{
    char *line = NULL;
    size_t capacity = 0;
    int last_status = 0;
    const ShellContext context = initialize_shell();

    for (;;) {
        TokenList tokens = {0};
        Pipeline pipeline = {0};
        char error[192] = {0};
        ssize_t length;

        (void)shell_reap_background();
        if (context.interactive) {
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

        if (is_parent_builtin(&pipeline)) {
            const Command *command = &pipeline.commands[0];

            if (strcmp(command->argv[0], "cd") == 0) {
                last_status = run_cd(command);
            } else if (command->argc > 2) {
                (void)fprintf(stderr, "minish: exit: too many arguments\n");
                last_status = 2;
            } else {
                int exit_status = last_status;

                if (command->argc == 2 &&
                    parse_exit_status(command->argv[1], &exit_status) != 0) {
                    (void)fprintf(stderr,
                                  "minish: exit: status must be 0..255\n");
                    last_status = 2;
                } else {
                    pipeline_free(&pipeline);
                    free(line);
                    return exit_status;
                }
            }
        } else if (pipeline_contains_builtin(&pipeline)) {
            (void)fprintf(stderr,
                          "minish: built-in cannot be redirected, piped, or backgrounded\n");
            last_status = 2;
        } else {
            last_status = execute_pipeline(&pipeline, &context);
        }
        pipeline_free(&pipeline);
    }

    free(line);
    return last_status;
}
