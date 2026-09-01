#include "msh.h"

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static int run_line(const char *line)
{
    msh_pipeline pipeline;
    char error[160];
    msh_parse_result result;

    result = msh_parse_line(line, &pipeline, error, sizeof(error));
    if (result == MSH_PARSE_EMPTY) {
        return 0;
    }
    if (result == MSH_PARSE_ERROR) {
        (void)fprintf(stderr, "msh: %s\n", error);
        return 2;
    }

    /* TODO(stages 2-5): dispatch built-ins or execute the whole pipeline. */
    (void)fprintf(stderr, "msh: executor milestone is not implemented\n");
    msh_pipeline_destroy(&pipeline);
    return 2;
}

static int run_stream(void)
{
    char *line = NULL;
    size_t capacity = 0;
    int last_status = 0;
    const int interactive = isatty(STDIN_FILENO);

    for (;;) {
        ssize_t length;

        if (interactive) {
            (void)fputs("msh$ ", stdout);
            (void)fflush(stdout);
        }
        errno = 0;
        length = getline(&line, &capacity, stdin);
        if (length < 0) {
            if (errno == EINTR) {
                clearerr(stdin);
                continue;
            }
            break;
        }
        last_status = run_line(line);
    }
    free(line);
    return last_status;
}

int main(int argc, char **argv)
{
    if (argc == 1) {
        return run_stream();
    }
    if (argc == 3 && strcmp(argv[1], "-c") == 0) {
        return run_line(argv[2]);
    }
    (void)fprintf(stderr, "usage: msh [-c command]\n");
    return 2;
}
