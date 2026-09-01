#include "allocator.h"

#include <stdint.h>
#include <stdio.h>
#include <stdalign.h>
#include <stdlib.h>
#include <string.h>

#define REQUIRE(condition, message) do { \
    if (!(condition)) { \
        fprintf(stderr, "withheld contract: %s (line %d)\n", message, __LINE__); \
        return 1; \
    } \
} while (0)

int main(void) {
    void *state_storage;
    unsigned char *arena_storage;
    void *overlap_storage;
    lf_allocator_stats before;
    lf_allocator_stats after;
    unsigned char *a;
    unsigned char *b;
    unsigned char *c;
    unsigned char *grown;
    unsigned char outsider = 0U;
    size_t index;
    size_t state_bytes = lf_state_size();

    REQUIRE(state_bytes > 0U && state_bytes <= 512U, "state contract exceeds fixture");
    state_storage = malloc(state_bytes);
    arena_storage = (unsigned char *)malloc(65536U);
    overlap_storage = malloc(512U);
    REQUIRE(state_storage != NULL && arena_storage != NULL && overlap_storage != NULL,
            "fixture storage allocation failed");
    REQUIRE(lf_init(overlap_storage, state_bytes, overlap_storage, 512U) == LF_ERR_ARGUMENT,
            "overlapping state and arena storage was accepted");
    REQUIRE(lf_init(state_storage, state_bytes, arena_storage + 1, 65535U) == LF_OK,
            "unaligned arena base was not normalized");
    a = (unsigned char *)lf_alloc(state_storage, 113U);
    b = (unsigned char *)lf_alloc(state_storage, 257U);
    c = (unsigned char *)lf_alloc(state_storage, 521U);
    REQUIRE(a != NULL && b != NULL && c != NULL, "setup allocation failed");
    memset(b, 0x3c, 257U);
    REQUIRE(lf_dealloc(state_storage, c) == LF_OK, "tail free failed");
    grown = (unsigned char *)lf_resize(state_storage, b, 900U);
    REQUIRE(grown != NULL, "growth into or around a free neighbor failed");
    for (index = 0U; index < 257U; index++) {
        REQUIRE(grown[index] == 0x3cU, "resize did not preserve the old prefix");
    }
    REQUIRE(lf_resize(state_storage, grown, 80U) == grown, "shrink should stay in place");
    REQUIRE(lf_dealloc(state_storage, &outsider) == LF_ERR_INVALID_POINTER,
            "foreign pointer was accepted");
    REQUIRE(lf_get_stats(state_storage, &before) == LF_OK, "pre-failure stats failed");
    REQUIRE(lf_alloc(state_storage, SIZE_MAX) == NULL, "overflowing request was accepted");
    REQUIRE(lf_get_stats(state_storage, &after) == LF_OK, "post-failure stats failed");
    REQUIRE(before.block_count == after.block_count &&
            before.live_bytes == after.live_bytes && before.free_bytes == after.free_bytes,
            "failed allocation changed allocator state");
    REQUIRE(lf_dealloc(state_storage, a) == LF_OK, "a free failed");
    REQUIRE(lf_dealloc(state_storage, grown) == LF_OK, "grown free failed");
    REQUIRE(lf_dealloc(state_storage, grown) == LF_ERR_INVALID_POINTER,
            "stale pointer to a coalesced block was not safely rejected");
    REQUIRE(lf_check(state_storage) == LF_OK, "final invariant check failed");
    REQUIRE(lf_get_stats(state_storage, &after) == LF_OK &&
            after.live_blocks == 0U && after.free_blocks == 1U,
            "final arena did not coalesce");
    free(overlap_storage);
    free(arena_storage);
    free(state_storage);
    printf("withheld allocator contract passed for %s\n", lf_architecture());
    return 0;
}
