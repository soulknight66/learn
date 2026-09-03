#include <stdio.h>
#include <time.h>

#include "cairn.h"

#define ITERATIONS 1000000U

int main(void)
{
    struct cairn_kernel kernel;
    cairn_u32 physical = 0U;
    clock_t start;
    clock_t finish;
    unsigned int i;
    int pid;

    cairn_init(&kernel);
    if (cairn_spawn(&kernel, 0U, &pid) != CAIRN_OK ||
        cairn_map(&kernel, pid, 0x4000U, 3U, 1) != CAIRN_OK) {
        puts("benchmark setup failed");
        return 1;
    }
    start = clock();
    for (i = 0U; i < ITERATIONS; ++i) {
        if (cairn_translate(&kernel, pid, 0x4000U + (i & (CAIRN_PAGE_SIZE - 1U)),
                            (int)(i & 1U), &physical) != CAIRN_OK) {
            puts("benchmark operation failed");
            return 1;
        }
    }
    finish = clock();
    if (finish == (clock_t)-1 || start == (clock_t)-1) {
        puts("clock unavailable");
        return 2;
    }
    printf("translations=%u final_physical=%u elapsed_clock_ticks=%ld\n",
           ITERATIONS, physical, (long)(finish - start));
    return 0;
}
