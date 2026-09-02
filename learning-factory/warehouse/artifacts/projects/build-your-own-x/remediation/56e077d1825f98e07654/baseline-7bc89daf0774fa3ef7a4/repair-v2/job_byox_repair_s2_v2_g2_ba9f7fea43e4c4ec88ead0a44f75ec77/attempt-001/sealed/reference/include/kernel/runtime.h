#ifndef LF_KERNEL_RUNTIME_H
#define LF_KERNEL_RUNTIME_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "kernel/scheduler.h"

typedef struct {
    uint32_t r4;
    uint32_t r5;
    uint32_t r6;
    uint32_t r7;
    uint32_t r8;
    uint32_t r9;
    uint32_t r10;
    uint32_t r11;
    uint32_t sp;
    uint32_t lr;
} lf_arm_context_t;

typedef struct {
    lf_scheduler_t scheduler;
    lf_arm_context_t contexts[LF_MAX_TASKS];
    uint32_t context_pids[LF_MAX_TASKS];
    lf_arm_context_t boot_context;
    lf_arm_context_t discard_context;
    int32_t executing_slot;
    uint32_t executing_pid;
} lf_runtime_t;

void lf_runtime_init(lf_runtime_t *runtime);
uint32_t lf_runtime_spawn(lf_runtime_t *runtime, lf_task_entry_t entry,
                          void *argument, void *stack, size_t stack_size);
bool lf_runtime_start(lf_runtime_t *runtime);
void lf_runtime_yield(void);
void lf_runtime_exit(void) __attribute__((noreturn));

void lf_arch_context_switch(lf_arm_context_t *old_context,
                            const lf_arm_context_t *new_context);

#endif
