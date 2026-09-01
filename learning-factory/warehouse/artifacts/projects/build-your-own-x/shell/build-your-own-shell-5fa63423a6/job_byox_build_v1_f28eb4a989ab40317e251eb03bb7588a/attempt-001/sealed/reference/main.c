#include "shell.h"

#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <sys/select.h>
#include <unistd.h>

typedef struct {
    char *data;
    size_t length;
    size_t capacity;
    bool eof;
} InputBuffer;

enum {
    INPUT_ERROR = -1,
    INPUT_EOF = 0,
    INPUT_LINE = 1,
    INPUT_CHILD_EVENT = 2,
    INPUT_NEED_DATA = 3
};

static void print_usage(FILE *stream) {
    (void)fprintf(stream, "usage: byosh [-c COMMAND]\n");
}

static int evaluate_line(Shell *shell, const char *line, bool *executed) {
    TokenList tokens;
    Pipeline pipeline;
    char *error_message = NULL;
    int parse_result;
    int status;

    *executed = true;
    if (lex_line(line, &tokens, &error_message) < 0) {
        (void)dprintf(STDERR_FILENO, "byosh: parse error: %s\n",
                      error_message != NULL ? error_message : "lexer failed");
        free(error_message);
        return 2;
    }
    parse_result = parse_tokens(&tokens, line, &pipeline, &error_message);
    token_list_free(&tokens);
    if (parse_result > 0) {
        *executed = false;
        return shell->last_status;
    }
    if (parse_result < 0) {
        (void)dprintf(STDERR_FILENO, "byosh: parse error: %s\n",
                      error_message != NULL ? error_message : "parser failed");
        free(error_message);
        return 2;
    }

    status = shell_execute_pipeline(shell, &pipeline);
    pipeline_free(&pipeline);
    return status;
}

static int input_buffer_append(InputBuffer *input, const char *data,
                               size_t length) {
    size_t required;
    size_t new_capacity;
    char *grown;

    if (length > SIZE_MAX - input->length) {
        errno = ENOMEM;
        return -1;
    }
    required = input->length + length;
    if (required <= input->capacity) {
        memcpy(input->data + input->length, data, length);
        input->length = required;
        return 0;
    }
    new_capacity = input->capacity == 0U ? 4096U : input->capacity;
    while (new_capacity < required) {
        if (new_capacity > SIZE_MAX / 2U) {
            errno = ENOMEM;
            return -1;
        }
        new_capacity *= 2U;
    }
    grown = realloc(input->data, new_capacity);
    if (grown == NULL) {
        return -1;
    }
    input->data = grown;
    input->capacity = new_capacity;
    memcpy(input->data + input->length, data, length);
    input->length = required;
    return 0;
}

static int input_buffer_extract(InputBuffer *input, char **line) {
    size_t newline = 0U;
    size_t line_length;
    size_t consumed;

    while (newline < input->length && input->data[newline] != '\n') {
        newline++;
    }
    if (newline == input->length && !input->eof) {
        return INPUT_NEED_DATA;
    }
    if (newline == input->length && input->length == 0U) {
        return INPUT_EOF;
    }
    consumed = newline < input->length ? newline + 1U : newline;
    line_length = newline;
    if (line_length > 0U && input->data[line_length - 1U] == '\r') {
        line_length--;
    }
    if (line_length == SIZE_MAX) {
        errno = ENOMEM;
        return INPUT_ERROR;
    }
    *line = malloc(line_length + 1U);
    if (*line == NULL) {
        return INPUT_ERROR;
    }
    memcpy(*line, input->data, line_length);
    (*line)[line_length] = '\0';
    input->length -= consumed;
    if (input->length > 0U) {
        memmove(input->data, input->data + consumed, input->length);
    }
    return INPUT_LINE;
}

