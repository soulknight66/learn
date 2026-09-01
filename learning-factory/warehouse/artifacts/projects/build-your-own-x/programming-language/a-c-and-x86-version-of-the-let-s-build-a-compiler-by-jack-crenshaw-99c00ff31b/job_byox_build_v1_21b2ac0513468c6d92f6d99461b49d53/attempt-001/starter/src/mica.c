#include "mica_limits.h"

#include <inttypes.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/*
 * Stage 1 is supplied: a bounded lexer and the `tokens` CLI mode.
 *
 * TODO(stage 2): define AST ownership and add the recursive-descent parser.
 * TODO(stage 3): validate declarations and assign deterministic slots.
 * TODO(stage 4): implement the tree-walking `run` mode.
 * TODO(stage 5): implement the x86-64 `compile` mode.
 */

typedef enum {
    TK_EOF,
    TK_INTEGER,
    TK_IDENTIFIER,
    TK_LET,
    TK_PRINT,
    TK_IF,
    TK_ELSE,
    TK_WHILE,
    TK_LPAREN,
    TK_RPAREN,
    TK_LBRACE,
    TK_RBRACE,
    TK_SEMICOLON,
    TK_PLUS,
    TK_MINUS,
    TK_STAR,
    TK_SLASH,
    TK_PERCENT,
    TK_ASSIGN,
    TK_EQUAL_EQUAL,
    TK_BANG_EQUAL,
    TK_LESS,
    TK_LESS_EQUAL,
    TK_GREATER,
    TK_GREATER_EQUAL
} TokenKind;

typedef struct {
    TokenKind kind;
    const char *start;
    size_t length;
    size_t line;
    size_t column;
    uint64_t value;
} Token;

typedef struct {
    Token *items;
    size_t count;
    size_t capacity;
    char error[192];
} TokenList;

static const char *token_kind_name(TokenKind kind) {
    static const char *const names[] = {
        "EOF",          "INTEGER",       "IDENTIFIER", "LET",
        "PRINT",        "IF",            "ELSE",       "WHILE",
        "LPAREN",       "RPAREN",        "LBRACE",     "RBRACE",
        "SEMICOLON",    "PLUS",          "MINUS",      "STAR",
        "SLASH",        "PERCENT",       "ASSIGN",     "EQUAL_EQUAL",
        "BANG_EQUAL",   "LESS",          "LESS_EQUAL", "GREATER",
        "GREATER_EQUAL"
    };
    return names[(int)kind];
}

static bool ascii_alpha(unsigned char c) {
    return (c >= (unsigned char)'a' && c <= (unsigned char)'z') ||
           (c >= (unsigned char)'A' && c <= (unsigned char)'Z') || c == '_';
}

static bool ascii_digit(unsigned char c) {
    return c >= (unsigned char)'0' && c <= (unsigned char)'9';
}

static bool push_token(TokenList *list, Token token) {
    Token *larger;
    size_t capacity;
    if (list->count < list->capacity) {
        list->items[list->count++] = token;
        return true;
    }
    capacity = list->capacity == 0 ? 128 : list->capacity * 2;
    larger = (Token *)realloc(list->items, capacity * sizeof(*larger));
    if (larger == NULL) {
        snprintf(list->error, sizeof(list->error),
                 "out of memory while storing tokens");
        return false;
    }
    list->items = larger;
    list->capacity = capacity;
    list->items[list->count++] = token;
    return true;
}

static TokenKind word_kind(const char *text, size_t length) {
    if (length == 3 && memcmp(text, "let", 3) == 0) {
        return TK_LET;
    }
    if (length == 5 && memcmp(text, "print", 5) == 0) {
        return TK_PRINT;
    }
    if (length == 2 && memcmp(text, "if", 2) == 0) {
        return TK_IF;
    }
    if (length == 4 && memcmp(text, "else", 4) == 0) {
        return TK_ELSE;
    }
    if (length == 5 && memcmp(text, "while", 5) == 0) {
        return TK_WHILE;
    }
    return TK_IDENTIFIER;
}

