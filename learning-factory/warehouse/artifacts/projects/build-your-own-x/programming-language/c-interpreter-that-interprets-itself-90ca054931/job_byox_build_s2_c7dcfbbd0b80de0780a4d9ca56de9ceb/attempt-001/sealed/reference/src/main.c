#include "ember.h"

#include <errno.h>
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef enum {
    MODE_RUN,
    MODE_CHECK,
    MODE_TOKENS,
    MODE_EMIT,
    MODE_TOWER
} Mode;

static void usage(const char *program) {
    fprintf(stderr, "usage: %s SOURCE [-- INTEGER ...]\n", program);
    fprintf(stderr, "       %s --check SOURCE\n", program);
    fprintf(stderr, "       %s --tokens SOURCE\n", program);
    fprintf(stderr, "       %s --emit SOURCE OUTPUT\n", program);
    fprintf(stderr, "       %s --tower SOURCE\n", program);
    fprintf(stderr,
            "       %s --max-steps POSITIVE_INTEGER SOURCE [-- INTEGER ...]\n",
            program);
}

static int read_source(const char *path, char **data, size_t *length,
                       char *error, size_t error_size) {
    FILE *stream = fopen(path, "rb");
    long measured;
    size_t got;
    if (stream == NULL) {
        (void)snprintf(error, error_size, "%s:1:1: cannot open: %s", path,
                       strerror(errno));
        return 1;
    }
    if (fseek(stream, 0L, SEEK_END) != 0 ||
        (measured = ftell(stream)) < 0L || fseek(stream, 0L, SEEK_SET) != 0) {
        (void)snprintf(error, error_size, "%s:1:1: cannot measure source",
                       path);
        (void)fclose(stream);
        return 1;
    }
    if ((unsigned long)measured > EMBER_SOURCE_MAX) {
        (void)snprintf(error, error_size,
                       "%s:1:1: source exceeds %u bytes", path,
                       EMBER_SOURCE_MAX);
        (void)fclose(stream);
        return 1;
    }
    *data = malloc((size_t)measured + 1U);
    if (*data == NULL) {
        (void)snprintf(error, error_size, "%s:1:1: out of memory", path);
        (void)fclose(stream);
        return 1;
    }
    got = fread(*data, 1U, (size_t)measured, stream);
    if (got != (size_t)measured) {
        (void)snprintf(error, error_size, "%s:1:1: incomplete source read",
                       path);
        free(*data);
        *data = NULL;
        (void)fclose(stream);
        return 1;
    }
    if (fclose(stream) != 0) {
        (void)snprintf(error, error_size, "%s:1:1: source close failed",
                       path);
        free(*data);
        *data = NULL;
        return 1;
    }
    (*data)[got] = '\0';
    *length = got;
    return 0;
}

static int parse_i64(const char *text, int64_t *value) {
    char *end = NULL;
    intmax_t parsed;
    errno = 0;
    parsed = strtoimax(text, &end, 10);
    if (errno == ERANGE || end == text || *end != '\0' ||
        parsed < INT64_MIN || parsed > INT64_MAX) {
        return 1;
    }
    *value = (int64_t)parsed;
    return 0;
}

static int parse_steps(const char *text, uint64_t *value) {
    char *end = NULL;
    uintmax_t parsed;
    if (text[0] == '-' || text[0] == '\0') {
        return 1;
    }
    errno = 0;
    parsed = strtoumax(text, &end, 10);
    if (errno == ERANGE || *end != '\0' || parsed == 0U ||
        parsed > UINT64_MAX) {
        return 1;
    }
    *value = (uint64_t)parsed;
    return 0;
}

static int emit_file(const char *path, const EmberProgram *program,
                     char *error, size_t error_size) {
    FILE *stream = fopen(path, "wb");
    size_t index;
    if (stream == NULL) {
        (void)snprintf(error, error_size, "%s: cannot create: %s", path,
                       strerror(errno));
        return 1;
    }
    for (index = 0U; index < program->count; index++) {
        if (fprintf(stream, "%" PRId64 "\n", program->words[index]) < 0) {
            (void)snprintf(error, error_size, "%s: bytecode write failed",
                           path);
            (void)fclose(stream);
            return 1;
        }
    }
    if (fclose(stream) != 0) {
        (void)snprintf(error, error_size, "%s: bytecode close failed", path);
        return 1;
    }
    return 0;
}

