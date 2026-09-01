#include "micaos.h"

static bool find_process(const mica_scheduler_t *scheduler,
                         mica_pid_t pid,
                         size_t *out_index)
{
    size_t index;

    for (index = 0u; index < MICA_MAX_PROCESSES; ++index) {
        if (scheduler->processes[index].state != MICA_PROCESS_UNUSED &&
            scheduler->processes[index].pid == pid) {
            *out_index = index;
            return true;
        }
    }
    return false;
}

void mica_scheduler_init(mica_scheduler_t *scheduler)
{
    size_t index;

    if (scheduler == NULL) {
        return;
    }
    for (index = 0u; index < MICA_MAX_PROCESSES; ++index) {
        scheduler->processes[index].pid = 0u;
        scheduler->processes[index].state = MICA_PROCESS_UNUSED;
        scheduler->processes[index].exit_code = 0;
    }
    scheduler->next_pid = 1u;
    scheduler->cursor = MICA_MAX_PROCESSES - 1u;
}

mica_status_t mica_scheduler_spawn(mica_scheduler_t *scheduler,
                                   mica_pid_t *out_pid)
{
    size_t index;

    if (scheduler == NULL || out_pid == NULL) {
        return MICA_ERR_ARG;
    }
    for (index = 0u; index < MICA_MAX_PROCESSES; ++index) {
        if (scheduler->processes[index].state == MICA_PROCESS_UNUSED) {
            /* TODO: create a READY process in this slot. */
            return MICA_ERR_STATE;
        }
    }
    return MICA_ERR_FULL;
}

mica_status_t mica_scheduler_schedule(mica_scheduler_t *scheduler,
                                      mica_pid_t *out_pid)
{
    size_t index;

    if (scheduler == NULL || out_pid == NULL) {
        return MICA_ERR_ARG;
    }
    for (index = 0u; index < MICA_MAX_PROCESSES; ++index) {
        mica_process_state_t state = scheduler->processes[index].state;

        if (state == MICA_PROCESS_READY || state == MICA_PROCESS_RUNNING) {
            /* TODO: perform one deterministic round-robin decision. */
            return MICA_ERR_STATE;
        }
    }
    return MICA_ERR_NOT_FOUND;
}

mica_status_t mica_scheduler_block(mica_scheduler_t *scheduler,
                                   mica_pid_t pid)
{
    size_t index;

    if (scheduler == NULL || pid == 0u) {
        return MICA_ERR_ARG;
    }
    if (!find_process(scheduler, pid, &index)) {
        return MICA_ERR_NOT_FOUND;
    }
    if (scheduler->processes[index].state != MICA_PROCESS_RUNNING &&
        scheduler->processes[index].state != MICA_PROCESS_READY) {
        return MICA_ERR_STATE;
    }
    /* TODO: block the READY or RUNNING process. */
    return MICA_ERR_STATE;
}

mica_status_t mica_scheduler_wake(mica_scheduler_t *scheduler,
                                  mica_pid_t pid)
{
    size_t index;

    if (scheduler == NULL || pid == 0u) {
        return MICA_ERR_ARG;
    }
    if (!find_process(scheduler, pid, &index)) {
        return MICA_ERR_NOT_FOUND;
    }
    if (scheduler->processes[index].state != MICA_PROCESS_BLOCKED) {
        return MICA_ERR_STATE;
    }
    /* TODO: make the blocked process READY. */
    return MICA_ERR_STATE;
}

mica_status_t mica_scheduler_exit(mica_scheduler_t *scheduler,
                                  mica_pid_t pid,
                                  int exit_code)
{
    size_t index;

    (void)exit_code;
    if (scheduler == NULL || pid == 0u) {
        return MICA_ERR_ARG;
    }
    if (!find_process(scheduler, pid, &index)) {
        return MICA_ERR_NOT_FOUND;
    }
    if (scheduler->processes[index].state == MICA_PROCESS_EXITED) {
        return MICA_ERR_STATE;
    }
    /* TODO: retain the process as an EXITED process. */
    return MICA_ERR_STATE;
}

mica_status_t mica_scheduler_reap(mica_scheduler_t *scheduler,
                                  mica_pid_t pid,
                                  int *out_exit_code)
{
    size_t index;

    if (scheduler == NULL || out_exit_code == NULL || pid == 0u) {
        return MICA_ERR_ARG;
    }
    if (!find_process(scheduler, pid, &index)) {
        return MICA_ERR_NOT_FOUND;
    }
    if (scheduler->processes[index].state != MICA_PROCESS_EXITED) {
        return MICA_ERR_STATE;
    }
    /* TODO: return the exit status and release the slot. */
    return MICA_ERR_STATE;
}

mica_status_t mica_scheduler_inspect(const mica_scheduler_t *scheduler,
                                     mica_pid_t pid,
                                     mica_process_info_t *out_info)
{
    size_t index;

    if (scheduler == NULL || out_info == NULL || pid == 0u) {
        return MICA_ERR_ARG;
    }
    if (!find_process(scheduler, pid, &index)) {
        return MICA_ERR_NOT_FOUND;
    }
    *out_info = scheduler->processes[index];
    return MICA_OK;
}

mica_status_t mica_scheduler_get(const mica_scheduler_t *scheduler,
                                 mica_pid_t pid,
                                 mica_process_info_t *out_info)
{
    return mica_scheduler_inspect(scheduler, pid, out_info);
}
