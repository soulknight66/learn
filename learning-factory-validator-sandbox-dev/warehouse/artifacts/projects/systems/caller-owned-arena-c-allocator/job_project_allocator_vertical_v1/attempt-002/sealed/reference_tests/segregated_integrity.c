#include "allocator.h"

#include <stdio.h>
#include <stdalign.h>
#include <stdlib.h>

/* Deliberately white-box and sealed: exercise the alternative's second topology. */
#include "../alternatives/segregated_bins/allocator.c"

#define REQUIRE(condition, message) do { \
    if (!(condition)) { \
        fprintf(stderr, "segregated integrity: %s (line %d)\n", message, __LINE__); \
        return 1; \
    } \
} while (0)

int main(void) {
    void *state_storage;
    unsigned char *arena;
    state *allocator;
    block *initial;
    block *forged;
    void *payload;
    size_t index;

    state_storage = malloc(lf_state_size());
    arena = (unsigned char *)malloc(8192U);
    REQUIRE(state_storage != NULL && arena != NULL, "fixture storage allocation failed");
    REQUIRE(lf_init(state_storage, lf_state_size(), arena, 8192U) == LF_OK,
            "missing-node fixture initialization failed");
    allocator = (state *)state_storage;
    initial = allocator->head;
    index = bin_index(initial->size);
    allocator->bins[index] = NULL;
    REQUIRE(lf_check(state_storage) == LF_ERR_CORRUPT,
            "missing physical free block was accepted");

    REQUIRE(lf_init(state_storage, lf_state_size(), arena, 8192U) == LF_OK,
            "wrong-bin fixture initialization failed");
    allocator = (state *)state_storage;
    initial = allocator->head;
    index = bin_index(initial->size);
    allocator->bins[index] = NULL;
    allocator->bins[(index + 1U) % BIN_COUNT] = initial;
    REQUIRE(lf_check(state_storage) == LF_ERR_CORRUPT,
            "size-class mismatch was accepted");

    REQUIRE(lf_init(state_storage, lf_state_size(), arena, 8192U) == LF_OK,
            "duplicate-node fixture initialization failed");
    allocator = (state *)state_storage;
    initial = allocator->head;
    initial->free_next = initial;
    REQUIRE(lf_check(state_storage) == LF_ERR_CORRUPT,
            "duplicate/cyclic bin node was accepted");

    REQUIRE(lf_init(state_storage, lf_state_size(), arena, 8192U) == LF_OK,
            "extraneous-node fixture initialization failed");
    allocator = (state *)state_storage;
    payload = lf_alloc(state_storage, 256U);
    REQUIRE(payload != NULL, "extraneous-node fixture allocation failed");
    forged = (block *)payload;
    forged->size = LF_ALIGNMENT;
    forged->previous = NULL;
    forged->next = NULL;
    forged->free_previous = NULL;
    forged->free_next = NULL;
    forged->magic = LF_BLOCK_MAGIC;
    forged->is_free = 1U;
    allocator->bins[bin_index(forged->size)] = forged;
    REQUIRE(lf_check(state_storage) == LF_ERR_CORRUPT,
            "extraneous non-physical bin node was accepted");

    free(arena);
    free(state_storage);
    puts("segregated bins reject missing, inconsistent, duplicate, and extraneous nodes");
    return 0;
}
