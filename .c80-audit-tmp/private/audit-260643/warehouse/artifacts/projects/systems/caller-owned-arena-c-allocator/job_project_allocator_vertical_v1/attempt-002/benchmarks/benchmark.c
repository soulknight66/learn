#define _POSIX_C_SOURCE 200809L
#include "allocator.h"

#include <stdint.h>
#include <stdio.h>
#include <stdalign.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define TIMED_OPERATIONS 80000U
#define SLOT_COUNT 256U
#define ARENA_BYTES 2097152U

static uint64_t nanoseconds(void) {
    struct timespec value;
    if (clock_gettime(CLOCK_MONOTONIC, &value) != 0) {
        return 0U;
    }
    return (uint64_t)value.tv_sec * UINT64_C(1000000000) + (uint64_t)value.tv_nsec;
}

int main(void) {
    void *state_storage = malloc(lf_state_size());
    unsigned char *arena = (unsigned char *)malloc(ARENA_BYTES);
    void *slots[SLOT_COUNT] = {0};
    size_t sizes[SLOT_COUNT] = {0};
    lf_allocator_stats stats;
    uint64_t start;
    uint64_t end;
    size_t operation;
    size_t successful_allocations = 0U;
    size_t failed_allocations = 0U;
    double external_fragmentation;

    if (state_storage == NULL || arena == NULL ||
        lf_init(state_storage, lf_state_size(), arena, ARENA_BYTES) != LF_OK) {
        return 2;
    }
    start = nanoseconds();
    for (operation = 0U; operation < TIMED_OPERATIONS; operation++) {
        size_t index = (operation * 73U + 19U) % SLOT_COUNT;
        if (slots[index] != NULL) {
            if (lf_dealloc(state_storage, slots[index]) != LF_OK) {
                return 3;
            }
            slots[index] = NULL;
        } else {
            size_t size = 8U + ((operation * 131U) % 2041U);
            slots[index] = lf_alloc(state_storage, size);
            sizes[index] = size;
            if (slots[index] != NULL) {
                unsigned char *bytes = (unsigned char *)slots[index];
                bytes[0] = (unsigned char)operation;
                bytes[size - 1U] = (unsigned char)(operation >> 8);
                successful_allocations++;
            } else {
                failed_allocations++;
            }
        }
    }
    end = nanoseconds();
    if (end <= start || lf_check(state_storage) != LF_OK) {
        return 4;
    }
    for (operation = 0U; operation < SLOT_COUNT; operation++) {
        if (slots[operation] != NULL) {
            unsigned char *bytes = (unsigned char *)slots[operation];
            (void)sizes[operation];
            bytes[0] ^= 0U;
            if (lf_dealloc(state_storage, slots[operation]) != LF_OK) {
                return 5;
            }
            slots[operation] = NULL;
        }
    }

    if (lf_init(state_storage, lf_state_size(), arena, ARENA_BYTES) != LF_OK) {
        return 6;
    }
    for (operation = 0U; operation < 900U; operation++) {
        size_t index = operation % SLOT_COUNT;
        size_t size = 24U + ((operation * 97U) % 3072U);
        if (slots[index] != NULL) {
            if (lf_dealloc(state_storage, slots[index]) != LF_OK) {
                return 7;
            }
        }
        slots[index] = lf_alloc(state_storage, size);
    }
    for (operation = 0U; operation < SLOT_COUNT; operation += 2U) {
        if (slots[operation] != NULL) {
            if (lf_dealloc(state_storage, slots[operation]) != LF_OK) {
                return 8;
            }
            slots[operation] = NULL;
        }
    }
    if (lf_get_stats(state_storage, &stats) != LF_OK || stats.free_bytes == 0U) {
        return 9;
    }
    external_fragmentation = 1.0 -
        ((double)stats.largest_free_block / (double)stats.free_bytes);
    printf("{\"architecture\":\"%s\",\"timed_operations\":%u,"
           "\"elapsed_ns\":%llu,\"operations_per_second\":%.3f,"
           "\"successful_allocations\":%zu,\"failed_allocations\":%zu,"
           "\"fragmentation_workload\":{\"block_count\":%zu,"
           "\"live_blocks\":%zu,\"live_bytes\":%zu,\"free_blocks\":%zu,"
           "\"free_bytes\":%zu,\"largest_free_block\":%zu,"
           "\"external_fragmentation_ratio\":%.9f}}\n",
           lf_architecture(), (unsigned int)TIMED_OPERATIONS,
           (unsigned long long)(end - start),
           (double)TIMED_OPERATIONS * 1000000000.0 / (double)(end - start),
           successful_allocations, failed_allocations, stats.block_count,
           stats.live_blocks, stats.live_bytes, stats.free_blocks,
           stats.free_bytes, stats.largest_free_block, external_fragmentation);
    free(arena);
    free(state_storage);
    return 0;
}
