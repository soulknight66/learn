#include "shell.h"

#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

static int set_error(char **error_message, size_t position,
                     const char *description) {
    int length = snprintf(NULL, 0, "at byte %zu: %s", position, description);
    char *message;

    if (length < 0) {
        return -1;
    }
    message = malloc((size_t)length + 1U);
    if (message == NULL) {
        return -1;
    }
    (void)snprintf(message, (size_t)length + 1U, "at byte %zu: %s",
                   position, description);
    *error_message = message;
    return -1;
}

static Command *pipeline_add_command(Pipeline *pipeline) {
    Command *grown;
    size_t new_capacity;
    Command *command;

    if (pipeline->command_count == pipeline->command_capacity) {
        if (pipeline->command_capacity > SIZE_MAX / 2U) {
            return NULL;
        }
        new_capacity = pipeline->command_capacity == 0U
                           ? 4U
                           : pipeline->command_capacity * 2U;
        if (new_capacity > SIZE_MAX / sizeof(*grown)) {
            return NULL;
        }
        grown = realloc(pipeline->commands, new_capacity * sizeof(*grown));
        if (grown == NULL) {
            return NULL;
        }
        pipeline->commands = grown;
        pipeline->command_capacity = new_capacity;
    }
    command = &pipeline->commands[pipeline->command_count++];
    memset(command, 0, sizeof(*command));
    return command;
}

static int command_add_argument(Command *command, const char *argument) {
    char **grown;
    size_t new_capacity;
    char *copy;

    if (command->argc >= SIZE_MAX - 1U) {
        return -1;
    }
    if (command->argc + 1U >= command->argv_capacity) {
        if (command->argv_capacity > SIZE_MAX / 2U) {
            return -1;
        }
        new_capacity = command->argv_capacity == 0U
                           ? 8U
                           : command->argv_capacity * 2U;
        if (new_capacity > SIZE_MAX / sizeof(*grown)) {
            return -1;
        }
        grown = realloc(command->argv, new_capacity * sizeof(*grown));
        if (grown == NULL) {
            return -1;
        }
        command->argv = grown;
        command->argv_capacity = new_capacity;
    }
    copy = strdup(argument);
    if (copy == NULL) {
        return -1;
    }
    command->argv[command->argc++] = copy;
    command->argv[command->argc] = NULL;
    return 0;
}

static int command_add_redirection(Command *command, RedirectionType type,
                                   const char *path) {
    Redirection *grown;
    size_t new_capacity;
    char *copy;

    if (command->redirection_count == command->redirection_capacity) {
        if (command->redirection_capacity > SIZE_MAX / 2U) {
            return -1;
        }
        new_capacity = command->redirection_capacity == 0U
                           ? 4U
                           : command->redirection_capacity * 2U;
        if (new_capacity > SIZE_MAX / sizeof(*grown)) {
            return -1;
        }
        grown = realloc(command->redirections,
                        new_capacity * sizeof(*grown));
        if (grown == NULL) {
            return -1;
        }
        command->redirections = grown;
        command->redirection_capacity = new_capacity;
    }
    copy = strdup(path);
    if (copy == NULL) {
        return -1;
    }
    command->redirections[command->redirection_count].type = type;
    command->redirections[command->redirection_count].path = copy;
    command->redirection_count++;
    return 0;
}

static bool command_has_redirection(const Command *command,
                                    RedirectionType requested_type) {
    bool requested_is_input = requested_type == REDIR_INPUT;
    size_t index;

    for (index = 0U; index < command->redirection_count; index++) {
        bool existing_is_input =
            command->redirections[index].type == REDIR_INPUT;
        if (requested_is_input == existing_is_input) {
            return true;
        }
    }
    return false;
}

int parse_tokens(const TokenList *tokens, const char *source,
                 Pipeline *pipeline, char **error_message) {
    size_t cursor = 0U;
    Command *current;

    memset(pipeline, 0, sizeof(*pipeline));
    *error_message = NULL;

    if (tokens->count == 0U || tokens->items[0].type == TOK_END) {
        return 1;
    }
    pipeline->source = strdup(source);
    if (pipeline->source == NULL) {
        goto memory_failure;
    }
    current = pipeline_add_command(pipeline);
    if (current == NULL) {
        goto memory_failure;
    }

    while (tokens->items[cursor].type != TOK_END) {
        const Token *token = &tokens->items[cursor];

        if (token->type == TOK_WORD) {
            if (command_add_argument(current, token->text) < 0) {
                goto memory_failure;
            }
            cursor++;
            continue;
        }
        if (token->type == TOK_REDIR_IN || token->type == TOK_REDIR_OUT ||
            token->type == TOK_REDIR_APPEND) {
            RedirectionType type;

            if (tokens->items[cursor + 1U].type != TOK_WORD) {
                (void)set_error(error_message, token->position,
                                "redirection requires a path");
                goto parse_failure;
            }
            type = token->type == TOK_REDIR_IN
                       ? REDIR_INPUT
                       : (token->type == TOK_REDIR_OUT ? REDIR_OUTPUT
                                                       : REDIR_APPEND);
            if (command_has_redirection(current, type)) {
                (void)set_error(error_message, token->position,
                                type == REDIR_INPUT
                                    ? "duplicate input redirection"
                                    : "duplicate output redirection");
                goto parse_failure;
            }
            if (command_add_redirection(current, type,
                                        tokens->items[cursor + 1U].text) < 0) {
                goto memory_failure;
            }
            cursor += 2U;
            continue;
        }
        if (token->type == TOK_PIPE) {
            if (current->argc == 0U) {
                (void)set_error(error_message, token->position,
                                "missing command before pipe");
                goto parse_failure;
            }
            current = pipeline_add_command(pipeline);
            if (current == NULL) {
                goto memory_failure;
            }
            cursor++;
            if (tokens->items[cursor].type == TOK_END) {
                (void)set_error(error_message, token->position,
                                "missing command after pipe");
                goto parse_failure;
            }
            continue;
        }
        if (token->type == TOK_AMP) {
            if (current->argc == 0U) {
                (void)set_error(error_message, token->position,
                                "background marker requires a command");
                goto parse_failure;
            }
            if (tokens->items[cursor + 1U].type != TOK_END) {
                (void)set_error(error_message, token->position,
                                "background marker must be last");
                goto parse_failure;
            }
            pipeline->background = true;
            cursor++;
            continue;
        }

        (void)set_error(error_message, token->position, "unexpected token");
        goto parse_failure;
    }

    if (current->argc == 0U) {
        (void)set_error(error_message, tokens->items[cursor].position,
                        "missing command after pipe");
        goto parse_failure;
    }
    return 0;

memory_failure:
    if (*error_message == NULL) {
        (void)set_error(error_message, 0U, "out of memory");
    }
parse_failure:
    pipeline_free(pipeline);
    return -1;
}

void pipeline_free(Pipeline *pipeline) {
    size_t command_index;

    for (command_index = 0U; command_index < pipeline->command_count;
         command_index++) {
        Command *command = &pipeline->commands[command_index];
        size_t index;

        for (index = 0U; index < command->argc; index++) {
            free(command->argv[index]);
        }
        for (index = 0U; index < command->redirection_count; index++) {
            free(command->redirections[index].path);
        }
        free(command->argv);
        free(command->redirections);
    }
    free(pipeline->commands);
    free(pipeline->source);
    memset(pipeline, 0, sizeof(*pipeline));
}