static int wait_for_input_or_child(const Shell *shell) {
    fd_set readable;
    int highest;
    int result;

    for (;;) {
        if (fcntl(STDIN_FILENO, F_GETFD) >= 0) {
            break;
        }
        if (errno == EINTR) {
            continue;
        }
        return errno == EBADF ? INPUT_EOF : INPUT_ERROR;
    }
    if (shell->sigchld_read_fd < 0 ||
        shell->sigchld_read_fd >= FD_SETSIZE) {
        errno = EMFILE;
        return INPUT_ERROR;
    }
    FD_ZERO(&readable);
    FD_SET(STDIN_FILENO, &readable);
    FD_SET(shell->sigchld_read_fd, &readable);
    highest = shell->sigchld_read_fd > STDIN_FILENO
                  ? shell->sigchld_read_fd
                  : STDIN_FILENO;
    result = pselect(highest + 1, &readable, NULL, NULL, NULL,
                     &shell->child_signal_mask);
    if (result < 0) {
        if (errno == EINTR) {
            return INPUT_CHILD_EVENT;
        }
        return INPUT_ERROR;
    }
    if (FD_ISSET(shell->sigchld_read_fd, &readable)) {
        return INPUT_CHILD_EVENT;
    }
    return FD_ISSET(STDIN_FILENO, &readable) ? INPUT_LINE : INPUT_ERROR;
}

static int read_next_line(Shell *shell, InputBuffer *input, char **line) {
    char chunk[4096];

    *line = NULL;
    for (;;) {
        int extracted = input_buffer_extract(input, line);
        int event;
        ssize_t count;

        if (extracted != INPUT_NEED_DATA) {
            return extracted;
        }
        event = wait_for_input_or_child(shell);
        if (event != INPUT_LINE) {
            return event;
        }
        count = read(STDIN_FILENO, chunk, sizeof(chunk));
        if (count > 0) {
            if (input_buffer_append(input, chunk, (size_t)count) < 0) {
                return INPUT_ERROR;
            }
            continue;
        }
        if (count == 0) {
            input->eof = true;
            continue;
        }
        if (errno == EINTR || errno == EAGAIN || errno == EWOULDBLOCK) {
            continue;
        }
        return INPUT_ERROR;
    }
}

static int run_input(Shell *shell) {
    InputBuffer input = {0};

    while (!shell->should_exit) {
        char *line = NULL;
        bool executed;
        int status;
        int input_result;

        shell_reap_jobs(shell, true);
        if (shell->interactive) {
            (void)dprintf(STDERR_FILENO, "byosh$ ");
        }
        input_result = read_next_line(shell, &input, &line);
        if (input_result == INPUT_CHILD_EVENT) {
            if (shell->interactive) {
                (void)dprintf(STDERR_FILENO, "\n");
            }
            shell_reap_jobs(shell, true);
            continue;
        }
        if (input_result == INPUT_EOF) {
            break;
        }
        if (input_result == INPUT_ERROR) {
            (void)dprintf(STDERR_FILENO, "byosh: input: %s\n",
                          strerror(errno));
            shell->last_status = 1;
            break;
        }
        status = evaluate_line(shell, line, &executed);
        free(line);
        if (executed) {
            shell->last_status = status;
        }
    }
    free(input.data);
    return shell->should_exit ? shell->exit_status : shell->last_status;
}

int main(int argc, char **argv) {
    Shell shell;
    int status;

    if (argc != 1 && argc != 3) {
        print_usage(stderr);
        return 2;
    }
    if (argc == 3 && strcmp(argv[1], "-c") != 0) {
        print_usage(stderr);
        return 2;
    }
    if (shell_initialize(&shell) < 0) {
        return 1;
    }

    if (argc == 3) {
        bool executed;
        status = evaluate_line(&shell, argv[2], &executed);
        if (executed) {
            shell.last_status = status;
        }
        if (shell.should_exit) {
            status = shell.exit_status;
        }
    } else {
        status = run_input(&shell);
    }

    shell_reap_jobs(&shell, true);
    shell_destroy(&shell);
    return status;
}
