#include "kernel/runtime.h"

#include <stdint.h>

static lf_runtime_t *active_runtime;

static void clear_context(lf_arm_context_t *context) {
    uint8_t *byte = (uint8_t *)context;
    size_t index;

    for (index = 0u; index < sizeof(*context); ++index) {
        byte[index] = 0u;
    }
}

static void task_bootstrap(void) __attribute__((noreturn));

static void task_bootstrap(void) {
    lf_runtime_t *runtime = active_runtime;
    int32_t slot = runtime->scheduler.current_slot;
    lf_task_entry_t entry = runtime->scheduler.tasks[(uint32_t)slot].entry;
    void *argument = runtime->scheduler.tasks[(uint32_t)slot].argument;

    entry(argument);
    lf_runtime_exit();
}

void lf_runtime_init(lf_runtime_t *runtime) {
    uint32_t slot;

    if (runtime == (lf_runtime_t *)0) {
        return;
    }
    lf_scheduler_init(&runtime->scheduler);
    clear_context(&runtime->boot_context);
    for (slot = 0u; slot < LF_MAX_TASKS; ++slot) {
        clear_context(&runtime->contexts[slot]);
    }
}

uint32_t lf_runtime_spawn(lf_runtime_t *runtime, lf_task_entry_t entry,
                          void *argument, void *stack, size_t stack_size) {
    uintptr_t bottom;
    uintptr_t top;
    uint32_t pid;
    int32_t slot;

    if (runtime == (lf_runtime_t *)0 || entry == (lf_task_entry_t)0 ||
        stack == (void *)0 || stack_size < 128u) {
        return 0u;
    }
    bottom = (uintptr_t)stack;
    if (bottom > UINTPTR_MAX - stack_size) {
        return 0u;
    }
    top = (bottom + stack_size) & ~(uintptr_t)7u;
    if (top <= bottom || top > UINT32_MAX) {
        return 0u;
    }

    pid = lf_scheduler_spawn(&runtime->scheduler, entry, argument);
    if (pid == 0u) {
        return 0u;
    }
    slot = lf_scheduler_slot_of(&runtime->scheduler, pid);
    clear_context(&runtime->contexts[(uint32_t)slot]);
    runtime->contexts[(uint32_t)slot].sp = (uint32_t)top;
    runtime->contexts[(uint32_t)slot].lr = (uint32_t)(uintptr_t)&task_bootstrap;
    return pid;
}

bool lf_runtime_start(lf_runtime_t *runtime) {
    uint32_t pid;
    int32_t slot;

    if (runtime == (lf_runtime_t *)0 || active_runtime != (lf_runtime_t *)0 ||
        runtime->scheduler.current_slot != LF_NO_SLOT) {
        return false;
    }
    pid = lf_scheduler_rotate(&runtime->scheduler);
    if (pid == 0u) {
        return false;
    }
    slot = lf_scheduler_slot_of(&runtime->scheduler, pid);
    active_runtime = runtime;
    lf_arch_context_switch(&runtime->boot_context,
                           &runtime->contexts[(uint32_t)slot]);
    active_runtime = (lf_runtime_t *)0;
    return true;
}

void lf_runtime_yield(void) {
    lf_runtime_t *runtime = active_runtime;
    int32_t old_slot;
    int32_t new_slot;
    uint32_t pid;

    if (runtime == (lf_runtime_t *)0 || runtime->scheduler.current_slot < 0) {
        return;
    }
    old_slot = runtime->scheduler.current_slot;
    pid = lf_scheduler_rotate(&runtime->scheduler);
    if (pid == 0u) {
        return;
    }
    new_slot = lf_scheduler_slot_of(&runtime->scheduler, pid);
    if (new_slot != old_slot) {
        lf_arch_context_switch(&runtime->contexts[(uint32_t)old_slot],
                               &runtime->contexts[(uint32_t)new_slot]);
    }
}

void lf_runtime_exit(void) {
    lf_runtime_t *runtime = active_runtime;
    int32_t old_slot;
    uint32_t pid;

    if (runtime == (lf_runtime_t *)0 || runtime->scheduler.current_slot < 0) {
        for (;;) {
            __asm__ volatile("" ::: "memory");
        }
    }
    old_slot = runtime->scheduler.current_slot;
    pid = lf_scheduler_exit_current(&runtime->scheduler);

    if (pid != 0u) {
        int32_t new_slot = lf_scheduler_slot_of(&runtime->scheduler, pid);
        lf_arch_context_switch(&runtime->contexts[(uint32_t)old_slot],
                               &runtime->contexts[(uint32_t)new_slot]);
    } else {
        lf_arch_context_switch(&runtime->contexts[(uint32_t)old_slot],
                               &runtime->boot_context);
    }
    for (;;) {
        __asm__ volatile("" ::: "memory");
    }
}
