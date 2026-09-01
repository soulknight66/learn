#ifndef MINISH_PARSER_H
#define MINISH_PARSER_H

#include <stdbool.h>
#include <stddef.h>

#include "lexer.h"
#include "shell.h"

typedef enum {
    REDIRECTION_INPUT = 0,
    REDIRECTION_OUTPUT_TRUNCATE,
    REDIRECTION_OUTPUT_APPEND
} RedirectionKind;

typedef struct {
    RedirectionKind kind;
    char *path;
} Redirection;

typedef struct {
    char **argv;
    size_t argc;
    Redirection *redirections;
    size_t redirection_count;
} Command;

typedef struct {
    Command *commands;
    size_t command_count;
    bool background;
    char *source_text;
} Pipeline;

typedef struct {
    Pipeline *pipelines;
    size_t pipeline_count;
} CommandList;

void pipeline_init(Pipeline *pipeline);
void pipeline_destroy(Pipeline *pipeline);
void command_list_init(CommandList *list);
void command_list_destroy(CommandList *list);

/* Validate the whole source, then build an owned list from its tokens. */
ShellResult parser_parse_list(const char *source, const TokenList *tokens,
                              CommandList *list, ShellError *error);

#endif
