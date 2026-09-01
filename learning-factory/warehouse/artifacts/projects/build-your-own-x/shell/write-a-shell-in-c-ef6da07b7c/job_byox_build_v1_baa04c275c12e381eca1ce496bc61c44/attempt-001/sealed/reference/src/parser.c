#include "msh.h"

#include <ctype.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef enum {
    TOKEN_WORD,
    TOKEN_PIPE,
    TOKEN_BACKGROUND
} token_kind;

typedef struct {
    token_kind kind;
    char *text;
} token;

typedef struct {
    token *items;
    size_t count;
    size_t capacity;
} token_vector;

typedef struct {
    char *data;
    size_t length;
    size_t capacity;
} byte_buffer;

static void set_error(char *error, size_t error_size, const char *message)
{
    if (error != NULL && error_size > 0) {
        (void)snprintf(error, error_size, "%s", message);
    }
}

static int grow_allocation(void **allocation, size_t *capacity,
                           size_t element_size, size_t minimum)
{
    size_t next = *capacity == 0 ? 8 : *capacity;
    void *replacement;

    while (next < minimum) {
        if (next > SIZE_MAX / 2) {
            return -1;
        }
        next *= 2;
    }
    if (next > SIZE_MAX / element_size) {
        return -1;
    }
    replacement = realloc(*allocation, next * element_size);
    if (replacement == NULL) {
        return -1;
    }
    *allocation = replacement;
    *capacity = next;
    return 0;
}

static int buffer_append(byte_buffer *buffer, char byte)
{
    if (buffer->length == buffer->capacity &&
        grow_allocation((void **)&buffer->data, &buffer->capacity,
                        sizeof(*buffer->data), buffer->length + 1) < 0) {
        return -1;
    }
    buffer->data[buffer->length++] = byte;
    return 0;
}

static int tokens_append(token_vector *tokens, token_kind kind, char *text)
{
    if (tokens->count == tokens->capacity &&
        grow_allocation((void **)&tokens->items, &tokens->capacity,
                        sizeof(*tokens->items), tokens->count + 1) < 0) {
        return -1;
    }
    tokens->items[tokens->count].kind = kind;
    tokens->items[tokens->count].text = text;
    ++tokens->count;
    return 0;
}

static int flush_word(token_vector *tokens, byte_buffer *word, int *started)
{
    char *owned;

    if (!*started) {
        return 0;
    }
    if (buffer_append(word, '\0') < 0) {
        return -1;
    }
    owned = word->data;
    word->data = NULL;
    word->length = 0;
    word->capacity = 0;
    *started = 0;
    if (tokens_append(tokens, TOKEN_WORD, owned) < 0) {
        free(owned);
        return -1;
    }
    return 0;
}

static void tokens_destroy(token_vector *tokens)
{
    size_t index;

    for (index = 0; index < tokens->count; ++index) {
        free(tokens->items[index].text);
    }
    free(tokens->items);
    tokens->items = NULL;
    tokens->count = 0;
    tokens->capacity = 0;
}

