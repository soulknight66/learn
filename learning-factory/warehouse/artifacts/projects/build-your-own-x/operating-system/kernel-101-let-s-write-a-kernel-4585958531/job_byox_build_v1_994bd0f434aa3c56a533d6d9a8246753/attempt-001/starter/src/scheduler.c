#include "tinykernel.h"

void tk_scheduler_init(tk_scheduler_t *scheduler)
{
    if (scheduler != NULL) {
        size_t i;
        for (i = 0; i < TK_MAX_PROCESSES; ++i) {
            scheduler->processes[i].pid = 0u;
            scheduler->processes[i].state = TK_UNUSED;
            scheduler->processes[i].quanta = 0u;
        }
        scheduler->current_slot = -1;
        scheduler->cursor = TK_MAX_PROCESSES - 1u;
        scheduler->next_pid = 1u;
    }
}

int tk_process_spawn(tk_scheduler_t *scheduler)
{
    (void)scheduler;
    /* TODO(stage 2): allocate a reusable slot and a fresh PID. */
    return -1;
}

int tk_schedule(tk_scheduler_t *scheduler)
{
    (void)scheduler;
    /* TODO(stage 2): make the current process ready, then scan cyclically. */
    return -1;
}

int tk_process_block(tk_scheduler_t *scheduler, uint32_t pid)
{
    (void)scheduler;
    (void)pid;
    return -1;
}

int tk_process_wake(tk_scheduler_t *scheduler, uint32_t pid)
{
    (void)scheduler;
    (void)pid;
    return -1;
}

int tk_process_exit(tk_scheduler_t *scheduler, uint32_t pid)
{
    (void)scheduler;
    (void)pid;
    return -1;
}

tk_process_state_t tk_process_state(const tk_scheduler_t *scheduler, uint32_t pid)
{
    (void)scheduler;
    (void)pid;
    return TK_UNUSED;
}

int tk_current_pid(const tk_scheduler_t *scheduler)
{
    (void)scheduler;
    return -1;
}
