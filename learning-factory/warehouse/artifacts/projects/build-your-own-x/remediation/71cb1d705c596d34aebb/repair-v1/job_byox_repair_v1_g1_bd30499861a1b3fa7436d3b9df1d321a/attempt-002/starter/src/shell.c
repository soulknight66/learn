#include <errno.h>
#include <stdlib.h>
#include <string.h>

#include "executor.h"
#include "lexer.h"
#include "parser.h"
#include "shell.h"

void shell_error_clear(ShellError *error)
{
    if (error == NULL) {
        return;
    }
    error->offset = 0U;
    error->message[0] = '\0';
}

void shell_error_set(ShellError *error, size_t offset, const char *message)
{
    if (error == NULL) {
        return;
    }
    error->offset = offset;
    (void)snprintf(error->message, sizeof(error->message), "%s",
                   message == NULL ? "unknown error" : message);
}

void shell_state_init(ShellState *state)
{
    state->last_status = 0;
    state->last_foreground_status = 0;
    state->requested_exit_status = 0;
    state->should_exit = false;
    state->runtime = NULL;
}

void shell_state_destroy(ShellState *state)
{
    if (state == NULL) {
        return;
    }
    /* TODO: release and reap the job-control runtime once implemented. */
    state->runtime = NULL;
}

static int report_stage_result(const char *stage, ShellResult result,
                               const ShellError *error, FILE *error_stream)
{
    const char *description = result == SHELL_RESULT_TODO
                                  ? "feature not implemented"
                                  : "stage failed";

    if (error != NULL && error->message[0] != '\0') {
        description = error->message;
    }
    fprintf(error_stream, "minish: %s: %s (at byte %zu)\n", stage,
            description, error == NULL ? 0U : error->offset);
    return 2;
}

int shell_run_line(const char *line, ShellState *state, FILE *error_stream)
{
    TokenList tokens;
    CommandList list;
    ShellError error;
    ShellResult result;
    int status;

    if (line == NULL || state == NULL || error_stream == NULL) {
        return 2;
    }

    token_list_init(&tokens);
    command_list_init(&list);
    shell_error_clear(&error);

    result = lexer_tokenize(line, &tokens, &error);
    if (result != SHELL_RESULT_OK) {
        status = report_stage_result("lexer", result, &error, error_stream);
        goto done;
    }

    result = parser_parse_list(line, &tokens, &list, &error);
    if (result != SHELL_RESULT_OK) {
        status = report_stage_result("parser", result, &error, error_stream);
        goto done;
    }

    result = executor_run_list(&list, state, &error);
    if (result != SHELL_RESULT_OK) {
        status = report_stage_result("executor", result, &error, error_stream);
        goto done;
    }

    status = state->last_status;

done:
    command_list_destroy(&list);
    token_list_destroy(&tokens);
    state->last_status = status;
    return status;
}

int shell_run_command_string(const char *source, ShellState *state,
                             FILE *error_stream)
{
    const char *start;
    int status;

    if (source == NULL || state == NULL || error_stream == NULL) {
        return 2;
    }

    start = source;
    status = state->last_status;
    while (*start != '\0' && !state->should_exit) {
        const char *newline = strchr(start, '\n');
        size_t length = newline == NULL
                            ? strlen(start)
                            : (size_t)(newline - start);
        char *line;

        if (length == (size_t)-1) {
            fputs("minish: input: line is too long\n", error_stream);
            state->last_status = 2;
            return 2;
        }
        line = malloc(length + 1U);
        if (line == NULL) {
            fputs("minish: input: out of memory\n", error_stream);
            state->last_status = 2;
            return 2;
        }
        memcpy(line, start, length);
        line[length] = '\0';
        status = shell_run_line(line, state, error_stream);
        free(line);

        if (newline == NULL) {
            break;
        }
        start = newline + 1;
    }

    return state->should_exit ? state->requested_exit_status : status;
}

int shell_repl(FILE *input, FILE *output, FILE *error_stream,
               bool show_prompt, ShellState *state)
{
    char *line = NULL;
    size_t capacity = 0U;
    ssize_t length;

    while (!state->should_exit) {
        if (show_prompt) {
            fputs("minish$ ", output);
            fflush(output);
        }

        errno = 0;
        length = getline(&line, &capacity, input);
        if (length < 0) {
            if (feof(input)) {
                break;
            }
            fprintf(error_stream, "minish: input: %s\n", strerror(errno));
            state->last_status = 2;
            break;
        }

        if (memchr(line, '\0', (size_t)length) != NULL) {
            fputs("minish: syntax error: NUL byte in input\n", error_stream);
            state->last_status = 2;
            continue;
        }
        if (length > 0 && line[(size_t)length - 1U] == '\n') {
            line[(size_t)length - 1U] = '\0';
        }

        (void)shell_run_line(line, state, error_stream);
    }

    free(line);
    return state->should_exit ? state->requested_exit_status
                              : state->last_status;
}
