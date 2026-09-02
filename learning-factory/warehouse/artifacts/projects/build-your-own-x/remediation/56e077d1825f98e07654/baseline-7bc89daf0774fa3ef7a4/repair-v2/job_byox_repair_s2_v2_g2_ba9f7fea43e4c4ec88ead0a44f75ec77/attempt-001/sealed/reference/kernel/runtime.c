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
static void runtime_exit_identity(lf_runtime_t *runtime, int32_t slot,
                                  uint32_t pid) __attribute__((noreturn));

static bool valid_slot(int32_t slot) {
    return slot >= 0 && slot < (int32_t)LF_MAX_TASKS;
}

static bool scheduler_has_identity(const lf_runtime_t *runtime, int32_t slot,
                                   uint32_t pid) {
    return runtime != (const lf_runtime_t *)0 && valid_slot(slot) && pid != 0u &&
           runtime->scheduler.tasks[(uint32_t)slot].state != LF_TASK_UNUSED &&
           runtime->scheduler.tasks[(uint32_t)slot].pid == pid;
}

static bool context_has_identity(const lf_runtime_t *runtime, int32_t slot,
                                 uint32_t pid) {
    return scheduler_has_identity(runtime, slot, pid) &&
           runtime->context_pids[(uint32_t)slot] == pid;
}

static bool execution_is_logical_current(const lf_runtime_t *runtime,
                                         int32_t slot, uint32_t pid) {
    return context_has_identity(runtime, slot, pid) &&
           runtime->scheduler.current_slot == slot &&
           runtime->scheduler.tasks[(uint32_t)slot].state == LF_TASK_RUNNING;
}

static lf_arm_context_t *save_context_for(lf_runtime_t *runtime, int32_t slot,
                                          uint32_t pid) {
    if (context_has_identity(runtime, slot, pid)) {
        return &runtime->contexts[(uint32_t)slot];
    }
    return &runtime->discard_context;
}

/*
 * Reconcile a physical ARM frame with scheduler state that may already have
 * moved on.  A stale frame is saved only when its PID still owns the context;
 * after slot reuse it is saved to discard_context.  An already-selected task
 * is dispatched without rotating it away.
 */
static void dispatch_logical_current(lf_runtime_t *runtime,
                                     int32_t physical_slot,
                                     uint32_t physical_pid) {
    lf_arm_context_t *old_context;
    int32_t selected_slot;
    uint32_t selected_pid;

    if (!lf_scheduler_invariant(&runtime->scheduler)) {
        return;
    }

    selected_slot = runtime->scheduler.current_slot;
    if (selected_slot == LF_NO_SLOT) {
        selected_pid = lf_scheduler_rotate(&runtime->scheduler);
        if (selected_pid != 0u) {
            selected_slot = lf_scheduler_slot_of(&runtime->scheduler,
                                                 selected_pid);
        }
    } else {
        selected_pid = runtime->scheduler.tasks[(uint32_t)selected_slot].pid;
    }

    if (selected_pid != 0u && selected_slot == physical_slot &&
        selected_pid == physical_pid) {
        runtime->executing_slot = physical_slot;
        runtime->executing_pid = physical_pid;
        return;
    }

    old_context = save_context_for(runtime, physical_slot, physical_pid);
    if (selected_pid != 0u && valid_slot(selected_slot) &&
        runtime->context_pids[(uint32_t)selected_slot] == selected_pid) {
        runtime->executing_slot = selected_slot;
        runtime->executing_pid = selected_pid;
        lf_arch_context_switch(old_context,
                               &runtime->contexts[(uint32_t)selected_slot]);
    } else {
        runtime->executing_slot = LF_NO_SLOT;
        runtime->executing_pid = 0u;
        lf_arch_context_switch(old_context, &runtime->boot_context);
    }

    /* This frame was selected again after its saved context resumed. */
    runtime->executing_slot = physical_slot;
    runtime->executing_pid = physical_pid;
}

