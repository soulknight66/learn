#include "msh.h"

#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>

void msh_pipeline_destroy(msh_pipeline *pipeline)
{
    size_t command_index;

    if (pipeline == NULL) {
        return;
    }
    for (command_index = 0; command_index < pipeline->count; ++command_index) {
        size_t argument_index;
        msh_command *command = &pipeline->commands[command_index];

        for (argument_index = 0; argument_index < command->argc; ++argument_index) {
            free(command->argv[argument_index]);
        }
        free(command->argv);
    }
    free(pipeline->commands);
    pipeline->commands = NULL;
    pipeline->count = 0;
    pipeline->background = 0;
}

msh_parse_result msh_parse_line(const char *line, msh_pipeline *out,
                                char *error, size_t error_size)
{
    const unsigned char *cursor;

    if (out == NULL || line == NULL) {
        if (error != NULL && error_size > 0) {
            (void)snprintf(error, error_size, "invalid parser input");
        }
        return MSH_PARSE_ERROR;
    }

    out->commands = NULL;
    out->count = 0;
    out->background = 0;

    cursor = (const unsigned char *)line;
    while (*cursor != '\0' && isspace(*cursor)) {
        ++cursor;
    }
    if (*cursor == '\0') {
        return MSH_PARSE_EMPTY;
    }

    /* TODO(stage 1): tokenize, validate, and populate out atomically. */
    if (error != NULL && error_size > 0) {
        (void)snprintf(error, error_size, "parser milestone is not implemented");
    }
    return MSH_PARSE_ERROR;
}
