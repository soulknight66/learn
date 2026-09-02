#include "kernel/scheduler.h"

/* Stage 2: replace the deterministic initialization below and every stub with
 * transitions satisfying REQUIREMENTS.md. Keep policy independent of ARM. */
void lf_scheduler_init(lf_scheduler_t *scheduler) {
    uint32_t slot;
    if (scheduler == (lf_scheduler_t *)0) {
        return;
    }
    for (slot = 0u; slot < LF_MAX_TASKS; ++slot) {
        scheduler->tasks[slot].pid = 0u;
        scheduler->tasks[slot].state = LF_TASK_UNUSED;
        scheduler->tasks[slot].entry = (lf_task_entry_t)0;
        scheduler->tasks[slot].argument = (void *)0;
    }
    scheduler->current_slot = LF_NO_SLOT;
    scheduler->next_pid = 1u;
}

uint32_t lf_scheduler_spawn(lf_scheduler_t *scheduler,
                            lf_task_entry_t entry, void *argument) {
    (void)scheduler;
    (void)entry;
    (void)argument;
    return 0u;
}

uint32_t lf_scheduler_rotate(lf_scheduler_t *scheduler) {
    (void)scheduler;
    return 0u;
}

uint32_t lf_scheduler_block_current(lf_scheduler_t *scheduler) {
    (void)scheduler;
    return 0u;
}

uint32_t lf_scheduler_exit_current(lf_scheduler_t *scheduler) {
    (void)scheduler;
    return 0u;
}

bool lf_scheduler_unblock(lf_scheduler_t *scheduler, uint32_t pid) {
    (void)scheduler;
    (void)pid;
    return false;
}

bool lf_scheduler_reap(lf_scheduler_t *scheduler, uint32_t pid) {
    (void)scheduler;
    (void)pid;
    return false;
}

int32_t lf_scheduler_slot_of(const lf_scheduler_t *scheduler, uint32_t pid) {
    (void)scheduler;
    (void)pid;
    return LF_NO_SLOT;
}

const lf_task_t *lf_scheduler_task(const lf_scheduler_t *scheduler,
                                   uint32_t pid) {
    (void)scheduler;
    (void)pid;
    return (const lf_task_t *)0;
}

bool lf_scheduler_invariant(const lf_scheduler_t *scheduler) {
    return scheduler != (const lf_scheduler_t *)0 &&
           scheduler->current_slot == LF_NO_SLOT;
}
