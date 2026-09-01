#include "minic.h"

#include <inttypes.h>
#include <stdio.h>
#include <string.h>

static int usage(const char *program) {
    fprintf(stderr, "usage: %s [--max-steps N] SOURCE\n", program);
    return MINIC_USAGE_ERROR;
}

static int parse_positive_u64(const char *text, uint64_t *out) {
    uint64_t value = 0;
    const unsigned char *cursor = (const unsigned char *)text;

    if (*cursor == '\0') return 0;
    while (*cursor != '\0') {
        unsigned digit;
        if (*cursor < '0' || *cursor > '9') return 0;
        digit = (unsigned)(*cursor - '0');
        if (value > (UINT64_MAX - digit) / UINT64_C(10)) return 0;
        value = value * UINT64_C(10) + digit;
        cursor++;
    }
    if (value == 0) return 0;
    *out = value;
    return 1;
}

int main(int argc, char **argv) {
    uint64_t max_steps = UINT64_C(1000000);
    const char *path;
    MinicSource source;
    int status;

    if (argc == 2 && strncmp(argv[1], "--", 2) != 0) {
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