static int lex_line(const char *line, token_vector *tokens,
                    char *error, size_t error_size)
{
    enum { LEX_NORMAL, LEX_SINGLE, LEX_DOUBLE } state = LEX_NORMAL;
    byte_buffer word = {NULL, 0, 0};
    int started = 0;
    size_t index;

    for (index = 0;; ++index) {
        const unsigned char byte = (unsigned char)line[index];

        if (state == LEX_SINGLE) {
            if (byte == '\0') {
                set_error(error, error_size, "unmatched single quote");
                goto syntax_error;
            }
            if (byte == '\'') {
                state = LEX_NORMAL;
            } else if (buffer_append(&word, (char)byte) < 0) {
                goto allocation_error;
            }
            continue;
        }

        if (state == LEX_DOUBLE) {
            if (byte == '\0') {
                set_error(error, error_size, "unmatched double quote");
                goto syntax_error;
            }
            if (byte == '"') {
                state = LEX_NORMAL;
            } else if (byte == '\\') {
                const unsigned char next = (unsigned char)line[++index];
                if (next == '\0') {
                    set_error(error, error_size, "trailing backslash in double quotes");
                    goto syntax_error;
                }
                if (buffer_append(&word, (char)next) < 0) {
                    goto allocation_error;
                }
            } else if (buffer_append(&word, (char)byte) < 0) {
                goto allocation_error;
            }
            continue;
        }

        if (byte == '\0') {
            if (flush_word(tokens, &word, &started) < 0) {
                goto allocation_error;
            }
            free(word.data);
            return 0;
        }
        if (isspace(byte)) {
            if (flush_word(tokens, &word, &started) < 0) {
                goto allocation_error;
            }
            continue;
        }
        if (byte == '\\') {
            const unsigned char next = (unsigned char)line[++index];
            if (next == '\0') {
                set_error(error, error_size, "trailing backslash");
                goto syntax_error;
            }
            started = 1;
            if (buffer_append(&word, (char)next) < 0) {
                goto allocation_error;
            }
            continue;
        }
        if (byte == '\'' || byte == '"') {
            started = 1;
            state = byte == '\'' ? LEX_SINGLE : LEX_DOUBLE;
            continue;
        }
        if (byte == '|' || byte == '&') {
            if (flush_word(tokens, &word, &started) < 0 ||
                tokens_append(tokens,
                              byte == '|' ? TOKEN_PIPE : TOKEN_BACKGROUND,
                              NULL) < 0) {
                goto allocation_error;
            }
            continue;
        }
        started = 1;
        if (buffer_append(&word, (char)byte) < 0) {
            goto allocation_error;
        }
    }

allocation_error:
    set_error(error, error_size, "out of memory while parsing");
syntax_error:
    free(word.data);
    return -1;
}

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
    token_vector tokens = {NULL, 0, 0};
    size_t effective_count;
    size_t command_count = 1;
    size_t index;
    size_t command_index;

    if (line == NULL || out == NULL) {
        set_error(error, error_size, "invalid parser input");
        return MSH_PARSE_ERROR;
    }
    out->commands = NULL;
    out->count = 0;
    out->background = 0;

    if (lex_line(line, &tokens, error, error_size) < 0) {
        tokens_destroy(&tokens);
        return MSH_PARSE_ERROR;
    }
    if (tokens.count == 0) {
        tokens_destroy(&tokens);
        return MSH_PARSE_EMPTY;
    }

    effective_count = tokens.count;
    if (tokens.items[effective_count - 1].kind == TOKEN_BACKGROUND) {
        out->background = 1;
        --effective_count;
    }
    if (effective_count == 0) {
        set_error(error, error_size, "background marker has no command");
        goto syntax_error;
    }

    for (index = 0; index < effective_count; ++index) {
        if (tokens.items[index].kind == TOKEN_BACKGROUND) {
            set_error(error, error_size, "background marker must be final");
            goto syntax_error;
        }
        if (tokens.items[index].kind == TOKEN_PIPE) {
            if (index == 0 || index + 1 == effective_count ||
                tokens.items[index - 1].kind == TOKEN_PIPE) {
                set_error(error, error_size, "empty command in pipeline");
                goto syntax_error;
            }
            ++command_count;
        }
    }

    out->commands = calloc(command_count, sizeof(*out->commands));
    if (out->commands == NULL) {
        set_error(error, error_size, "out of memory while building pipeline");
        goto syntax_error;
    }
    out->count = command_count;

    command_index = 0;
    index = 0;
    while (index < effective_count) {
        size_t end = index;
        size_t argument_index;
        msh_command *command = &out->commands[command_index];

        while (end < effective_count && tokens.items[end].kind == TOKEN_WORD) {
            ++end;
        }
        command->argc = end - index;
        command->argv = calloc(command->argc + 1, sizeof(*command->argv));
        if (command->argv == NULL) {
            set_error(error, error_size, "out of memory while building arguments");
            msh_pipeline_destroy(out);
            tokens_destroy(&tokens);
            return MSH_PARSE_ERROR;
        }
        for (argument_index = 0; argument_index < command->argc; ++argument_index) {
            command->argv[argument_index] = tokens.items[index + argument_index].text;
            tokens.items[index + argument_index].text = NULL;
        }
        index = end + 1;
        ++command_index;
    }

    tokens_destroy(&tokens);
    return MSH_PARSE_OK;

syntax_error:
    out->background = 0;
    tokens_destroy(&tokens);
    return MSH_PARSE_ERROR;
}