static bool lex(const char *source, size_t length, TokenList *tokens) {
    size_t at = 0;
    size_t line = 1;
    size_t column = 1;
    while (at < length) {
        unsigned char c = (unsigned char)source[at];
        size_t begin;
        size_t begin_column;
        Token token;

        if (c == ' ' || c == '\t' || c == '\r') {
            ++at;
            ++column;
            continue;
        }
        if (c == '\n') {
            ++at;
            ++line;
            column = 1;
            continue;
        }
        if (c == '/' && at + 1 < length && source[at + 1] == '/') {
            at += 2;
            column += 2;
            while (at < length && source[at] != '\n') {
                ++at;
                ++column;
            }
            continue;
        }

        memset(&token, 0, sizeof(token));
        token.start = source + at;
        token.length = 1;
        token.line = line;
        token.column = column;

        if (ascii_alpha(c)) {
            begin = at;
            begin_column = column;
            do {
                ++at;
                ++column;
            } while (at < length &&
                     (ascii_alpha((unsigned char)source[at]) ||
                      ascii_digit((unsigned char)source[at])));
            token.start = source + begin;
            token.length = at - begin;
            token.column = begin_column;
            token.kind = word_kind(token.start, token.length);
            if (!push_token(tokens, token)) {
                return false;
            }
            continue;
        }

        if (ascii_digit(c)) {
            uint64_t value = 0;
            begin = at;
            begin_column = column;
            while (at < length && ascii_digit((unsigned char)source[at])) {
                unsigned digit = (unsigned)(source[at] - '0');
                if (value > (UINT64_C(9223372036854775807) - digit) / 10) {
                    snprintf(tokens->error, sizeof(tokens->error),
                             "%zu:%zu: integer literal is outside signed 64-bit range",
                             line, begin_column);
                    return false;
                }
                value = value * 10 + digit;
                ++at;
                ++column;
            }
            token.kind = TK_INTEGER;
            token.start = source + begin;
            token.length = at - begin;
            token.column = begin_column;
            token.value = value;
            if (!push_token(tokens, token)) {
                return false;
            }
            continue;
        }

        ++at;
        ++column;
        switch (c) {
            case '(':
                token.kind = TK_LPAREN;
                break;
            case ')':
                token.kind = TK_RPAREN;
                break;
            case '{':
                token.kind = TK_LBRACE;
                break;
            case '}':
                token.kind = TK_RBRACE;
                break;
            case ';':
                token.kind = TK_SEMICOLON;
                break;
            case '+':
                token.kind = TK_PLUS;
                break;
            case '-':
                token.kind = TK_MINUS;
                break;
            case '*':
                token.kind = TK_STAR;
                break;
            case '/':
                token.kind = TK_SLASH;
                break;
            case '%':
                token.kind = TK_PERCENT;
                break;
            case '=':
                if (at < length && source[at] == '=') {
                    ++at;
                    ++column;
                    token.kind = TK_EQUAL_EQUAL;
                    token.length = 2;
                } else {
                    token.kind = TK_ASSIGN;
                }
                break;
            case '!':
                if (at < length && source[at] == '=') {
                    ++at;
                    ++column;
                    token.kind = TK_BANG_EQUAL;
                    token.length = 2;
                } else {
                    snprintf(tokens->error, sizeof(tokens->error),
                             "%zu:%zu: unexpected '!' (only '!=' is valid)", line,
                             token.column);
                    return false;
                }
                break;
            case '<':
                if (at < length && source[at] == '=') {
                    ++at;
                    ++column;
                    token.kind = TK_LESS_EQUAL;
                    token.length = 2;
                } else {
                    token.kind = TK_LESS;
                }
                break;
            case '>':
                if (at < length && source[at] == '=') {
                    ++at;
                    ++column;
                    token.kind = TK_GREATER_EQUAL;
                    token.length = 2;
                } else {
                    token.kind = TK_GREATER;
                }
                break;
            default:
                snprintf(tokens->error, sizeof(tokens->error),
                         "%zu:%zu: unexpected byte 0x%02x", line, token.column,
                         (unsigned)c);
                return false;
        }
        if (!push_token(tokens, token)) {
            return false;
        }
    }

    {
        Token eof;
        memset(&eof, 0, sizeof(eof));
        eof.kind = TK_EOF;
        eof.start = source + length;
        eof.line = line;
        eof.column = column;
        return push_token(tokens, eof);
    }
}

