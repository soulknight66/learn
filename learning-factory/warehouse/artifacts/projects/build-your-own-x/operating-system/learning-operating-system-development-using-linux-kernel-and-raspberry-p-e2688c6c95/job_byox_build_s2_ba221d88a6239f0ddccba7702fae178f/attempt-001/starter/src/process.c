#include "minios.h"

void proc_table_init(proc_table_t *table)
{
    size_t i;

    if (table == NULL) {
        return;
    }
    for (i = 0; i < MINIOS_MAX_PROCESSES; ++i) {
        table->slots[i].pid = 0;
        table->slots[i].parent_pid = 0;
        table->slots[i].entry_point = (uintptr_t)0;
        table->slots[i].exit_code = 0;
        table->slots[i].state = PROC_UNUSED;
    }
    table->next_pid = 1;
    table->current_slot = -1;
}

os_status_t proc_get(const proc_table_t *table, uint32_t pid,
                     const process_t **out_process)
{
    /* TODO: validate the request and locate an occupied slot by PID. */
    (void)table;
    (void)pid;
    if (out_process != NULL) {
        *out_process = NULL;
    }
    return OS_ERR_NOT_FOUND;
}

os_status_t proc_spawn(proc_table_t *table, uint32_t parent_pid,
                       uintptr_t entry_point, uint32_t *out_pid)
{
    /* TODO: validate the parent, reserve the lowest free slot, and issue a PID. */
    (void)table;
    (void)parent_pid;
    (void)entry_point;
    if (out_pid != NULL) {
        *out_pid = 0;
    }
    return OS_ERR_FULL;
}

os_status_t proc_schedule(proc_table_t *table, uint32_t *out_pid)
{
    /* TODO: preempt the current process and make one ready process run. */
    (void)table;
    if (out_pid != NULL) {
        *out_pid = 0;
    }
    return OS_ERR_NOT_FOUND;
}

os_status_t proc_block(proc_table_t *table, uint32_t pid)
{
    /* TODO: permit only the currently running process to block. */
    (void)table;
    (void)pid;
    return OS_ERR_STATE;
}

os_status_t proc_wake(proc_table_t *table, uint32_t pid)
{
    /* TODO: make a blocked process ready. */
    (void)table;
    (void)pid;
    return OS_ERR_STATE;
}

os_status_t proc_exit(proc_table_t *table, uint32_t pid, int32_t exit_code)
{
    /* TODO: preserve the exit result in a zombie slot. */
    (void)table;
    (void)pid;
    (void)exit_code;
    return OS_ERR_STATE;
}

os_status_t proc_reap(proc_table_t *table, uint32_t pid,
                      int32_t *out_exit_code)
{
    /* TODO: return a zombie's code and fully release its slot. */
    (void)table;
    (void)pid;
    if (out_exit_code != NULL) {
        *out_exit_code = 0;
    }
    return OS_ERR_STATE;
}
