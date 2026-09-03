#include "minish.h"

#include <stdio.h>
#include <stdlib.h>

void pipeline_free(Pipeline *pipeline)
{
    size_t i;
    size_t j;

    if (pipeline == NULL) {
        return;
    }
    for (i = 0; i < pipeline->count; ++i) {
        for (j = 0; j < pipeline->commands[i].argc; ++j) {
            free(pipeline->commands[i].argv[j]);
        }
        free(pipeline->commands[i].argv);
        free(pipeline->commands[i].input_path);
        free(pipeline->commands[i].output_path);
    }
    free(pipeline->commands);
    *pipeline = (Pipeline){0};
}

int parse_pipeline(const TokenList *tokens, Pipeline *out, char *error,
                   size_t error_size)
{
    (void)tokens;
    if (out != NULL) {
        *out = (Pipeline){0};
    }
    if (error != NULL && error_size > 0) {
        (void)snprintf(error, error_size, "parser is not implemented");
    }

    /* TODO: validate the grammar and build an independently owned tree. */
    return -1;
}
