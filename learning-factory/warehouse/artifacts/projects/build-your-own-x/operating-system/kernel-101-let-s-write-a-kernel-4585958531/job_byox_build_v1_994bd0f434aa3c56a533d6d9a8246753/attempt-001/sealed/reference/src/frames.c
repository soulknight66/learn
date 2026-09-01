#include "tinykernel.h"

void tk_frames_init(tk_frame_allocator_t *allocator, uint16_t frame_count)
{
    size_t index;

    if (allocator == NULL) {
        return;
    }
    for (index = 0; index < TK_MAX_FRAMES; ++index) {
        allocator->used[index] = 0u;
    }
    if (frame_count == 0u || frame_count > TK_MAX_FRAMES) {
        allocator->frame_count = 0u;
        allocator->free_count = 0u;
        return;
    }
    allocator->frame_count = frame_count;
    allocator->free_count = frame_count;
}

int tk_frame_alloc(tk_frame_allocator_t *allocator)
{
    uint16_t frame;

    if (allocator == NULL || allocator->free_count == 0u) {
        return -1;
    }
    for (frame = 0u; frame < allocator->frame_count; ++frame) {
        if (allocator->used[frame] == 0u) {
            allocator->used[frame] = 1u;
            --allocator->free_count;
            return (int)frame;
        }
    }
    return -1;
}

int tk_frame_free(tk_frame_allocator_t *allocator, uint16_t frame)
{
    if (allocator == NULL || frame >= allocator->frame_count ||
        allocator->used[frame] == 0u) {
        return -1;
    }
    allocator->used[frame] = 0u;
    ++allocator->free_count;
    return 0;
}

size_t tk_frame_available(const tk_frame_allocator_t *allocator)
{
    if (allocator == NULL) {
        return 0u;
    }
    return allocator->free_count;
}
