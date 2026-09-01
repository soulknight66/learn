#ifndef LEARNING_FACTORY_ALLOCATOR_H
#define LEARNING_FACTORY_ALLOCATOR_H

#include <stddef.h>

enum {
    LF_OK = 0,
    LF_ERR_ARGUMENT = 1,
    LF_ERR_ARENA_TOO_SMALL = 2,
    LF_ERR_INVALID_POINTER = 3,
    LF_ERR_DOUBLE_FREE = 4,
    LF_ERR_CORRUPT = 5
};

typedef struct lf_allocator_stats {
    size_t arena_bytes;
    size_t block_count;
    size_t live_blocks;
    size_t live_bytes;
    size_t free_blocks;
    size_t free_bytes;
    size_t largest_free_block;
} lf_allocator_stats;

size_t lf_state_size(void);
const char *lf_architecture(void);
/*
 * Portable C11 storage contract: state_storage and arena designate disjoint
 * regions returned by malloc/aligned_alloc (or equivalent storage with no
 * incompatible declared object type).  state_storage is max_align_t-aligned.
 * A casted, declared unsigned char array is outside this portable contract:
 * alignment alone does not change its effective type.
 */
int lf_init(void *state_storage, size_t state_bytes, void *arena, size_t arena_bytes);
void *lf_alloc(void *state_storage, size_t bytes);
/*
 * LF_ERR_DOUBLE_FREE is returned while the freed block is still represented
 * in the physical list.  Coalescing removes interior block identities, so a
 * later stale pointer to a coalesced block is rejected as
 * LF_ERR_INVALID_POINTER rather than being accepted or dereferenced.
 */
int lf_dealloc(void *state_storage, void *pointer);
void *lf_resize(void *state_storage, void *pointer, size_t bytes);
int lf_check(const void *state_storage);
int lf_get_stats(const void *state_storage, lf_allocator_stats *output);

#endif
