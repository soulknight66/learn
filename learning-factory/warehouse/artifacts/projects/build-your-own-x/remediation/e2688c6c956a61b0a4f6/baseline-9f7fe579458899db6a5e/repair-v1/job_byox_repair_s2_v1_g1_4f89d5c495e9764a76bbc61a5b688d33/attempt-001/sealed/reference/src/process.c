#include "minios.h"

static void clear_process(process_t *process)
{
    process->pid = 0;
    process->parent_pid = 0;
    process->entry_point = (uintptr_t)0;
    process->exit_code = 0;
    process->state = PROC_UNUSED;
}

static int find_process_index(const proc_table_t *table, uint32_t pid)
{
    size_t i;

    if (pid == 0u) {
        return -1;
    }
    for (i = 0; i < MINIOS_MAX_PROCESSES; ++i) {
        if (table->slots[i].state != PROC_UNUSED &&
            table->slots[i].pid == pid) {
            return (int)i;
        }
    }
    return -1;
}

void proc_table_init(proc_table_t *table)
{
    size_t i;

    if (table == NULL) {
        return;
    }
    for (i = 0; i < MINIOS_MAX_PROCESSES; ++i) {
        clear_process(&table->slots[i]);
    }
    table->next_pid = 1u;
    table->current_slot = -1;
}

os_status_t proc_get(const proc_table_t *table, uint32_t pid,
                     const process_t **out_process)
{
    int index;

    if (out_process != NULL) {
        *out_process = NULL;
    }
    if (table == NULL || out_process == NULL) {
        return OS_ERR_INVALID;
    }
    index = find_process_index(table, pid);
    if (index < 0) {
        return OS_ERR_NOT_FOUND;
    }
    *out_process = &table->slots[(size_t)index];
    return OS_OK;
}

os_status_t proc_spawn(proc_table_t *table, uint32_t parent_pid,
                       uintptr_t entry_point, uint32_t *out_pid)
{
    size_t free_index = MINIOS_MAX_PROCESSES;
    size_t i;

    if (out_pid != NULL) {
        *out_pid = 0u;
    }
    if (table == NULL || out_pid == NULL) {
        return OS_ERR_INVALID;
    }
    if (parent_pid != 0u) {
        int parent_index = find_process_index(table, parent_pid);
        if (parent_index < 0) {
            return OS_ERR_NOT_FOUND;
        }
        if (table->slots[(size_t)parent_index].state == PROC_ZOMBIE) {
            return OS_ERR_STATE;
        }
    }
    if (table->next_pid == 0u) {
        return OS_ERR_FULL;
    }
    for (i = 0; i < MINIOS_MAX_PROCESSES; ++i) {
        if (table->slots[i].state == PROC_UNUSED) {
            free_index = i;
            break;
        }
    }
    if (free_index == MINIOS_MAX_PROCESSES) {
        return OS_ERR_FULL;
    }

    table->slots[free_index].pid = table->next_pid;
    table->slots[free_index].parent_pid = parent_pid;
    table->slots[free_index].entry_point = entry_point;
    table->slots[free_index].exit_code = 0;
    table->slots[free_index].state = PROC_READY;
    *out_pid = table->next_pid;
    ++table->next_pid;
    return OS_OK;
}

os_status_t proc_schedule(proc_table_t *table, uint32_t *out_pid)
{
    size_t start;
    size_t step;
    size_t selected = MINIOS_MAX_PROCESSES;
    int old_current;

    if (out_pid != NULL) {
        *out_pid = 0u;
    }
    if (table == NULL || out_pid == NULL) {
        return OS_ERR_INVALID;
    }

    old_current = table->current_slot;
    if (old_current == -1) {
        start = MINIOS_MAX_PROCESSES - 1u;
    } else {
        if (old_current < 0 ||
            (size_t)old_current >= MINIOS_MAX_PROCESSES ||
            table->slots[(size_t)old_current].state != PROC_RUNNING) {
            return OS_ERR_STATE;
        }
        start = (size_t)old_current;
    }

    for (step = 1u; step <= MINIOS_MAX_PROCESSES; ++step) {
        size_t index = (start + step) % MINIOS_MAX_PROCESSES;
        proc_state_t state = table->slots[index].state;
        if (state == PROC_READY ||
            ((int)index == old_current && state == PROC_RUNNING)) {
            selected = index;
            break;
        }
    }
    if (selected == MINIOS_MAX_PROCESSES) {
        table->current_slot = -1;
        return OS_ERR_NOT_FOUND;
    }

    if (old_current >= 0) {
        table->slots[(size_t)old_current].state = PROC_READY;
    }
    table->slots[selected].state = PROC_RUNNING;
    table->current_slot = (int32_t)selected;
    *out_pid = table->slots[selected].pid;
    return OS_OK;
}

os_status_t proc_block(proc_table_t *table, uint32_t pid)
{
    int index;

    if (table == NULL) {
        return OS_ERR_INVALID;
    }
    index = find_process_index(table, pid);
    if (index < 0) {
        return OS_ERR_NOT_FOUND;
    }
    if (table->slots[(size_t)index].state != PROC_RUNNING ||
        table->current_slot != index) {
        return OS_ERR_STATE;
    }
    table->slots[(size_t)index].state = PROC_BLOCKED;
    table->current_slot = -1;
    return OS_OK;
}

os_status_t proc_wake(proc_table_t *table, uint32_t pid)
{
    int index;

    if (table == NULL) {
        return OS_ERR_INVALID;
    }
    index = find_process_index(table, pid);
    if (index < 0) {
        return OS_ERR_NOT_FOUND;
    }
    if (table->slots[(size_t)index].state != PROC_BLOCKED) {
        return OS_ERR_STATE;
    }
    table->slots[(size_t)index].state = PROC_READY;
    return OS_OK;
}

os_status_t proc_exit(proc_table_t *table, uint32_t pid, int32_t exit_code)
{
    int index;
    proc_state_t state;

    if (table == NULL) {
        return OS_ERR_INVALID;
    }
    index = find_process_index(table, pid);
    if (index < 0) {
        return OS_ERR_NOT_FOUND;
    }
    state = table->slots[(size_t)index].state;
    if (state != PROC_READY && state != PROC_RUNNING &&
        state != PROC_BLOCKED) {
        return OS_ERR_STATE;
    }
    table->slots[(size_t)index].exit_code = exit_code;
    table->slots[(size_t)index].state = PROC_ZOMBIE;
    if (table->current_slot == index) {
        table->current_slot = -1;
    }
    return OS_OK;
}

os_status_t proc_reap(proc_table_t *table, uint32_t pid,
                      int32_t *out_exit_code)
{
    int index;

    if (out_exit_code != NULL) {
        *out_exit_code = 0;
    }
    if (table == NULL || out_exit_code == NULL) {
        return OS_ERR_INVALID;
    }
    index = find_process_index(table, pid);
    if (index < 0) {
        return OS_ERR_NOT_FOUND;
    }
    if (table->slots[(size_t)index].state != PROC_ZOMBIE) {
        return OS_ERR_STATE;
    }
    *out_exit_code = table->slots[(size_t)index].exit_code;
    clear_process(&table->slots[(size_t)index]);
    return OS_OK;
}
