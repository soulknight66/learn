#include "tinykernel.h"

static int find_process(const tk_scheduler_t *scheduler, uint32_t pid)
{
    size_t index;

    if (scheduler == NULL || pid == 0u) {
        return -1;
    }
    for (index = 0; index < TK_MAX_PROCESSES; ++index) {
        if (scheduler->processes[index].state != TK_UNUSED &&
            scheduler->processes[index].pid == pid) {
            return (int)index;
        }
    }
    return -1;
}

void tk_scheduler_init(tk_scheduler_t *scheduler)
{
    size_t index;

    if (scheduler == NULL) {
        return;
    }
    for (index = 0; index < TK_MAX_PROCESSES; ++index) {
        scheduler->processes[index].pid = 0u;
        scheduler->processes[index].state = TK_UNUSED;
        scheduler->processes[index].quanta = 0u;
    }
    scheduler->current_slot = -1;
    scheduler->cursor = TK_MAX_PROCESSES - 1u;
    scheduler->next_pid = 1u;
}

int tk_process_spawn(tk_scheduler_t *scheduler)
{
    size_t index;
    uint32_t pid;

    if (scheduler == NULL || scheduler->next_pid == 0u ||
        scheduler->next_pid > (uint32_t)INT32_MAX) {
        return -1;
    }
    for (index = 0; index < TK_MAX_PROCESSES; ++index) {
        tk_process_state_t state = scheduler->processes[index].state;
        if (state == TK_UNUSED || state == TK_EXITED) {
            pid = scheduler->next_pid;
            ++scheduler->next_pid;
            scheduler->processes[index].pid = pid;
            scheduler->processes[index].state = TK_READY;
            scheduler->processes[index].quanta = 0u;
            return (int)pid;
        }
    }
    return -1;
}

int tk_schedule(tk_scheduler_t *scheduler)
{
    size_t step;

    if (scheduler == NULL) {
        return -1;
    }
    if (scheduler->current_slot >= 0 &&
        (size_t)scheduler->current_slot < TK_MAX_PROCESSES &&
        scheduler->processes[scheduler->current_slot].state == TK_RUNNING) {
        scheduler->processes[scheduler->current_slot].state = TK_READY;
    }
    scheduler->current_slot = -1;

    for (step = 1u; step <= TK_MAX_PROCESSES; ++step) {
        size_t index = (scheduler->cursor + step) % TK_MAX_PROCESSES;
        if (scheduler->processes[index].state == TK_READY) {
            scheduler->processes[index].state = TK_RUNNING;
            ++scheduler->processes[index].quanta;
            scheduler->current_slot = (int)index;
            scheduler->cursor = index;
            return (int)scheduler->processes[index].pid;
        }
    }
    return -1;
}

int tk_process_block(tk_scheduler_t *scheduler, uint32_t pid)
{
    int index = find_process(scheduler, pid);

    if (index < 0 || (scheduler->processes[index].state != TK_READY &&
                      scheduler->processes[index].state != TK_RUNNING)) {
        return -1;
    }
    if (scheduler->current_slot == index) {
        scheduler->current_slot = -1;
    }
    scheduler->processes[index].state = TK_BLOCKED;
    return 0;
}

int tk_process_wake(tk_scheduler_t *scheduler, uint32_t pid)
{
    int index = find_process(scheduler, pid);

    if (index < 0 || scheduler->processes[index].state != TK_BLOCKED) {
        return -1;
    }
    scheduler->processes[index].state = TK_READY;
    return 0;
}

int tk_process_exit(tk_scheduler_t *scheduler, uint32_t pid)
{
    int index = find_process(scheduler, pid);
    tk_process_state_t state;

    if (index < 0) {
        return -1;
    }
    state = scheduler->processes[index].state;
    if (state != TK_READY && state != TK_RUNNING && state != TK_BLOCKED) {
        return -1;
    }
    if (scheduler->current_slot == index) {
        scheduler->current_slot = -1;
    }
    scheduler->processes[index].state = TK_EXITED;
    return 0;
}

tk_process_state_t tk_process_state(const tk_scheduler_t *scheduler, uint32_t pid)
{
    int index = find_process(scheduler, pid);

    if (index < 0) {
        return TK_UNUSED;
    }
    return scheduler->processes[index].state;
}

int tk_current_pid(const tk_scheduler_t *scheduler)
{
    int index;

    if (scheduler == NULL) {
        return -1;
    }
    index = scheduler->current_slot;
    if (index < 0 || (size_t)index >= TK_MAX_PROCESSES ||
        scheduler->processes[index].state != TK_RUNNING) {
        return -1;
    }
    return (int)scheduler->processes[index].pid;
}
