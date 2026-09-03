#include "ember.h"

#include <stdio.h>

int ember_execute(const Bytecode *code, const int64_t *arguments,
                  size_t argument_count, uint64_t max_steps,
                  int64_t *return_value, char *error, size_t error_size) {
    (void)code;
    (void)arguments;
    (void)argument_count;
    (void)max_steps;
    if (return_value != NULL) {
        *return_value = 0;
    }
    if (error != NULL && error_size > 0U) {
        (void)snprintf(error, error_size, "VM not implemented in starter");
    }
    return 1;
}
