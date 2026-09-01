#include "shell.h"

#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
    char *data;
    size_t length;
    size_t capacity;
} Buffer;

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

static int buffer_push(Buffer *buffer, char value) {
    char *grown;
    size_t new_capacity;

    if (buffer->length == SIZE_MAX) {
        return -1;
    }
    if (buffer->length + 1U >= buffer->capacity) {
        if (buffer->capacity > SIZE_MAX / 2U) {
            return -1;
        }
        new_capacity = buffer->capacity == 0U ? 32U : buffer->capacity * 2U;
        grown = realloc(buffer->data, new_capacity);
        if (grown == NULL) {
            return -1;
        }
        buffer->data = grown;
        buffer->capacity = new_capacity;
    }
    buffer->data[buffer->length++] = value;
    return 0;
}

static int token_push(TokenList *tokens, TokenType type, const char *text,
                      size_t position) {
    Token *grown;
    size_t new_capacity;
    char *copy = NULL;

    if (tokens->count == tokens->capacity) {
        if (tokens->capacity > SIZE_MAX / 2U) {
            return -1;
        }
        new_capacity = tokens->capacity == 0U ? 16U : tokens->capacity * 2U;
        if (new_capacity > SIZE_MAX / sizeof(*grown)) {
            return -1;
        }
        grown = realloc(tokens->items, new_capacity * sizeof(*grown));
        if (grown == NULL) {
            return -1;
        }
        tokens->items = grown;
        tokens->capacity = new_capacity;
    }
    if (text != NULL) {
        copy = strdup(text);
        if (copy == NULL) {
            return -1;
        }
    }
    tokens->items[tokens->count].type = type;
    tokens->items[tokens->count].text = copy;
    tokens->items[tokens->count].position = position;
    tokens->count++;
    return 0;
}

static bool is_operator(char value) {
    return value == '|' || value == '<' || value == '>' || value == '&';
}

static int lex_word(const char *line, size_t *cursor, TokenList *tokens,
                    char **error_message) {
    Buffer buffer = {0};
    size_t start = *cursor;
    bool started = false;

    while (line[*cursor] != '\0') {
        char current = line[*cursor];

        if (current == ' ' || current == '\t' || current == '\r' ||
            current == '\n' || is_operator(current)) {
            break;
        }
        started = true;
        if (current == '\\') {
            (*cursor)++;
            if (line[*cursor] == '\0') {
                free(buffer.data);
                return set_error(error_message, *cursor - 1U,
                                 "trailing escape");
            }
            if (buffer_push(&buffer, line[*cursor]) < 0) {
                free(buffer.data);
                return -1;
            }
            (*cursor)++;
            continue;
        }
        if (current == '\'' || current == '"') {
            char quote = current;
            size_t quote_position = *cursor;
            (*cursor)++;
            while (line[*cursor] != '\0' && line[*cursor] != quote) {
                if (buffer_push(&buffer, line[*cursor]) < 0) {
                    free(buffer.data);
                    return -1;
                }
                (*cursor)++;
            }
            if (line[*cursor] == '\0') {
                free(buffer.data);
                return set_error(error_message, quote_position,
                                 quote == '\'' ? "unclosed single quote"
                                                : "unclosed double quote");
            }
            (*cursor)++;
            continue;
        }
        if (buffer_push(&buffer, current) < 0) {
            free(buffer.data);
            return -1;
        }
        (*cursor)++;
    }

    if (!started || buffer_push(&buffer, '\0') < 0) {
        free(buffer.data);
        return -1;
    }
    if (token_push(tokens, TOK_WORD, buffer.data, start) < 0) {
        free(buffer.data);
        return -1;
    }
    free(buffer.data);
    return 0;
}

int lex_line(const char *line, TokenList *tokens, char **error_message) {
    size_t cursor = 0U;

    memset(tokens, 0, sizeof(*tokens));
    *error_message = NULL;

    while (line[cursor] != '\0') {
        TokenType type;
        size_t position;

        if (line[cursor] == ' ' || line[cursor] == '\t' ||
            line[cursor] == '\r' || line[cursor] == '\n') {
            cursor++;
            continue;
        }
        if (!is_operator(line[cursor])) {
            if (lex_word(line, &cursor, tokens, error_message) < 0) {
                goto failure;
            }
            continue;
        }

        position = cursor;
        switch (line[cursor]) {
        case '|':
            type = TOK_PIPE;
            cursor++;
            break;
        case '<':
            type = TOK_REDIR_IN;
            cursor++;
            break;
        case '&':
            type = TOK_AMP;
            cursor++;
            break;
        case '>':
            cursor++;
            if (line[cursor] == '>') {
                type = TOK_REDIR_APPEND;
                cursor++;
            } else {
                type = TOK_REDIR_OUT;
            }
            break;
        default:
            type = TOK_END;
            break;
        }
        if (token_push(tokens, type, NULL, position) < 0) {
            goto failure;
        }
    }

    if (token_push(tokens, TOK_END, NULL, cursor) < 0) {
        goto failure;
    }
    return 0;

failure:
    if (*error_message == NULL) {
        (void)set_error(error_message, cursor, "out of memory");
    }
    token_list_free(tokens);
    return -1;
}

void token_list_free(TokenList *tokens) {
    size_t index;

    for (index = 0U; index < tokens->count; index++) {
        free(tokens->items[index].text);
    }
    free(tokens->items);
    memset(tokens, 0, sizeof(*tokens));
}
