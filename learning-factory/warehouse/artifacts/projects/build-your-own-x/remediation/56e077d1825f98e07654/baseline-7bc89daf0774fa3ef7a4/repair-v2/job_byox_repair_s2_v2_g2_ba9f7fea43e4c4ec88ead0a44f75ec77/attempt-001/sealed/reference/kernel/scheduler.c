#include "kernel/scheduler.h"

static void clear_task(lf_task_t *task) {
    task->pid = 0u;
    task->state = LF_TASK_UNUSED;
    task->entry = (lf_task_entry_t)0;
    task->argument = (void *)0;
}

static uint32_t select_after(lf_scheduler_t *scheduler, int32_t old_slot) {
    uint32_t start;
    uint32_t distance;

    start = old_slot >= 0 ? (uint32_t)old_slot : LF_MAX_TASKS - 1u;
    for (distance = 1u; distance <= LF_MAX_TASKS; ++distance) {
        uint32_t slot = (start + distance) % LF_MAX_TASKS;
        if (scheduler->tasks[slot].state == LF_TASK_READY) {
            scheduler->tasks[slot].state = LF_TASK_RUNNING;
            scheduler->current_slot = (int32_t)slot;
            return scheduler->tasks[slot].pid;
        }
    }

    scheduler->current_slot = LF_NO_SLOT;
    return 0u;
}

void lf_scheduler_init(lf_scheduler_t *scheduler) {
    uint32_t slot;

    if (scheduler == (lf_scheduler_t *)0) {
        return;
    }
    for (slot = 0u; slot < LF_MAX_TASKS; ++slot) {
        clear_task(&scheduler->tasks[slot]);
    }
    scheduler->current_slot = LF_NO_SLOT;
    scheduler->next_pid = 1u;
}

uint32_t lf_scheduler_spawn(lf_scheduler_t *scheduler,
                            lf_task_entry_t entry,
                            void *argument) {
    uint32_t slot;
    uint32_t pid;

    if (scheduler == (lf_scheduler_t *)0 || entry == (lf_task_entry_t)0 ||
        scheduler->next_pid == 0u || !lf_scheduler_invariant(scheduler)) {
        return 0u;
    }
    for (slot = 0u; slot < LF_MAX_TASKS; ++slot) {
        if (scheduler->tasks[slot].state == LF_TASK_UNUSED) {
            pid = scheduler->next_pid;
            scheduler->next_pid = pid == UINT32_MAX ? 0u : pid + 1u;
            scheduler->tasks[slot].pid = pid;
            scheduler->tasks[slot].entry = entry;
            scheduler->tasks[slot].argument = argument;
            scheduler->tasks[slot].state = LF_TASK_READY;
            return pid;
        }
    }
    return 0u;
}

uint32_t lf_scheduler_rotate(lf_scheduler_t *scheduler) {
    int32_t old_slot;

    if (scheduler == (lf_scheduler_t *)0 || !lf_scheduler_invariant(scheduler)) {
        return 0u;
    }
    old_slot = scheduler->current_slot;
    if (old_slot >= 0) {
        scheduler->tasks[(uint32_t)old_slot].state = LF_TASK_READY;
    }
    return select_after(scheduler, old_slot);
}

uint32_t lf_scheduler_block_current(lf_scheduler_t *scheduler) {
    int32_t old_slot;

    if (scheduler == (lf_scheduler_t *)0 || !lf_scheduler_invariant(scheduler) ||
        scheduler->current_slot < 0) {
        return 0u;
    }
    old_slot = scheduler->current_slot;
    scheduler->tasks[(uint32_t)old_slot].state = LF_TASK_BLOCKED;
    scheduler->current_slot = LF_NO_SLOT;
    return select_after(scheduler, old_slot);
}

