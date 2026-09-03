#include "pebble.h"

#include <inttypes.h>
#include <stdio.h>

int pebble_eval_file(const char *path, uint64_t max_steps) {
    (void)path;
    (void)max_steps;
    fprintf(stderr,
            "1:1: starter incomplete: implement lexer, parser, and evaluator\n");
    return PEBBLE_SOURCE_ERROR;
}

int pebble_compile_file(const char *input_path, const char *output_path) {
    (void)input_path;
    (void)output_path;
    fprintf(stderr,
            "1:1: starter incomplete: implement parser and x86-64 backend\n");
    return PEBBLE_SOURCE_ERROR;
}
