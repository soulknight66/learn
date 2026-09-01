#include <stdint.h>
#include <stddef.h>

int64_t dispatch_add(int64_t *stack, size_t *depth) {
    int64_t right = stack[--*depth];
    int64_t left = stack[--*depth];
    return left + right;
}

int budget_allows(uint64_t *steps, uint64_t maximum) {
    (*steps)++;
    return *steps <= maximum;
}
