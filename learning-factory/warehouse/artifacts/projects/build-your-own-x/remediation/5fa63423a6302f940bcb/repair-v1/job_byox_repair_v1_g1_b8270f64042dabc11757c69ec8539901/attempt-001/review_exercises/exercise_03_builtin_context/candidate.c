/* Review excerpt: types and helpers are reduced to the relevant fields. */
#include <fcntl.h>
#include <stddef.h>
#include <stdlib.h>
#include <unistd.h>

enum redirect_kind {
    REDIRECT_INPUT,
    REDIRECT_OUTPUT,
    REDIRECT_APPEND
};

struct redirect {
    enum redirect_kind kind;
    const char *path;
};

struct command {
    char **argv;
    struct redirect *redirects;
    size_t redirect_count;
};

struct pipeline {
    struct command *commands;
    size_t command_count;
    int background;
};

int is_builtin(const char *name);
int change_directory(char **argv);
int print_working_directory(void);
int launch_external_pipeline(const struct pipeline *pipeline);

static int run_builtin(struct command *command)
{
    size_t i;

    for (i = 0; i < command->redirect_count; ++i) {
        struct redirect *item = &command->redirects[i];
        int target = item->kind == REDIRECT_INPUT ? STDIN_FILENO : STDOUT_FILENO;
        int flags = item->kind == REDIRECT_INPUT ? O_RDONLY : O_WRONLY | O_CREAT;
        int opened;

        if (item->kind == REDIRECT_OUTPUT) {
            flags |= O_TRUNC;
        } else if (item->kind == REDIRECT_APPEND) {
            flags |= O_APPEND;
        }
        opened = open(item->path, flags, 0666);
        if (opened == -1 || dup2(opened, target) == -1) {
            return 1;
        }
        close(opened);
    }

    if (command->argv[0][0] == 'c') {
        return change_directory(command->argv);
    }
    if (command->argv[0][0] == 'p') {
        return print_working_directory();
    }
    if (command->argv[0][0] == 'e') {
        exit(0);
    }
    return 1;
}

int execute_pipeline(struct pipeline *pipeline)
{
    if (is_builtin(pipeline->commands[0].argv[0])) {
        return run_builtin(&pipeline->commands[0]);
    }
    return launch_external_pipeline(pipeline);
}

