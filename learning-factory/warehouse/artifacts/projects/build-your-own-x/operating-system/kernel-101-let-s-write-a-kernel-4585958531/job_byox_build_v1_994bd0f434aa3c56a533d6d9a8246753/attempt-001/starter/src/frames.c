#include "tinykernel.h"

void tk_frames_init(tk_frame_allocator_t *allocator, uint16_t frame_count)
{
    (void)frame_count;
    if (allocator != NULL) {
        size_t i;
        for (i = 0; i < TK_MAX_FRAMES; ++i) {
            allocator->used[i] = 0u;
        }
        allocator->frame_count = 0u;
        allocator->free_count = 0u;
    }
    /* TODO(stage 1): establish the requested valid frame range. */
}

int tk_frame_alloc(tk_frame_allocator_t *allocator)
{
    (void)allocator;
    /* TODO(stage 1): claim and return the lowest free frame. */
    return -1;
}

int tk_frame_free(tk_frame_allocator_t *allocator, uint16_t frame)
{
    (void)allocator;
    (void)frame;
    /* TODO(stage 1): reject invalid and already-free frames. */
    return -1;
}

size_t tk_frame_available(const tk_frame_allocator_t *allocator)
{
    (void)allocator;
    /* TODO(stage 1): report free frames. */
    return 0u;
}