int main(int argc, char **argv) {
    Mode mode = MODE_RUN;
    const char *source_path = NULL;
    const char *output_path = NULL;
    int argument_marker = -1;
    uint64_t max_steps = EMBER_DEFAULT_STEPS;
    char *source = NULL;
    size_t source_length = 0U;
    char error[512];
    EmberProgram *program = NULL;
    int64_t *arguments = NULL;
    size_t argument_count = 0U;
    int64_t return_value = 0;
    int status = 1;
    int index;

    if (argc < 2) {
        usage(argv[0]);
        return 2;
    }
    if (strcmp(argv[1], "--check") == 0 && argc == 3) {
        mode = MODE_CHECK;
        source_path = argv[2];
    } else if (strcmp(argv[1], "--tokens") == 0 && argc == 3) {
        mode = MODE_TOKENS;
        source_path = argv[2];
    } else if (strcmp(argv[1], "--emit") == 0 && argc == 4) {
        mode = MODE_EMIT;
        source_path = argv[2];
        output_path = argv[3];
    } else if (strcmp(argv[1], "--tower") == 0 && argc == 3) {
        mode = MODE_TOWER;
        source_path = argv[2];
    } else if (strcmp(argv[1], "--max-steps") == 0 && argc >= 4) {
        if (parse_steps(argv[2], &max_steps) != 0) {
            fprintf(stderr, "invalid positive instruction budget: %s\n",
                    argv[2]);
            return 2;
        }
        source_path = argv[3];
        argument_marker = 4;
    } else if (argv[1][0] != '-') {
        source_path = argv[1];
        argument_marker = 2;
    } else {
        usage(argv[0]);
        return 2;
    }

    if (mode == MODE_RUN && argument_marker < argc) {
        if (strcmp(argv[argument_marker], "--") != 0) {
            usage(argv[0]);
            return 2;
        }
        argument_count = (size_t)(argc - argument_marker - 1);
        if (argument_count > 0U) {
            arguments = calloc(argument_count, sizeof(*arguments));
            if (arguments == NULL) {
                fprintf(stderr, "out of memory while reading arguments\n");
                return 1;
            }
        }
        for (index = argument_marker + 1; index < argc; index++) {
            if (parse_i64(argv[index],
                          &arguments[(size_t)(index - argument_marker - 1)]) !=
                0) {
                fprintf(stderr, "invalid signed 64-bit argument: %s\n",
                        argv[index]);
                free(arguments);
                return 2;
            }
        }
    }

    if (read_source(source_path, &source, &source_length, error,
                    sizeof(error)) != 0) {
        fprintf(stderr, "%s\n", error);
        goto cleanup;
    }

    if (mode == MODE_TOKENS) {
        status = ember_dump_tokens(source_path, source, source_length, stdout,
                                   error, sizeof(error));
        if (status != 0) {
            fprintf(stderr, "%s\n", error);
        }
        goto cleanup;
    }

    program = calloc(1U, sizeof(*program));
    if (program == NULL) {
        fprintf(stderr, "%s:1:1: out of memory\n", source_path);
        goto cleanup;
    }
    if (ember_compile(source_path, source, source_length, program, error,
                      sizeof(error)) != 0) {
        fprintf(stderr, "%s\n", error);
        goto cleanup;
    }

    if (mode == MODE_CHECK) {
        status = 0;
    } else if (mode == MODE_EMIT) {
        status = emit_file(output_path, program, error, sizeof(error));
        if (status != 0) {
            fprintf(stderr, "%s\n", error);
        }
    } else if (mode == MODE_TOWER) {
        int64_t *tower_arguments =
            calloc(program->count + 1U, sizeof(*tower_arguments));
        if (tower_arguments == NULL) {
            fprintf(stderr, "out of memory while constructing tower input\n");
            goto cleanup;
        }
        tower_arguments[0] = 0;
        for (index = 0; (size_t)index < program->count; index++) {
            tower_arguments[(size_t)index + 1U] =
                program->words[(size_t)index];
        }
        status = ember_execute(program, tower_arguments, program->count + 1U,
                               max_steps, stdout, &return_value, error,
                               sizeof(error));
        free(tower_arguments);
        if (status != 0) {
            fprintf(stderr, "%s\n", error);
        }
    } else {
        status = ember_execute(program, arguments, argument_count, max_steps,
                               stdout, &return_value, error, sizeof(error));
        if (status != 0) {
            fprintf(stderr, "%s\n", error);
        }
    }

cleanup:
    free(arguments);
    free(program);
    free(source);
    return status;
}
