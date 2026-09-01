#include <stddef.h>
#include <string.h>

#define MAX_COMMANDS 4
#define MAX_ARGS 8
#define MAX_WORD 32

enum token_kind {
    TOKEN_WORD,
    TOKEN_PIPE
};

struct token {
    enum token_kind kind;
    char text[MAX_WORD];
};

struct command {
    char *argv[MAX_ARGS + 1];
    size_t argc;
};

struct pipeline {
    struct command commands[MAX_COMMANDS];
    size_t command_count;
};

int parse_tokens(const struct token *tokens, size_t token_count,
                 struct pipeline *output)
{
    size_t command_index = 0;
    size_t i;
    struct token current;

    memset(output, 0, sizeof(*output));
    output->command_count = 1;

    for (i = 0; i < token_count; ++i) {
        current = tokens[i];

        if (current.kind == TOKEN_PIPE) {
            ++command_index;
            ++output->command_count;
            if (output->command_count > MAX_COMMANDS) {
                return -1;
            }
            continue;
        }

        output->commands[command_index].argv[
            output->commands[command_index].argc++] = current.text;
        if (output->commands[command_index].argc > MAX_ARGS) {
            return -1;
        }
    }

    return 0;
}

