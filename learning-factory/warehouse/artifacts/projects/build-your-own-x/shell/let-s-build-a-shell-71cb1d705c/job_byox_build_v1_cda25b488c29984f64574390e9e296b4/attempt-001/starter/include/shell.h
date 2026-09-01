#ifndef MINISH_SHELL_H
#define MINISH_SHELL_H

#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>

#define SHELL_ERROR_MESSAGE_SIZE 160U

typedef enum {
    SHELL_RESULT_OK = 0,
    SHELL_RESULT_TODO,
    SHELL_RESULT_ERROR
} ShellResult;

typedef struct {
    size_t offset;
    char message[SHELL_ERROR_MESSAGE_SIZE];
} ShellError;

typedef struct ShellRuntime ShellRuntime;

typedef struct {
    int last_status;
    int last_foreground_status;
    int requested_exit_status;
    bool should_exit;
    ShellRuntime *runtime;
} ShellState;

void shell_error_clear(ShellError *error);
void shell_error_set(ShellError *error, size_t offset, const char *message);
void shell_state_init(ShellState *state);
void shell_state_destroy(ShellState *state);

/* Run one source line through lexer, parser, and executor in that order. */
int shell_run_line(const char *line, ShellState *state, FILE *error_stream);

/* Split a -c operand into physical lines and run them in order. */
int shell_run_command_string(const char *source, ShellState *state,
                             FILE *error_stream);

/* Read lines until EOF or until an executor requests exit. */
int shell_repl(FILE *input, FILE *output, FILE *error_stream,
               bool show_prompt, ShellState *state);

#endif
