#include "pebble.h"

#include <errno.h>
#include <inttypes.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void usage(const char *program) {
    fprintf(stderr,
            "usage: %s eval [--max-steps N] PROGRAM.pb\n"
            "       %s compile PROGRAM.pb -o PROGRAM.s\n",
            program, program);
}

static int parse_steps(const char *text, uint64_t *value) {
    char *end = NULL;
    uintmax_t parsed;

    errno = 0;
    parsed = strtoumax(text, &end, 10);
    if (errno != 0 || end == text || *end != '\0' || parsed < 1 ||
        parsed > UINT64_C(1000000000)) {
        return 0;
    }
    *value = (uint64_t)parsed;
    return 1;
}

int main(int argc, char **argv) {
    if (signal(SIGPIPE, SIG_IGN) == SIG_ERR) {
        fprintf(stderr, "I/O error: cannot configure output handling\n");
        return PEBBLE_IO_ERROR;
    }

    if (argc < 2) {
        usage(argv[0]);
        return PEBBLE_USAGE;
    }

    if (strcmp(argv[1], "eval") == 0) {
        uint64_t max_steps = UINT64_C(1000000);
        const char *path = NULL;

        if (argc == 3) {
            path = argv[2];
        } else if (argc == 5 && strcmp(argv[2], "--max-steps") == 0 &&
                   parse_steps(argv[3], &max_steps)) {
            path = argv[4];
        } else {
            usage(argv[0]);
            return PEBBLE_USAGE;
        }
        return pebble_eval_file(path, max_steps);
    }

    if (strcmp(argv[1], "compile") == 0) {
        if (argc != 5 || strcmp(argv[3], "-o") != 0) {
            usage(argv[0]);
            return PEBBLE_USAGE;
        }
        return pebble_compile_file(argv[2], argv[4]);
    }

    usage(argv[0]);
    return PEBBLE_USAGE;
}