static bool read_source(const char *path, char **source_out, size_t *length_out,
                        char *error, size_t error_size) {
    FILE *input = fopen(path, "rb");
    char *source;
    size_t count;
    if (input == NULL) {
        snprintf(error, error_size, "cannot open input file");
        return false;
    }
    source = (char *)malloc((size_t)MICA_SOURCE_LIMIT + 2);
    if (source == NULL) {
        (void)fclose(input);
        snprintf(error, error_size, "out of memory while reading input");
        return false;
    }
    count = fread(source, 1, (size_t)MICA_SOURCE_LIMIT + 1, input);
    if (ferror(input)) {
        free(source);
        (void)fclose(input);
        snprintf(error, error_size, "cannot read input file");
        return false;
    }
    if (count > (size_t)MICA_SOURCE_LIMIT) {
        free(source);
        (void)fclose(input);
        snprintf(error, error_size, "source exceeds 1048576-byte limit");
        return false;
    }
    if (fclose(input) != 0) {
        free(source);
        snprintf(error, error_size, "cannot close input file");
        return false;
    }
    source[count] = '\0';
    *source_out = source;
    *length_out = count;
    return true;
}

static int print_tokens(const TokenList *tokens) {
    size_t i;
    for (i = 0; i < tokens->count; ++i) {
        const Token *token = &tokens->items[i];
        if (token->kind == TK_EOF) {
            printf("%zu:%zu %s -\n", token->line, token->column,
                   token_kind_name(token->kind));
        } else if (token->kind == TK_INTEGER) {
            printf("%zu:%zu %s %" PRIu64 "\n", token->line, token->column,
                   token_kind_name(token->kind), token->value);
        } else {
            printf("%zu:%zu %s %.*s\n", token->line, token->column,
                   token_kind_name(token->kind), (int)token->length,
                   token->start);
        }
    }
    return ferror(stdout) ? 1 : 0;
}

static int unfinished_pipeline(const char *mode, const TokenList *tokens) {
    (void)mode;
    (void)tokens;
    /* Replace this function as stages 2--5 are implemented. */
    fprintf(stderr,
            "mica: implementation error: parser and backend stages are not implemented\n");
    return 3;
}

static void usage(void) {
    fprintf(stderr,
            "usage: mica tokens FILE\n"
            "       mica run FILE\n"
            "       mica compile FILE -o OUTPUT.s\n");
}

int main(int argc, char **argv) {
    const char *mode;
    const char *input_path;
    char *source = NULL;
    size_t source_length = 0;
    char io_error[160];
    TokenList tokens;
    int result;

    if ((argc == 3 &&
         (strcmp(argv[1], "tokens") == 0 || strcmp(argv[1], "run") == 0)) ||
        (argc == 5 && strcmp(argv[1], "compile") == 0 &&
         strcmp(argv[3], "-o") == 0)) {
        mode = argv[1];
        input_path = argv[2];
    } else {
        usage();
        return 2;
    }

    memset(io_error, 0, sizeof(io_error));
    if (!read_source(input_path, &source, &source_length, io_error,
                     sizeof(io_error))) {
        fprintf(stderr, "mica: I/O error: %s\n", io_error);
        return 1;
    }
    memset(&tokens, 0, sizeof(tokens));
    if (!lex(source, source_length, &tokens)) {
        fprintf(stderr, "mica: lexical error: %s\n", tokens.error);
        free(tokens.items);
        free(source);
        return 1;
    }

    if (strcmp(mode, "tokens") == 0) {
        result = print_tokens(&tokens);
    } else {
        result = unfinished_pipeline(mode, &tokens);
    }
    free(tokens.items);
    free(source);
    return result;
}
