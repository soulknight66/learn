#ifndef MINISH_H
#define MINISH_H

#include <stdbool.h>
#include <stddef.h>
#include <sys/types.h>

typedef enum {
    TOK_WORD,
    TOK_PIPE,
    TOK_REDIR_IN,
    TOK_REDIR_OUT,
    TOK_REDIR_APPEND,
    TOK_AMP,
    TOK_END
} TokenType;

typedef struct {
    TokenType type;
    char *text;
} Token;

typedef struct {
    Token *items;
    size_t len;
    size_t capacity;
} TokenList;

typedef struct {
    char **argv;
    size_t argc;
    char *input_path;
    char *output_path;
    bool append_output;
} Command;

typedef struct {
    Command *commands;
    size_t count;
    bool background;
} Pipeline;

typedef struct {
    bool interactive;
    int terminal_fd;
    pid_t shell_pgid;
} ShellContext;

/* On success, the returned list always ends with TOK_END. */
int lex_line(const char *line, TokenList *out, char *error, size_t error_size);
void token_list_free(TokenList *tokens);

/* The parser deep-copies strings; tokens may be freed after this returns. */
int parse_pipeline(const TokenList *tokens, Pipeline *out, char *error,
                   size_t error_size);
void pipeline_free(Pipeline *pipeline);

int execute_pipeline(const Pipeline *pipeline, const ShellContext *context);

/* Reap completed background children without blocking; return children reaped. */
size_t shell_reap_background(void);

#endif
