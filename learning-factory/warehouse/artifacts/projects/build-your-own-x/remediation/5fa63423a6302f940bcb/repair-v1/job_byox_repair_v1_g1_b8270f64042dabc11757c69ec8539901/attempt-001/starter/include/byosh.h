#ifndef BYOSH_H
#define BYOSH_H

#include <stddef.h>

#define BYOSH_MAX_COMMANDS 16U
#define BYOSH_MAX_ARGS 64U

enum byosh_parse_status {
    BYOSH_PARSE_OK = 0,
    BYOSH_PARSE_EMPTY = 1,
    BYOSH_PARSE_ERROR = 2,
    BYOSH_PARSE_TODO = 3
};

struct byosh_command {
    char *argv[BYOSH_MAX_ARGS + 1U];
    size_t argc;
    char *input_path;
    char *output_path;
    int append_output;
};

struct byosh_pipeline {
    struct byosh_command commands[BYOSH_MAX_COMMANDS];
    size_t command_count;
    int background;
};

void byosh_pipeline_init(struct byosh_pipeline *pipeline);

/*
 * Parse one writable, NUL-terminated line. Successful argv and path pointers
 * refer into line and remain valid only while that buffer remains alive.
 */
enum byosh_parse_status byosh_parse_line(char *line,
                                         struct byosh_pipeline *pipeline,
                                         char *error,
                                         size_t error_size);

/* Milestone hook: replace the starter implementation with process execution. */
int byosh_execute_pipeline(const struct byosh_pipeline *pipeline, int interactive);

#endif