uint32_t lf_scheduler_exit_current(lf_scheduler_t *scheduler) {
    int32_t old_slot;

    if (scheduler == (lf_scheduler_t *)0 || !lf_scheduler_invariant(scheduler) ||
        scheduler->current_slot < 0) {
        return 0u;
    }
    old_slot = scheduler->current_slot;
    scheduler->tasks[(uint32_t)old_slot].state = LF_TASK_ZOMBIE;
    scheduler->current_slot = LF_NO_SLOT;
    return select_after(scheduler, old_slot);
}

int32_t lf_scheduler_slot_of(const lf_scheduler_t *scheduler, uint32_t pid) {
    uint32_t slot;

    if (scheduler == (const lf_scheduler_t *)0 || pid == 0u) {
        return LF_NO_SLOT;
    }
    for (slot = 0u; slot < LF_MAX_TASKS; ++slot) {
        if (scheduler->tasks[slot].state != LF_TASK_UNUSED &&
            scheduler->tasks[slot].pid == pid) {
            return (int32_t)slot;
        }
    }
    return LF_NO_SLOT;
}

bool lf_scheduler_unblock(lf_scheduler_t *scheduler, uint32_t pid) {
    int32_t slot;

    if (scheduler == (lf_scheduler_t *)0 || !lf_scheduler_invariant(scheduler)) {
        return false;
    }
    slot = lf_scheduler_slot_of(scheduler, pid);
    if (slot < 0 || scheduler->tasks[(uint32_t)slot].state != LF_TASK_BLOCKED) {
        return false;
    }
    scheduler->tasks[(uint32_t)slot].state = LF_TASK_READY;
    return true;
}

bool lf_scheduler_reap(lf_scheduler_t *scheduler, uint32_t pid) {
    int32_t slot;

    if (scheduler == (lf_scheduler_t *)0 || !lf_scheduler_invariant(scheduler)) {
        return false;
    }
    slot = lf_scheduler_slot_of(scheduler, pid);
    if (slot < 0 || scheduler->tasks[(uint32_t)slot].state != LF_TASK_ZOMBIE) {
        return false;
    }
    clear_task(&scheduler->tasks[(uint32_t)slot]);
    return true;
}

const lf_task_t *lf_scheduler_task(const lf_scheduler_t *scheduler,
                                   uint32_t pid) {
    int32_t slot = lf_scheduler_slot_of(scheduler, pid);
    return slot < 0 ? (const lf_task_t *)0 : &scheduler->tasks[(uint32_t)slot];
}

bool lf_scheduler_invariant(const lf_scheduler_t *scheduler) {
    uint32_t slot;
    uint32_t other;
    uint32_t running = 0u;

    if (scheduler == (const lf_scheduler_t *)0 || scheduler->current_slot < LF_NO_SLOT ||
        scheduler->current_slot >= (int32_t)LF_MAX_TASKS) {
        return false;
    }
    for (slot = 0u; slot < LF_MAX_TASKS; ++slot) {
        const lf_task_t *task = &scheduler->tasks[slot];
        if (task->state > LF_TASK_ZOMBIE) {
            return false;
        }
        if (task->state == LF_TASK_UNUSED) {
            if (task->pid != 0u || task->entry != (lf_task_entry_t)0 ||
                task->argument != (void *)0) {
                return false;
            }
            continue;
        }
        if (task->pid == 0u || task->entry == (lf_task_entry_t)0) {
            return false;
        }
        if (scheduler->next_pid != 0u && task->pid >= scheduler->next_pid) {
            return false;
        }
        if (task->state == LF_TASK_RUNNING) {
            ++running;
            if (scheduler->current_slot != (int32_t)slot) {
                return false;
            }
        }
        for (other = slot + 1u; other < LF_MAX_TASKS; ++other) {
            if (scheduler->tasks[other].state != LF_TASK_UNUSED &&
                scheduler->tasks[other].pid == task->pid) {
                return false;
            }
        }
    }
    if (scheduler->current_slot == LF_NO_SLOT) {
        return running == 0u;
    }
    return running == 1u;
}
