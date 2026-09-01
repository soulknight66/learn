#include "pebble.h"

#include <stdlib.h>

struct PebbleProgram {
    unsigned char reserved;
};

PebbleOptions pebble_default_options(void) {
    PebbleOptions options;
    options.max_code = 65536;
    options.max_constants = 4096;
    options.max_symbols = 1024;
    options.max_stack = 1024;
    options.max_steps = UINT64_C(1000000);
    return options;
}

PebbleResult pebble_compile(const char *source, const PebbleOptions *options,
                            PebbleProgram **out_program, FILE *diagnostics) {
    (void)options;
    if (source == NULL || out_program == NULL || diagnostics == NULL) {
        return PEBBLE_SYSTEM_ERROR;
    }
    *out_program = NULL;
    fputs("1:1: compiler not implemented\n", diagnostics);
    return PEBBLE_COMPILE_ERROR;
}

PebbleResult pebble_execute(const PebbleProgram *program, const PebbleOptions *options,
                            FILE *output, FILE *diagnostics) {
    (void)program;
    (void)options;
    (void)output;
    (void)diagnostics;
    return PEBBLE_SYSTEM_ERROR;
}

PebbleResult pebble_run(const char *source, const PebbleOptions *options,
                        FILE *output, FILE *diagnostics) {
    PebbleProgram *program = NULL;
    PebbleResult result;
    if (output == NULL || diagnostics == NULL) {
        return PEBBLE_SYSTEM_ERROR;
    }
    result = pebble_compile(source, options, &program, diagnostics);
    if (result == PEBBLE_OK) {
        result = pebble_execute(program, options, output, diagnostics);
    }
    pebble_program_free(program);
    return result;
}

void pebble_program_free(PebbleProgram *program) {
    free(program);
}
