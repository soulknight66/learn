    #include "allocator.h"

    #include <stdint.h>
    #include <stdalign.h>
    #include <string.h>

    #define LF_STATE_MAGIC UINT64_C(0x4c46414c4c4f4331)
    #define LF_BLOCK_MAGIC UINT32_C(0xb10ca110)

    typedef struct block block;
    struct block {
        size_t size;
        block *previous;
        block *next;
        uint32_t magic;
        unsigned char is_free;
    };

    typedef struct state {
        uint64_t magic;
        unsigned char *begin;
        unsigned char *end;
        block *head;
    } state;

    #define LF_ALIGNMENT ((size_t)alignof(max_align_t))
    #define HEADER_SIZE ((sizeof(block) + LF_ALIGNMENT - 1U) & ~(LF_ALIGNMENT - 1U))

    static size_t aligned_size(size_t value) {
        if (value == 0U || value > SIZE_MAX - (LF_ALIGNMENT - 1U)) {
            return 0U;
        }
        return (value + LF_ALIGNMENT - 1U) & ~(LF_ALIGNMENT - 1U);
    }

    static int state_is_plausible(const state *allocator) {
        return allocator != NULL && allocator->magic == LF_STATE_MAGIC &&
               allocator->begin != NULL && allocator->end > allocator->begin &&
               allocator->head == (block *)allocator->begin;
    }

    static block *find_pointer(state *allocator, void *pointer) {
        block *item;
        size_t guard = 0U;
        size_t limit;
        if (!state_is_plausible(allocator) || pointer == NULL) {
            return NULL;
        }
        limit = (size_t)(allocator->end - allocator->begin) / HEADER_SIZE + 1U;
        for (item = allocator->head; item != NULL && guard++ < limit; item = item->next) {
            if (item->magic != LF_BLOCK_MAGIC) {
                return NULL;
            }
            if ((void *)((unsigned char *)item + HEADER_SIZE) == pointer) {
                return item;
            }
        }
        return NULL;
    }

    static void merge_next(block *item) {
        block *next = item->next;
        item->size += HEADER_SIZE + next->size;
        item->next = next->next;
        if (item->next != NULL) {
            item->next->previous = item;
        }
    }

    static block *split_block(block *item, size_t need) {
        block *remainder;
        if (item->size < need + HEADER_SIZE + LF_ALIGNMENT) {
            return NULL;
        }
        remainder = (block *)((unsigned char *)item + HEADER_SIZE + need);
        remainder->size = item->size - need - HEADER_SIZE;
        remainder->previous = item;
        remainder->next = item->next;
        remainder->magic = LF_BLOCK_MAGIC;
        remainder->is_free = 1U;
        if (remainder->next != NULL) {
            remainder->next->previous = remainder;
        }
        item->next = remainder;
        item->size = need;
        return remainder;
    }

    static block *select_block(state *allocator, size_t need) {

block *item;
block *best = NULL;
for (item = allocator->head; item != NULL; item = item->next) {
    if (item->magic != LF_BLOCK_MAGIC) {
        return NULL;
    }
    if (item->is_free != 0U && item->size >= need &&
        (best == NULL || item->size < best->size)) {
        best = item;
    }
}
return best;
    }

    size_t lf_state_size(void) {
        return sizeof(state);
    }

    const char *lf_architecture(void) {
        return "address-ordered-best-fit";
    }

    int lf_init(void *state_storage, size_t state_bytes, void *arena, size_t arena_bytes) {
        uintptr_t raw;
        uintptr_t aligned;
        uintptr_t state_raw;
        uintptr_t state_end;
        uintptr_t arena_end;
        size_t prefix;
        size_t usable;
        state *allocator;
        block *initial;
        if (state_storage == NULL || arena == NULL || state_bytes < sizeof(state) ||
            ((uintptr_t)state_storage % LF_ALIGNMENT) != 0U) {
            return LF_ERR_ARGUMENT;
        }
        raw = (uintptr_t)arena;
        state_raw = (uintptr_t)state_storage;
        if (raw > UINTPTR_MAX - (LF_ALIGNMENT - 1U) ||
            state_raw > UINTPTR_MAX - sizeof(state) ||
            arena_bytes > UINTPTR_MAX - raw) {
            return LF_ERR_ARGUMENT;
        }
        state_end = state_raw + sizeof(state);
        arena_end = raw + arena_bytes;
        if (state_raw < arena_end && raw < state_end) {
            return LF_ERR_ARGUMENT;
        }
        aligned = (raw + LF_ALIGNMENT - 1U) & ~(uintptr_t)(LF_ALIGNMENT - 1U);
        prefix = (size_t)(aligned - raw);
        if (arena_bytes <= prefix) {
            return LF_ERR_ARENA_TOO_SMALL;
        }
        usable = (arena_bytes - prefix) & ~(LF_ALIGNMENT - 1U);
        if (usable < HEADER_SIZE + LF_ALIGNMENT) {
            return LF_ERR_ARENA_TOO_SMALL;
        }
        memset(state_storage, 0, sizeof(state));
        allocator = (state *)state_storage;
        allocator->magic = LF_STATE_MAGIC;
        allocator->begin = (unsigned char *)aligned;
        allocator->end = allocator->begin + usable;
        allocator->head = (block *)allocator->begin;
        initial = allocator->head;
        initial->size = usable - HEADER_SIZE;
        initial->previous = NULL;
        initial->next = NULL;
        initial->magic = LF_BLOCK_MAGIC;
        initial->is_free = 1U;
        return LF_OK;
    }

    void *lf_alloc(void *state_storage, size_t bytes) {
        state *allocator = (state *)state_storage;
        size_t need = aligned_size(bytes);
        block *selected;
        if (need == 0U || !state_is_plausible(allocator)) {
            return NULL;
        }
        selected = select_block(allocator, need);
        if (selected == NULL) {
            return NULL;
        }
        (void)split_block(selected, need);
        selected->is_free = 0U;
        return (unsigned char *)selected + HEADER_SIZE;
    }

    int lf_dealloc(void *state_storage, void *pointer) {
        state *allocator = (state *)state_storage;
        block *item;
        if (pointer == NULL) {
            return LF_OK;
        }
        if (!state_is_plausible(allocator)) {
            return LF_ERR_ARGUMENT;
        }
        item = find_pointer(allocator, pointer);
        if (item == NULL) {
            return LF_ERR_INVALID_POINTER;
        }
        if (item->is_free != 0U) {
            return LF_ERR_DOUBLE_FREE;
        }
        item->is_free = 1U;
        if (item->next != NULL && item->next->is_free != 0U) {
            merge_next(item);
        }
        if (item->previous != NULL && item->previous->is_free != 0U) {
            item = item->previous;
            merge_next(item);
        }
        return LF_OK;
    }

    void *lf_resize(void *state_storage, void *pointer, size_t bytes) {
        state *allocator = (state *)state_storage;
        block *item;
        block *remainder;
        size_t need;
        void *replacement;
        if (pointer == NULL) {
            return lf_alloc(state_storage, bytes);
        }
        item = find_pointer(allocator, pointer);
        if (item == NULL || item->is_free != 0U) {
            return NULL;
        }
        if (bytes == 0U) {
            (void)lf_dealloc(state_storage, pointer);
            return NULL;
        }
        need = aligned_size(bytes);
        if (need == 0U) {
            return NULL;
        }
        if (need <= item->size) {
            remainder = split_block(item, need);
            if (remainder != NULL && remainder->next != NULL &&
                remainder->next->is_free != 0U) {
                merge_next(remainder);
            }
            return pointer;
        }
        if (item->next != NULL && item->next->is_free != 0U &&
            item->size + HEADER_SIZE + item->next->size >= need) {
            merge_next(item);
            (void)split_block(item, need);
            item->is_free = 0U;
            return pointer;
        }
        replacement = lf_alloc(state_storage, bytes);
        if (replacement == NULL) {
            return NULL;
        }
        memcpy(replacement, pointer, item->size < bytes ? item->size : bytes);
        (void)lf_dealloc(state_storage, pointer);
        return replacement;
    }

    int lf_check(const void *state_storage) {
        const state *allocator = (const state *)state_storage;
        const block *item;
        const block *previous = NULL;
        const unsigned char *expected;
        size_t guard = 0U;
        size_t limit;
        if (!state_is_plausible(allocator)) {
            return LF_ERR_CORRUPT;
        }
        expected = allocator->begin;
        limit = (size_t)(allocator->end - allocator->begin) / HEADER_SIZE + 1U;
        for (item = allocator->head; item != NULL; item = item->next) {
            const unsigned char *after;
            size_t remaining;
            if (++guard > limit || (const unsigned char *)item != expected) {
                return LF_ERR_CORRUPT;
            }
            remaining = (size_t)(allocator->end - expected);
            if (remaining < HEADER_SIZE || item->magic != LF_BLOCK_MAGIC ||
                item->previous != previous || item->size == 0U ||
                (item->size % LF_ALIGNMENT) != 0U ||
                item->size > remaining - HEADER_SIZE ||
                (previous != NULL && previous->is_free != 0U && item->is_free != 0U)) {
                return LF_ERR_CORRUPT;
            }
            after = expected + HEADER_SIZE + item->size;
            if (after > allocator->end ||
                (after == allocator->end && item->next != NULL) ||
                (after != allocator->end &&
                 (const unsigned char *)item->next != after)) {
                return LF_ERR_CORRUPT;
            }
            expected = after;
            previous = item;
        }
        return LF_OK;
    }

    int lf_get_stats(const void *state_storage, lf_allocator_stats *output) {
        const state *allocator = (const state *)state_storage;
        const block *item;
        if (output == NULL || lf_check(state_storage) != LF_OK) {
            return LF_ERR_CORRUPT;
        }
        memset(output, 0, sizeof(*output));
        output->arena_bytes = (size_t)(allocator->end - allocator->begin);
        for (item = allocator->head; item != NULL; item = item->next) {
            output->block_count++;
            if (item->is_free != 0U) {
                output->free_blocks++;
                output->free_bytes += item->size;
                if (item->size > output->largest_free_block) {
                    output->largest_free_block = item->size;
                }
            } else {
                output->live_blocks++;
                output->live_bytes += item->size;
            }
        }
        return LF_OK;
    }
