#include <stdlib.h>

#include "parser.h"

void pipeline_init(Pipeline *pipeline)
{
    pipeline->commands = NULL;
    pipeline->command_count = 0U;
    pipeline->background = false;
    pipeline->source_text = NULL;
}

void pipeline_destroy(Pipeline *pipeline)
{
    size_t command_index;

    if (pipeline == NULL) {
        return;
    }
    for (command_index = 0U; command_index < pipeline->command_count;
         ++command_index) {
        Command *command = &pipeline->commands[command_index];
        size_t argument_index;
        size_t redirection_index;

        for (argument_index = 0U; argument_index < command->argc;
             ++argument_index) {
            free(command->argv[argument_index]);
        }
        free(command->argv);
        for (redirection_index = 0U;
             redirection_index < command->redirection_count;
             ++redirection_index) {
            free(command->redirections[redirection_index].path);
        }
        free(command->redirections);
    }
    free(pipeline->commands);
    free(pipeline->source_text);
    pipeline_init(pipeline);
}

void command_list_init(CommandList *list)
{
    list->pipelines = NULL;
    list->pipeline_count = 0U;
}

void command_list_destroy(CommandList *list)
{
    size_t index;

    if (list == NULL) {
        return;
    }
    for (index = 0U; index < list->pipeline_count; ++index) {
        pipeline_destroy(&list->pipelines[index]);
    }
    free(list->pipelines);
    command_list_init(list);
}

ShellResult parser_parse_list(const char *source, const TokenList *tokens,
                              CommandList *list, ShellError *error)
{
    if (source == NULL || tokens == NULL || list == NULL ||
        tokens->length == 0U) {
        shell_error_set(error, 0U, "invalid parser input");
        return SHELL_RESULT_ERROR;
    }

    if (tokens->length == 1U && tokens->items[0].kind == TOKEN_END) {
        return SHELL_RESULT_OK;
    }

    /* TODO: validate the whole list before building any execution plan. */
    shell_error_set(error, tokens->items[0].offset, "parsing is a TODO");
    return SHELL_RESULT_TODO;
}
