#include "minic.h"

#include <errno.h>
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int usage(const char *program) {
    fprintf(stderr, "usage: %s [--max-steps N] SOURCE\n", program);
    return MINIC_USAGE_ERROR;
}

static int parse_positive_u64(const char *text, uint64_t *out) {
    char *end = NULL;
    uintmax_t value;

    if (text[0] == '\0' || text[0] == '-') {
        return 0;
    }
    errno = 0;
    value = strtoumax(text, &end, 10);
    if (errno == ERANGE || *end != '\0' || value == 0 || value > UINT64_MAX) {
        return 0;
    }
    *out = (uint64_t)value;
    return 1;
}

int main(int argc, char **argv) {
    uint64_t max_steps = UINT64_C(1000000);
    const char *path;
    MinicSource source;
    int status;

    if (argc == 2) {
        path = argv[1];
    } else if (argc == 4 && strcmp(argv[1], "--max-steps") == 0) {
        if (!parse_positive_u64(argv[2], &max_steps)) {
            return usage(argv[0]);
        }
        path = argv[3];
    } else {
        return usage(argv[0]);
    }

    status = minic_load_source(path, &source);
    if (status != MINIC_OK) {
        return status;
    }
    status = minic_run(&source, max_steps);
    minic_free_source(&source);
    return status;
}
