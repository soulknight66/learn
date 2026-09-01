#include "allocator.h"

#include <stdint.h>
#include <stdio.h>
#include <stdalign.h>
#include <stdlib.h>
#include <string.h>

#define SLOT_COUNT 96U
#define ITERATIONS 4000U
#define ARENA_BYTES 32768U

typedef struct slot {
    unsigned char *pointer;
    size_t size;
    unsigned char tag;
} slot;

static uint32_t next_random(uint32_t *state) {
    uint32_t value = *state;
    value ^= value << 13;
    value ^= value >> 17;
    value ^= value << 5;
    *state = value;
    return value;
}

static int verify_slot(const slot *item) {
    size_t index;
    if (item->pointer == NULL) {
        return 1;
    }
    for (index = 0U; index < item->size; index++) {
        if (item->pointer[index] != item->tag) {
            return 0;
        }
    }
    return 1;
}

int main(void) {
    void *state_storage = malloc(lf_state_size());
    unsigned char *arena = (unsigned char *)malloc(ARENA_BYTES);
    slot slots[SLOT_COUNT] = {{0}};
    uint32_t random_state = UINT32_C(0x20260830);
    size_t operation;
    size_t completed = 0U;
    size_t allocation_failures = 0U;
    size_t resize_failures = 0U;

    if (state_storage == NULL || arena == NULL ||
        lf_init(state_storage, lf_state_size(), arena, ARENA_BYTES) != LF_OK) {
        fputs("model: initialization failed\n", stderr);
        return 1;
    }
    for (operation = 0U; operation < ITERATIONS; operation++) {
        size_t index = (size_t)(next_random(&random_state) % SLOT_COUNT);
        uint32_t choice = next_random(&random_state) % 100U;
        slot *item = &slots[index];
        size_t check_index;
        for (check_index = 0U; check_index < SLOT_COUNT; check_index++) {
            if (!verify_slot(&slots[check_index])) {
                fprintf(stderr, "model: payload corruption in slot %zu at operation %zu\n",
                        check_index, operation);
                return 1;
            }
        }
        if (item->pointer == NULL && choice < 62U) {
            size_t size = 1U + (size_t)(next_random(&random_state) % 1536U);
            unsigned char *pointer = (unsigned char *)lf_alloc(state_storage, size);
            if (pointer == NULL) {
                allocation_failures++;
            } else {
                uintptr_t address = (uintptr_t)pointer;
                uintptr_t arena_begin = (uintptr_t)arena;
                uintptr_t arena_end = arena_begin + ARENA_BYTES;
                if ((address % alignof(max_align_t)) != 0U || address < arena_begin ||
                    address > arena_end || size > (size_t)(arena_end - address)) {
                    fputs("model: allocation pointer violates alignment or arena bounds\n", stderr);
                    return 1;
                }
                item->pointer = pointer;
                item->size = size;
                item->tag = (unsigned char)(1U + (next_random(&random_state) % 254U));
                memset(item->pointer, item->tag, item->size);
                completed++;
            }
        } else if (item->pointer != NULL && choice < 35U) {
            if (lf_dealloc(state_storage, item->pointer) != LF_OK) {
                fputs("model: valid free rejected\n", stderr);
                return 1;
            }
            memset(item, 0, sizeof(*item));
            completed++;
        } else if (item->pointer != NULL && choice < 75U) {
            size_t new_size = 1U + (size_t)(next_random(&random_state) % 2048U);
            size_t preserved = item->size < new_size ? item->size : new_size;
            unsigned char *replacement =
                (unsigned char *)lf_resize(state_storage, item->pointer, new_size);
            if (replacement == NULL) {
                if (!verify_slot(item)) {
                    fputs("model: failed resize modified original allocation\n", stderr);
                    return 1;
                }
                allocation_failures++;
                resize_failures++;
            } else {
                size_t byte;
                uintptr_t address = (uintptr_t)replacement;
                uintptr_t arena_begin = (uintptr_t)arena;
                uintptr_t arena_end = arena_begin + ARENA_BYTES;
                if ((address % alignof(max_align_t)) != 0U || address < arena_begin ||
                    address > arena_end || new_size > (size_t)(arena_end - address)) {
                    fputs("model: resized pointer violates alignment or arena bounds\n", stderr);
                    return 1;
                }
                for (byte = 0U; byte < preserved; byte++) {
                    if (replacement[byte] != item->tag) {
                        fputs("model: resize prefix mismatch\n", stderr);
                        return 1;
                    }
                }
                item->pointer = replacement;
                item->size = new_size;
                memset(item->pointer, item->tag, item->size);
                completed++;
            }
        }
        if (lf_check(state_storage) != LF_OK) {
            fprintf(stderr, "model: invariant failure at operation %zu\n", operation);
            return 1;
        }
    }
    for (operation = 0U; operation < SLOT_COUNT; operation++) {
        if (!verify_slot(&slots[operation])) {
            fputs("model: final payload mismatch\n", stderr);
            return 1;
        }
        if (slots[operation].pointer != NULL &&
            lf_dealloc(state_storage, slots[operation].pointer) != LF_OK) {
            fputs("model: cleanup free failed\n", stderr);
            return 1;
        }
    }
    if (lf_check(state_storage) != LF_OK) {
        fputs("model: final invariant failure\n", stderr);
        return 1;
    }
    if (resize_failures == 0U) {
        fputs("model: fixture did not exercise resize failure atomicity\n", stderr);
        return 1;
    }
    printf("deterministic model passed architecture=%s seed=0x20260830 "
           "iterations=%u completed=%zu allocation_failures=%zu resize_failures=%zu\n",
           lf_architecture(), (unsigned int)ITERATIONS, completed, allocation_failures,
           resize_failures);
    free(arena);
    free(state_storage);
    return 0;
}
