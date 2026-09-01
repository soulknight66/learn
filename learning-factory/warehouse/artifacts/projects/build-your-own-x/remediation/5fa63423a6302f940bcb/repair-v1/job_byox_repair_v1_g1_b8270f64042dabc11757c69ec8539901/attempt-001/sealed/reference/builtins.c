#include "shell.h"

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

BuiltinKind builtin_identify(const Command *command) {
    const char *name;

    if (command->argc == 0U) {
        return BUILTIN_NONE;
    }
    name = command->argv[0];
    if (strcmp(name, "cd") == 0) {
        return BUILTIN_CD;
    }
    if (strcmp(name, "pwd") == 0) {
        return BUILTIN_PWD;
    }
    if (strcmp(name, "exit") == 0) {
        return BUILTIN_EXIT;
    }
    if (strcmp(name, "jobs") == 0) {
        return BUILTIN_JOBS;
    }
    if (strcmp(name, "fg") == 0) {
        return BUILTIN_FG;
    }
    if (strcmp(name, "bg") == 0) {
        return BUILTIN_BG;
    }
    return BUILTIN_NONE;
}

static int builtin_cd(const Command *command) {
    const char *destination;

    if (command->argc > 2U) {
        (void)dprintf(STDERR_FILENO, "byosh: cd: too many arguments\n");
        return 2;
    }
    if (command->argc == 1U) {
        destination = getenv("HOME");
        if (destination == NULL || destination[0] == '\0') {
            (void)dprintf(STDERR_FILENO, "byosh: cd: HOME is not set\n");
            return 1;
        }
    } else {
        destination = command->argv[1];
    }
    if (chdir(destination) < 0) {
        (void)dprintf(STDERR_FILENO, "byosh: cd: %s: %s\n", destination,
                      strerror(errno));
        return 1;
    }
    return 0;
}

static int builtin_pwd(const Command *command) {
    char *directory = NULL;
    size_t capacity = 128U;

    if (command->argc != 1U) {
        (void)dprintf(STDERR_FILENO, "byosh: pwd: expected no arguments\n");
        return 2;
    }
    for (;;) {
        char *grown = realloc(directory, capacity);
        if (grown == NULL) {
            free(directory);
            (void)dprintf(STDERR_FILENO, "byosh: pwd: out of memory\n");
            return 1;
        }
        directory = grown;
        if (getcwd(directory, capacity) != NULL) {
            break;
        }
        if (errno != ERANGE) {
            (void)dprintf(STDERR_FILENO, "byosh: pwd: %s\n",
                          strerror(errno));
            free(directory);
            return 1;
        }
        if (capacity > ((size_t)-1) / 2U) {
            (void)dprintf(STDERR_FILENO, "byosh: pwd: path is too long\n");
            free(directory);
            return 1;
        }
        capacity *= 2U;
    }
    if (dprintf(STDOUT_FILENO, "%s\n", directory) < 0) {
        int saved_errno = errno;
        free(directory);
        (void)dprintf(STDERR_FILENO, "byosh: pwd: write: %s\n",
                      strerror(saved_errno));
        return 1;
    }
    free(directory);
    return 0;
}

static int parse_exit_status(const char *text, int *status) {
    char *end = NULL;
    long value;

    errno = 0;
    value = strtol(text, &end, 10);
    if (errno == ERANGE || end == text || *end != '\0') {
        return -1;
    }
    value %= 256L;
    if (value < 0L) {
        value += 256L;
    }
    *status = (int)value;
    return 0;
}

static int builtin_exit(Shell *shell, const Command *command,
                        bool in_parent) {
    int status = shell->last_status;

    if (command->argc > 2U) {
        (void)dprintf(STDERR_FILENO, "byosh: exit: too many arguments\n");
        return 2;
    }
    if (command->argc == 2U &&
        parse_exit_status(command->argv[1], &status) < 0) {
        (void)dprintf(STDERR_FILENO,
                      "byosh: exit: %s: numeric argument required\n",
                      command->argv[1]);
        status = 2;
        if (in_parent) {
            shell->should_exit = true;
            shell->exit_status = status;
        }
        return status;
    }
    if (in_parent) {
        shell->should_exit = true;
        shell->exit_status = status;
    }
    return status;
}

int builtin_run(Shell *shell, const Command *command, bool in_parent) {
    BuiltinKind kind = builtin_identify(command);

    switch (kind) {
    case BUILTIN_CD:
        return builtin_cd(command);
    case BUILTIN_PWD:
        return builtin_pwd(command);
    case BUILTIN_EXIT:
        return builtin_exit(shell, command, in_parent);
    case BUILTIN_JOBS:
        if (command->argc != 1U) {
            (void)dprintf(STDERR_FILENO,
                          "byosh: jobs: expected no arguments\n");
            return 2;
        }
        return shell_builtin_jobs(shell);
    case BUILTIN_FG:
    case BUILTIN_BG:
        if (command->argc > 2U) {
            (void)dprintf(STDERR_FILENO, "byosh: %s: too many arguments\n",
                          command->argv[0]);
            return 2;
        }
        if (!in_parent) {
            (void)dprintf(STDERR_FILENO,
                          "byosh: %s: unavailable in a pipeline or "
                          "background command\n",
                          command->argv[0]);
            return 1;
        }
        return kind == BUILTIN_FG
                   ? shell_builtin_fg(shell,
                                      command->argc == 2U ? command->argv[1]
                                                          : NULL)
                   : shell_builtin_bg(shell,
                                      command->argc == 2U ? command->argv[1]
                                                          : NULL);
    case BUILTIN_NONE:
        break;
    }
    return 127;
}
