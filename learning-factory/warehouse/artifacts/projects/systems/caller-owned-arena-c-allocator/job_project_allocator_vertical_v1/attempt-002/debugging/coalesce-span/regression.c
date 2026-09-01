#include "allocator.h"

#include <stdio.h>
#include <stdlib.h>

int main(void) {
    void *state_storage = malloc(lf_state_size());
    unsigned char *arena = (unsigned char *)malloc(8192U);
    void *first;
    void *middle;
    void *last;
    if (state_storage == NULL || arena == NULL ||
        lf_init(state_storage, lf_state_size(), arena, 8192U) != LF_OK) {
        return 2;
    }
    first = lf_alloc(state_storage, 128U);
    middle = lf_alloc(state_storage, 256U);
    last = lf_alloc(state_storage, 128U);
    if (first == NULL || middle == NULL || last == NULL) {
        return 3;
    }
    if (lf_dealloc(state_storage, middle) != LF_OK ||
        lf_dealloc(state_storage, first) != LF_OK) {
        return 4;
    }
    if (lf_check(state_storage) != LF_OK) {
        fputs("detected allocator metadata corruption after adjacent coalescing\n", stderr);
        return 1;
    }
    if (lf_dealloc(state_storage, last) != LF_OK || lf_check(state_storage) != LF_OK) {
        return 5;
    }
    free(arena);
    free(state_storage);
    puts("adjacent coalescing retained the exact physical arena span");
    return 0;
}
