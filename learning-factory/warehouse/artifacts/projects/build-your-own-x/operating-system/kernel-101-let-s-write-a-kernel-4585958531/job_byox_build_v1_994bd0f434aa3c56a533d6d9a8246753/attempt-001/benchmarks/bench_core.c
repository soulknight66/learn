#include "tinykernel.h"

#include <stdio.h>
#include <time.h>

#define ITERATIONS 100000u

int main(void)
{
    tk_frame_allocator_t frames;
    tk_fs_t fs;
    static const uint8_t payload[] = {1u, 2u, 3u, 4u};
    uint8_t output[sizeof(payload)];
    unsigned long completed = 0ul;
    unsigned int iteration;
    clock_t start;
    clock_t finish;

    tk_frames_init(&frames, TK_MAX_FRAMES);
    start = clock();
    for (iteration = 0u; iteration < ITERATIONS; ++iteration) {
        int frame = tk_frame_alloc(&frames);
        if (frame < 0 || tk_frame_free(&frames, (uint16_t)frame) != 0) {
            break;
        }
        ++completed;
    }
    finish = clock();
    printf("frame cycles: %lu; clock ticks: %ld\n", completed,
           (long)(finish - start));

    tk_fs_init(&fs);
    if (tk_fs_create(&fs, "bench") != 0) {
        return 1;
    }
    completed = 0ul;
    start = clock();
    for (iteration = 0u; iteration < ITERATIONS; ++iteration) {
        if (tk_fs_write(&fs, "bench", payload, sizeof(payload)) != 0 ||
            tk_fs_read(&fs, "bench", output, sizeof(output)) != (int)sizeof(payload)) {
            break;
        }
        ++completed;
    }
    finish = clock();
    printf("filesystem cycles: %lu; clock ticks: %ld\n", completed,
           (long)(finish - start));
    return completed == ITERATIONS ? 0 : 1;
}
