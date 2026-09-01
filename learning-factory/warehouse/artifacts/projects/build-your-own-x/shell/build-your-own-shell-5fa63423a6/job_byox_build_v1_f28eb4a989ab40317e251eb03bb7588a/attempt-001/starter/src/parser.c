#include "byosh.h"

#include <ctype.h>
#include <stdio.h>
#include <string.h>

static void set_error(char *error, size_t error_size, const char *message)
{
    if (error != NULL && error_size > 0U) {
        (void)snprintf(error, error_size, "%s", message);
    }
}

void byosh_pipeline_init(struct byosh_pipeline *pipeline)
{
    if (pipeline != NULL) {
        (void)memset(pipeline, 0, sizeof(*pipeline));
    }
}

static int is_operator(char ch)
{
    return ch == '|' || ch == '<' || ch == '>' || ch == '&' ||
           ch == '\'' || ch == '"' || ch == '\\';
}

enum byosh_parse_status byosh_parse_line(char *line,
                                         struct byosh_pipeline *pipeline,
                                         char *error,
                                         size_t error_size)
{
    char *cursor;
    struct byosh_command *command;

    if (line == NULL || pipeline == NULL) {
        set_error(error, error_size, "parser received a null argument");
        return BYOSH_PARSE_ERROR;
    }

    byosh_pipeline_init(pipeline);
    if (error != NULL && error_size > 0U) {
        error[0] = '\0';
    }

    /*
     * The starter recognizes plain whitespace-separated words. Quoting,
     * operators, pipelines, and redirection are intentionally learner work.
     * TODO(milestone 1): replace this feature gate and plain-word loop with
     * the complete parser contract while preserving atomic failure behavior.
     */
    for (cursor = line; *cursor != '\0'; ++cursor) {
        if (is_operator(*cursor)) {
            set_error(error, error_size,
                      "syntax feature belongs to a later parser milestone");
            return BYOSH_PARSE_TODO;
        }
    }

    cursor = line;
    while (isspace((unsigned char)*cursor)) {
        ++cursor;
    }
    if (*cursor == '\0') {
        return BYOSH_PARSE_EMPTY;
    }

    pipeline->command_count = 1U;
    command = &pipeline->commands[0];
    while (*cursor != '\0') {
        char *word;

        while (isspace((unsigned char)*cursor)) {
            ++cursor;
        }
        if (*cursor == '\0') {
            break;
        }
        if (command->argc == BYOSH_MAX_ARGS) {
            set_error(error, error_size, "too many arguments");
            byosh_pipeline_init(pipeline);
            return BYOSH_PARSE_ERROR;
        }
        word = cursor;
        while (*cursor != '\0' && !isspace((unsigned char)*cursor)) {
            ++cursor;
        }
        if (*cursor != '\0') {
            *cursor++ = '\0';
        }
        command->argv[command->argc++] = word;
    }
    command->argv[command->argc] = NULL;
    return BYOSH_PARSE_OK;
}
