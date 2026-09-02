#include "kernel/runtime.h"

/* Stage 2 (ARM half): construct initial contexts and connect scheduler
 * transitions to lf_arch_context_switch. */
void lf_runtime_init(lf_runtime_t *runtime) {
    if (runtime != (lf_runtime_t *)0) {
        lf_scheduler_init(&runtime->scheduler);
    }
}

uint32_t lf_runtime_spawn(lf_runtime_t *runtime, lf_task_entry_t entry,
                          void *argument, void *stack, size_t stack_size) {
    (void)runtime;
    (void)entry;
    (void)argument;
    (void)stack;
    (void)stack_size;
    return 0u;
}

bool lf_runtime_start(lf_runtime_t *runtime) {
    (void)runtime;
    return false;
}

void lf_runtime_yield(void) {
}

void lf_runtime_exit(void) {
    for (;;) {
        __asm__ volatile("" ::: "memory");
    }
}
