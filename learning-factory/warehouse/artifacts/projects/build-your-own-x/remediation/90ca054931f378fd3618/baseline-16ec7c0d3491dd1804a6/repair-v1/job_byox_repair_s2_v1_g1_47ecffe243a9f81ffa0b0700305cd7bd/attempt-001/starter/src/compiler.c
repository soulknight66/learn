#include "ember.h"

#include <stdio.h>

int ember_compile(const char *path, const char *source, size_t length,
                  Bytecode *output, char *error, size_t error_size) {
    (void)source;
    (void)length;
    if (output != NULL) {
        output->count = 0U;
    }
    if (error != NULL && error_size > 0U) {
        (void)snprintf(error, error_size,
                       "%s:1:1: compiler not implemented in starter", path);
    }
    return 1;
}
