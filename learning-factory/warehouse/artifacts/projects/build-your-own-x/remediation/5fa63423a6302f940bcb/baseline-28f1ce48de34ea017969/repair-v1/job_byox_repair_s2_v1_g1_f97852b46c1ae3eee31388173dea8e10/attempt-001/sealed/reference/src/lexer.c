#include "minish.h"

#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum { MAX_INPUT_BYTES = 4096 };

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

static int grow_bytes(char **buffer, size_t *capacity, size_t needed)
{
    size_t next = *capacity == 0 ? 16 : *capacity;
    char *replacement;

    while (next < needed) {
        if (next > ((size_t)-1) / 2) {
            return -1;
        }
        next *= 2;
    }
    replacement = realloc(*buffer, next);
    if (replacement == NULL) {
        return -1;
    }
    *buffer = replacement;
    *capacity = next;
    return 0;
}

static int append_byte(char **buffer, size_t *length, size_t *capacity, char byte)
{
    if (grow_bytes(buffer, capacity, *length + 2) != 0) {
        return -1;
    }
    (*buffer)[(*length)++] = byte;
    (*buffer)[*length] = '\0';
    return 0;
}

static int reserve_tokens(TokenList *tokens, size_t needed)
{
    size_t next = tokens->capacity == 0 ? 8 : tokens->capacity;
    Token *replacement;

    while (next < needed) {
        if (next > ((size_t)-1) / (2 * sizeof(*replacement))) {
            return -1;
        }
        next *= 2;
    }
    replacement = realloc(tokens->items, next * sizeof(*replacement));
    if (replacement == NULL) {
        return -1;
    }
    tokens->items = replacement;
    tokens->capacity = next;
    return 0;
}

static int push_token(TokenList *tokens, TokenType type, const char *text)
{
    char *copy = NULL;

    if (text != NULL) {
        copy = strdup(text);
        if (copy == NULL) {
            return -1;
        }
    }
    if (reserve_tokens(tokens, tokens->len + 1) != 0) {
        free(copy);
        return -1;
    }
    tokens->items[tokens->len++] = (Token){.type = type, .text = copy};
    return 0;
}

static int is_separator(char byte)
{
    return byte == ' ' || byte == '\t' || byte == '\r' || byte == '\n';
}

static int flush_word(TokenList *tokens, char *word, size_t *word_length,
                      bool *word_started)
{
    const char *text;

    if (!*word_started) {
        return 0;
    }
    text = word == NULL ? "" : word;
    if (push_token(tokens, TOK_WORD, text) != 0) {
        return -1;
    }
    *word_length = 0;
    *word_started = false;
    if (word != NULL) {
        word[0] = '\0';
    }
    return 0;
}

void token_list_free(TokenList *tokens)
{
    size_t i;

    if (tokens == NULL) {
        return;
    }
    for (i = 0; i < tokens->len; ++i) {
        free(tokens->items[i].text);
    }
    free(tokens->items);
    *tokens = (TokenList){0};
}

int lex_line(const char *line, TokenList *out, char *error, size_t error_size)
{
    size_t position = 0;
    char *word = NULL;
    size_t word_length = 0;
    size_t word_capacity = 0;
    bool word_started = false;

    if (error != NULL && error_size > 0) {
        error[0] = '\0';
    }
    if (out == NULL) {
        set_error(error, error_size, "lexer output is null");
        return -1;
    }
    *out = (TokenList){0};
    if (line == NULL) {
        set_error(error, error_size, "input is null");
        return -1;
    }
    if (strlen(line) > MAX_INPUT_BYTES) {
        set_error(error, error_size, "input exceeds %d bytes", MAX_INPUT_BYTES);
        return -1;
    }

    while (line[position] != '\0') {
        const char current = line[position];

        if (is_separator(current)) {
            if (flush_word(out, word, &word_length, &word_started) != 0) {
                goto no_memory;
            }
            ++position;
            continue;
        }
        if (current == '#' && !word_started) {
            break;
        }
        if (current == '|' || current == '<' || current == '>' ||
            current == '&') {
            TokenType type;

            if (flush_word(out, word, &word_length, &word_started) != 0) {
                goto no_memory;
            }
            if (current == '|') {
                type = TOK_PIPE;
            } else if (current == '<') {
                type = TOK_REDIR_IN;
            } else if (current == '&') {
                type = TOK_AMP;
            } else if (line[position + 1] == '>') {
                type = TOK_REDIR_APPEND;
                ++position;
            } else {
                type = TOK_REDIR_OUT;
            }
            if (push_token(out, type, NULL) != 0) {
                goto no_memory;
            }
            ++position;
            continue;
        }
        if (current == '\\') {
            word_started = true;
            ++position;
            if (line[position] == '\0') {
                set_error(error, error_size, "trailing backslash");
                goto failure;
            }
            if (append_byte(&word, &word_length, &word_capacity,
                            line[position++]) != 0) {
                goto no_memory;
            }
            continue;
        }
        if (current == '\'' || current == '"') {
            const char quote = current;

            word_started = true;
            ++position;
            while (line[position] != quote) {
                if (line[position] == '\0') {
                    set_error(error, error_size,
                              quote == '\'' ? "unterminated single quote"
                                             : "unterminated double quote");
                    goto failure;
                }
                if (quote == '"' && line[position] == '\\') {
                    ++position;
                    if (line[position] == '\0') {
                        set_error(error, error_size,
                                  "trailing backslash in double quote");
                        goto failure;
                    }
                }
                if (append_byte(&word, &word_length, &word_capacity,
                                line[position++]) != 0) {
                    goto no_memory;
                }
            }
            ++position;
            continue;
        }

        word_started = true;
        if (append_byte(&word, &word_length, &word_capacity, current) != 0) {
            goto no_memory;
        }
        ++position;
    }

    if (flush_word(out, word, &word_length, &word_started) != 0 ||
        push_token(out, TOK_END, NULL) != 0) {
        goto no_memory;
    }
    free(word);
    return 0;

no_memory:
    set_error(error, error_size, "out of memory while lexing");
failure:
    free(word);
    token_list_free(out);
    return -1;
}
