#include "allocator.h"

#include <stdint.h>
#include <stdio.h>
#include <stdalign.h>
#include <stdlib.h>
#include <string.h>

#define REQUIRE(condition, message) do { \
    if (!(condition)) { \
        fprintf(stderr, "public contract: %s (line %d)\n", message, __LINE__); \
        return 1; \
    } \
} while (0)

int main(void) {
    void *state_storage;
    unsigned char *arena;
    lf_allocator_stats stats;
    unsigned char *first;
    unsigned char *second;
    size_t index;
    size_t state_bytes = lf_state_size();

    REQUIRE(state_bytes > 0U && state_bytes <= 512U, "state contract exceeds fixture");
    state_storage = malloc(state_bytes);
    arena = (unsigned char *)malloc(32768U);
    REQUIRE(state_storage != NULL && arena != NULL, "fixture storage allocation failed");
    REQUIRE(lf_init(state_storage, state_bytes, arena, 32768U) == LF_OK,
            "initialization failed");
    REQUIRE(lf_alloc(state_storage, 0U) == NULL, "zero-size allocation must be NULL");
    first = (unsigned char *)lf_alloc(state_storage, 37U);
    second = (unsigned char *)lf_alloc(state_storage, 200U);
    REQUIRE(first != NULL && second != NULL && first != second, "distinct allocations failed");
    REQUIRE(((uintptr_t)first % alignof(max_align_t)) == 0U, "first pointer is misaligned");
    REQUIRE(((uintptr_t)second % alignof(max_align_t)) == 0U, "second pointer is misaligned");
    memset(first, 0xa5, 37U);
    memset(second, 0x5a, 200U);
    for (index = 0U; index < 37U; index++) {
        REQUIRE(first[index] == 0xa5U, "first allocation changed unexpectedly");
    }
    REQUIRE(lf_check(state_storage) == LF_OK, "invariants failed after allocation");
    REQUIRE(lf_dealloc(state_storage, first) == LF_OK, "free failed");
    REQUIRE(lf_dealloc(state_storage, first) == LF_ERR_DOUBLE_FREE,
            "double free was not rejected");
    REQUIRE(lf_dealloc(state_storage, second) == LF_OK, "second free failed");
    REQUIRE(lf_get_stats(state_storage, &stats) == LF_OK, "stats failed");
    REQUIRE(stats.live_blocks == 0U && stats.free_blocks == 1U,
            "adjacent free blocks were not fully coalesced");
    free(arena);
    free(state_storage);
    puts("public allocator contract passed");
    return 0;
}
