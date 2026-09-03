#include "minish.h"

#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void set_error(char *error, size_t error_size, const char *format, ...)
{
    va_list arguments;

    if (error == NULL || error_size == 0) {
        return;
    }
    va_start(arguments, format);
    (void)vsnprintf(error, error_size, format, arguments);
    va_end(arguments);
}

static void command_free(Command *command)
{
    size_t i;

    for (i = 0; i < command->argc; ++i) {
        free(command->argv[i]);
    }
    free(command->argv);
    free(command->input_path);
    free(command->output_path);
    *command = (Command){0};
}

void pipeline_free(Pipeline *pipeline)
{
    size_t i;

    if (pipeline == NULL) {
        return;
    }
    for (i = 0; i < pipeline->count; ++i) {
        command_free(&pipeline->commands[i]);
    }
    free(pipeline->commands);
    *pipeline = (Pipeline){0};
}

static int append_argument(Command *command, const char *text)
{
    char **replacement;
    char *copy = strdup(text);

    if (copy == NULL) {
        return -1;
    }
    replacement = realloc(command->argv,
                          (command->argc + 2) * sizeof(*replacement));
    if (replacement == NULL) {
        free(copy);
        return -1;
    }
    command->argv = replacement;
    command->argv[command->argc++] = copy;
    command->argv[command->argc] = NULL;
    return 0;
}

static int append_command(Pipeline *pipeline, Command *command)
{
    Command *replacement =
        realloc(pipeline->commands,
                (pipeline->count + 1) * sizeof(*replacement));

    if (replacement == NULL) {
        return -1;
    }
    pipeline->commands = replacement;
    pipeline->commands[pipeline->count++] = *command;
    *command = (Command){0};
    return 0;
}

static int parse_command(const TokenList *tokens, size_t *position,
                         Command *command, char *error, size_t error_size)
{
    while (*position < tokens->len) {
        const Token *token = &tokens->items[*position];

        if (token->type == TOK_PIPE || token->type == TOK_AMP ||
            token->type == TOK_END) {
            break;
        }
        if (token->type == TOK_WORD) {
            if (token->text == NULL ||
                append_argument(command, token->text) != 0) {
                set_error(error, error_size,
                          token->text == NULL
                              ? "syntax error: word token has no value"
                              : "out of memory while parsing arguments");
                return -1;
            }
            ++*position;
            continue;
        }
        if (token->type == TOK_REDIR_IN || token->type == TOK_REDIR_OUT ||
            token->type == TOK_REDIR_APPEND) {
            const TokenType redirection = token->type;
            char **target = redirection == TOK_REDIR_IN
                                ? &command->input_path
                                : &command->output_path;

            ++*position;
            if (*position >= tokens->len ||
                tokens->items[*position].type != TOK_WORD ||
                tokens->items[*position].text == NULL) {
                set_error(error, error_size,
                          "syntax error: redirection requires a path");
                return -1;
            }
            if (*target != NULL) {
                set_error(error, error_size,
                          redirection == TOK_REDIR_IN
                              ? "syntax error: duplicate input redirection"
                              : "syntax error: duplicate output redirection");
                return -1;
            }
            *target = strdup(tokens->items[*position].text);
            if (*target == NULL) {
                set_error(error, error_size,
                          "out of memory while parsing redirection");
                return -1;
            }
            if (redirection != TOK_REDIR_IN) {
                command->append_output = redirection == TOK_REDIR_APPEND;
            }
            ++*position;
            continue;
        }

        set_error(error, error_size, "syntax error: unexpected token");
        return -1;
    }

    if (command->argc == 0) {
        set_error(error, error_size, "syntax error: expected a command");
        return -1;
    }
    return 0;
}

int parse_pipeline(const TokenList *tokens, Pipeline *out, char *error,
                   size_t error_size)
{
    size_t position = 0;

    if (error != NULL && error_size > 0) {
        error[0] = '\0';
    }
    if (out == NULL) {
        set_error(error, error_size, "parser output is null");
        return -1;
    }
    *out = (Pipeline){0};
    if (tokens == NULL || tokens->items == NULL || tokens->len == 0) {
        set_error(error, error_size, "syntax error: missing token stream");
        return -1;
    }

    for (;;) {
        Command command = {0};
        TokenType delimiter;

        if (parse_command(tokens, &position, &command, error, error_size) != 0) {
            command_free(&command);
            goto failure;
        }
        if (append_command(out, &command) != 0) {
            command_free(&command);
            set_error(error, error_size, "out of memory while parsing pipeline");
            goto failure;
        }
        if (position >= tokens->len) {
            set_error(error, error_size,
                      "syntax error: token stream has no terminator");
            goto failure;
        }

        delimiter = tokens->items[position].type;
        if (delimiter == TOK_PIPE) {
            ++position;
            continue;
        }
        if (delimiter == TOK_AMP) {
            out->background = true;
            ++position;
            if (position >= tokens->len ||
                tokens->items[position].type != TOK_END) {
                set_error(error, error_size,
                          "syntax error: '&' must end the pipeline");
                goto failure;
            }
            ++position;
            break;
        }
        if (delimiter == TOK_END) {
            ++position;
            break;
        }
        set_error(error, error_size, "syntax error: unexpected delimiter");
        goto failure;
    }

    if (position != tokens->len) {
        set_error(error, error_size,
                  "syntax error: tokens appear after end marker");
        goto failure;
    }
    return 0;

failure:
    pipeline_free(out);
    return -1;
}
