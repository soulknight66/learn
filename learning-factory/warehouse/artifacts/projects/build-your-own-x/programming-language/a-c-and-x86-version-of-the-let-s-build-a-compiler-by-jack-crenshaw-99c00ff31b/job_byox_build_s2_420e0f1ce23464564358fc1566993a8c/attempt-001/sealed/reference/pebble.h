#ifndef SEALED_PEBBLE_H
#define SEALED_PEBBLE_H

#include <stdint.h>

enum pebble_status {
    PEBBLE_OK = 0,
    PEBBLE_USAGE = 64,
    PEBBLE_SOURCE_ERROR = 65,
    PEBBLE_IO_ERROR = 66,
    PEBBLE_RUNTIME_ERROR = 70
};

int pebble_eval_file(const char *path, uint64_t max_steps);
int pebble_compile_file(const char *input_path, const char *output_path);

#endif
