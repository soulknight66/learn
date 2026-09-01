#ifndef PEBBLE_H
#define PEBBLE_H

#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

typedef enum {
    PEBBLE_OK = 0,
    PEBBLE_COMPILE_ERROR = 1,
    PEBBLE_RUNTIME_ERROR = 2,
    PEBBLE_LIMIT_ERROR = 3,
    PEBBLE_SYSTEM_ERROR = 4
} PebbleResult;

typedef struct {
    size_t max_code;
    size_t max_constants;
    size_t max_symbols;
    size_t max_stack;
    uint64_t max_steps;
} PebbleOptions;

typedef struct PebbleProgram PebbleProgram;

PebbleOptions pebble_default_options(void);

PebbleResult pebble_compile(const char *source, const PebbleOptions *options,
                            PebbleProgram **out_program, FILE *diagnostics);

PebbleResult pebble_execute(const PebbleProgram *program, const PebbleOptions *options,
                            FILE *output, FILE *diagnostics);

PebbleResult pebble_run(const char *source, const PebbleOptions *options,
                        FILE *output, FILE *diagnostics);

void pebble_program_free(PebbleProgram *program);

#endif
