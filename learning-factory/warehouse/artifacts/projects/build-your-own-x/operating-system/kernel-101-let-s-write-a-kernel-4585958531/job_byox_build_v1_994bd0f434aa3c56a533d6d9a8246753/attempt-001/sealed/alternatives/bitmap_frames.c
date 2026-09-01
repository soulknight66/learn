#include <stddef.h>
#include <stdint.h>

#define ALT_FRAME_LIMIT 128u

typedef struct {
    uint8_t bits[ALT_FRAME_LIMIT / 8u];
    uint16_t count;
    uint16_t free_count;
} alt_bitmap_frames_t;

void alt_bitmap_init(alt_bitmap_frames_t *pool, uint16_t count)
{
    size_t index;

    if (pool == NULL) {
        return;
    }
    for (index = 0; index < sizeof(pool->bits); ++index) {
        pool->bits[index] = 0u;
    }
    if (count == 0u || count > ALT_FRAME_LIMIT) {
        pool->count = 0u;
        pool->free_count = 0u;
    } else {
        pool->count = count;
        pool->free_count = count;
    }
}

int alt_bitmap_alloc(alt_bitmap_frames_t *pool)
{
    uint16_t frame;

    if (pool == NULL || pool->free_count == 0u) {
        return -1;
    }
    for (frame = 0u; frame < pool->count; ++frame) {
        uint8_t mask = (uint8_t)(1u << (frame % 8u));
        if ((pool->bits[frame / 8u] & mask) == 0u) {
            pool->bits[frame / 8u] |= mask;
            --pool->free_count;
            return (int)frame;
        }
    }
    return -1;
}

int alt_bitmap_free(alt_bitmap_frames_t *pool, uint16_t frame)
{
    uint8_t mask;

    if (pool == NULL || frame >= pool->count) {
        return -1;
    }
    mask = (uint8_t)(1u << (frame % 8u));
    if ((pool->bits[frame / 8u] & mask) == 0u) {
        return -1;
    }
    pool->bits[frame / 8u] &= (uint8_t)~mask;
    ++pool->free_count;
    return 0;
}
