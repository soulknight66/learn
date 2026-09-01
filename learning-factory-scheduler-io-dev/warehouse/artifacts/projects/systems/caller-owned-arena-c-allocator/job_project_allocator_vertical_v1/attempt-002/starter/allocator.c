#include "allocator.h"

size_t lf_state_size(void) {
    /* Decide what durable allocator state belongs outside the managed arena. */
    return 0U;
}

const char *lf_architecture(void) {
    return "learner-design-not-implemented";
}

int lf_init(void *state_storage, size_t state_bytes, void *arena, size_t arena_bytes) {
    (void)state_storage;
    (void)state_bytes;
    (void)arena;
    (void)arena_bytes;
    return LF_ERR_ARGUMENT;
}

void *lf_alloc(void *state_storage, size_t bytes) {
    (void)state_storage;
    (void)bytes;
    return NULL;
}

int lf_dealloc(void *state_storage, void *pointer) {
    (void)state_storage;
    (void)pointer;
    return LF_ERR_ARGUMENT;
}

void *lf_resize(void *state_storage, void *pointer, size_t bytes) {
    (void)state_storage;
    (void)pointer;
    (void)bytes;
    return NULL;
}

int lf_check(const void *state_storage) {
    (void)state_storage;
    return LF_ERR_CORRUPT;
}

int lf_get_stats(const void *state_storage, lf_allocator_stats *output) {
    (void)state_storage;
    (void)output;
    return LF_ERR_CORRUPT;
}
