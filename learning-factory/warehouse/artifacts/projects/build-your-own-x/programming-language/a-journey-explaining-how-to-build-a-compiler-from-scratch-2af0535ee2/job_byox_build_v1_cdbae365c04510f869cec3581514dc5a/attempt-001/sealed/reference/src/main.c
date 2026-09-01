#include "pebble.h"

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define INPUT_LIMIT ((size_t)1048576)

static int result_exit_status(PebbleResult result) {
    switch (result) {
        case PEBBLE_OK: return 0;
        case PEBBLE_COMPILE_ERROR: return 65;
        case PEBBLE_RUNTIME_ERROR:
        case PEBBLE_LIMIT_ERROR: return 70;
        case PEBBLE_SYSTEM_ERROR:
        default: return 74;
    }
}

static char *read_source(const char *path) {
    FILE *stream = fopen(path, "rb");
    char *buffer;
    size_t used;
    if (stream == NULL) {
        fprintf(stderr, "input: cannot open '%s': %s\n", path, strerror(errno));
        return NULL;
    }
    buffer = malloc(INPUT_LIMIT + 2);
    if (buffer == NULL) {
        fputs("input: allocation failed\n", stderr);
        fclose(stream);
        return NULL;
    }
    used = fread(buffer, 1, INPUT_LIMIT + 1, stream);
    if (ferror(stream)) {
        fprintf(stderr, "input: cannot read '%s'\n", path);
        free(buffer);
        fclose(stream);
        return NULL;
    }
    if (used > INPUT_LIMIT) {
        fprintf(stderr, "input: '%s' exceeds 1 MiB\n", path);
        free(buffer);
        fclose(stream);
        return NULL;
    }
    if (fclose(stream) != 0) {
        fprintf(stderr, "input: cannot close '%s'\n", path);
        free(buffer);
        return NULL;
    }
    buffer[used] = '\0';
    return buffer;
}

int main(int argc, char **argv) {
    const char *source;
    char *owned_source = NULL;
    PebbleResult result;
    if (argc == 3 && strcmp(argv[1], "-e") == 0) {
        if (strlen(argv[2]) > INPUT_LIMIT) {
            fputs("input: expression source exceeds 1 MiB\n", stderr);
            return 74;
        }
        source = argv[2];
    } else if (argc == 2 && strcmp(argv[1], "-e") != 0) {
        owned_source = read_source(argv[1]);
        if (owned_source == NULL) return 74;
        source = owned_source;
    } else {
        fputs("usage: pebble FILE | pebble -e SOURCE\n", stderr);
        return 64;
    }
    result = pebble_run(source, NULL, stdout, stderr);
    free(owned_source);
    return result_exit_status(result);
}
