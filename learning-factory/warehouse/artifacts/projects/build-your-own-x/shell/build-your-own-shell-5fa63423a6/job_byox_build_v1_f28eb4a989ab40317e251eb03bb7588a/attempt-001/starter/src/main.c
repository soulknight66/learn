#define _POSIX_C_SOURCE 200809L

#include "byosh.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static int run_line(char *line, int interactive, int *did_execute)
{
    struct byosh_pipeline pipeline;
    char error[160];
    enum byosh_parse_status status;

    *did_execute = 0;
    status = byosh_parse_line(line, &pipeline, error, sizeof(error));
    if (status == BYOSH_PARSE_EMPTY) {
        return 0;
    }
    *did_execute = 1;
    if (status != BYOSH_PARSE_OK) {
        (void)fprintf(stderr, "byosh: %s\n",
                      error[0] == '\0' ? "parse failed" : error);
        return 2;
    }
    return byosh_execute_pipeline(&pipeline, interactive);
}

int main(int argc, char **argv)
{
    char *line = NULL;
    size_t capacity = 0U;
    int interactive;
    int result = 0;
    int did_execute;

    if (argc == 3 && strcmp(argv[1], "-c") == 0) {
        line = strdup(argv[2]);
        if (line == NULL) {
            perror("strdup");
            return 1;
        }
        result = run_line(line, 0, &did_execute);
        free(line);
        return result;
    }
    if (argc != 1) {
        (void)fprintf(stderr, "usage: %s [-c command]\n", argv[0]);
        return 2;
    }

    interactive = isatty(STDIN_FILENO);
    for (;;) {
        ssize_t length;
        if (interactive) {
            (void)fputs("byosh$ ", stderr);
            (void)fflush(stderr);
        }
        length = getline(&line, &capacity, stdin);
        if (length < 0) {
            break;
        }
        {
            int line_result = run_line(line, interactive, &did_execute);
            if (did_execute) {
                result = line_result;
            }
        }
    }
    free(line);
    return result;
}