static void task_bootstrap(void) {
    lf_runtime_t *runtime = active_runtime;
    int32_t slot;
    uint32_t pid;
    lf_task_entry_t entry;
    void *argument;

    if (runtime == (lf_runtime_t *)0) {
        for (;;) {
            __asm__ volatile("" ::: "memory");
        }
    }
    slot = runtime->executing_slot;
    pid = runtime->executing_pid;
    if (!execution_is_logical_current(runtime, slot, pid)) {
        runtime_exit_identity(runtime, slot, pid);
    }
    entry = runtime->scheduler.tasks[(uint32_t)slot].entry;
    argument = runtime->scheduler.tasks[(uint32_t)slot].argument;

    entry(argument);
    runtime_exit_identity(runtime, slot, pid);
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
        runtime->context_pids[slot] = 0u;
    }
    clear_context(&runtime->discard_context);
    runtime->executing_slot = LF_NO_SLOT;
    runtime->executing_pid = 0u;
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
    if (!valid_slot(slot)) {
        return 0u;
    }
    runtime->context_pids[(uint32_t)slot] = 0u;
    clear_context(&runtime->contexts[(uint32_t)slot]);
    runtime->contexts[(uint32_t)slot].sp = (uint32_t)top;
    runtime->contexts[(uint32_t)slot].lr = (uint32_t)(uintptr_t)&task_bootstrap;
    runtime->context_pids[(uint32_t)slot] = pid;
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
    if (!valid_slot(slot) || runtime->context_pids[(uint32_t)slot] != pid) {
        return false;
    }
    active_runtime = runtime;
    runtime->executing_slot = slot;
    runtime->executing_pid = pid;
    lf_arch_context_switch(&runtime->boot_context,
                           &runtime->contexts[(uint32_t)slot]);
    runtime->executing_slot = LF_NO_SLOT;
    runtime->executing_pid = 0u;
    active_runtime = (lf_runtime_t *)0;
    return true;
}

void lf_runtime_yield(void) {
    lf_runtime_t *runtime = active_runtime;
    int32_t physical_slot;
    uint32_t physical_pid;

    if (runtime == (lf_runtime_t *)0) {
        return;
    }
    physical_slot = runtime->executing_slot;
    physical_pid = runtime->executing_pid;
    if (!valid_slot(physical_slot) || physical_pid == 0u ||
        !lf_scheduler_invariant(&runtime->scheduler)) {
        return;
    }

    if (execution_is_logical_current(runtime, physical_slot, physical_pid)) {
        (void)lf_scheduler_rotate(&runtime->scheduler);
    }
    dispatch_logical_current(runtime, physical_slot, physical_pid);
}

static void runtime_exit_identity(lf_runtime_t *runtime, int32_t physical_slot,
                                  uint32_t physical_pid) {
    if (runtime != (lf_runtime_t *)0 && valid_slot(physical_slot) &&
        physical_pid != 0u && lf_scheduler_invariant(&runtime->scheduler)) {
        if (execution_is_logical_current(runtime, physical_slot, physical_pid)) {
            (void)lf_scheduler_exit_current(&runtime->scheduler);
        } else if (scheduler_has_identity(runtime, physical_slot,
                                          physical_pid)) {
            lf_task_t *physical_task =
                &runtime->scheduler.tasks[(uint32_t)physical_slot];

            if (physical_task->state == LF_TASK_READY ||
                physical_task->state == LF_TASK_BLOCKED) {
                physical_task->state = LF_TASK_ZOMBIE;
            }
        }
        dispatch_logical_current(runtime, physical_slot, physical_pid);
    }

    for (;;) {
        __asm__ volatile("" ::: "memory");
    }
}

void lf_runtime_exit(void) {
    lf_runtime_t *runtime = active_runtime;

    if (runtime == (lf_runtime_t *)0) {
        for (;;) {
            __asm__ volatile("" ::: "memory");
        }
    }
    runtime_exit_identity(runtime, runtime->executing_slot,
                          runtime->executing_pid);
}
