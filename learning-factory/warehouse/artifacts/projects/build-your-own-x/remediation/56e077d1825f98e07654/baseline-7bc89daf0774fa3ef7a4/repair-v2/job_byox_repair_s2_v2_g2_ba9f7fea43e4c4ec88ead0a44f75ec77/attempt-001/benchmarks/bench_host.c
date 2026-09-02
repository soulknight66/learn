#define _POSIX_C_SOURCE 200809L

#include "kernel/ramfs.h"
#include "kernel/scheduler.h"
#include "kernel/vm.h"

#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <time.h>

#define ITERATIONS UINT32_C(100000)

static void no_op(void *argument) {
    (void)argument;
}

static uint64_t nanoseconds(struct timespec value) {
    return (uint64_t)value.tv_sec * UINT64_C(1000000000) +
           (uint64_t)value.tv_nsec;
}

int main(void) {
    struct timespec begin;
    struct timespec end;
    lf_scheduler_t scheduler;
    uint32_t iteration;
    uint32_t checksum = 0u;

    lf_scheduler_init(&scheduler);
    for (iteration = 0u; iteration < LF_MAX_TASKS; ++iteration) {
        if (lf_scheduler_spawn(&scheduler, no_op, (void *)0) == 0u) {
            return 2;
        }
    }
    if (clock_gettime(CLOCK_MONOTONIC, &begin) != 0) {
        return 3;
    }
    for (iteration = 0u; iteration < ITERATIONS; ++iteration) {
        checksum ^= lf_scheduler_rotate(&scheduler);
    }
    if (clock_gettime(CLOCK_MONOTONIC, &end) != 0) {
        return 4;
    }
    printf("iterations=%" PRIu32 " elapsed_ns=%" PRIu64
           " checksum=%" PRIu32 "\n",
           ITERATIONS, nanoseconds(end) - nanoseconds(begin), checksum);
    return lf_scheduler_invariant(&scheduler) ? 0 : 5;
}
