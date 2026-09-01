#include "micaos.h"

static mica_pid_t increment_pid(mica_pid_t pid)
{
    pid++;
    if (pid == 0u) {
        pid = 1u;
    }
    return pid;
}

static bool pid_is_live(const mica_scheduler_t *scheduler, mica_pid_t pid)
{
    size_t i;

    for (i = 0u; i < MICA_MAX_PROCESSES; i++) {
        if (scheduler->processes[i].state != MICA_PROCESS_UNUSED &&
            scheduler->processes[i].pid == pid) {
            return true;
        }
    }
    return false;
}

static mica_pid_t choose_pid(const mica_scheduler_t *scheduler)
{
    mica_pid_t candidate = scheduler->next_pid;
    size_t attempts;

    if (candidate == 0u) {
        candidate = 1u;
    }
    for (attempts = 0u; attempts <= MICA_MAX_PROCESSES; attempts++) {
        if (!pid_is_live(scheduler, candidate)) {
            return candidate;
        }
        candidate = increment_pid(candidate);
    }
    return 0u;
}

static bool scheduler_is_valid(const mica_scheduler_t *scheduler)
{
    size_t i;
    size_t j;
    size_t running = 0u;

    if (scheduler->cursor >= MICA_MAX_PROCESSES) {
        return false;
    }
    for (i = 0u; i < MICA_MAX_PROCESSES; i++) {
        const mica_process_info_t *process = &scheduler->processes[i];

        if (process->state < MICA_PROCESS_UNUSED ||
            process->state > MICA_PROCESS_EXITED) {
            return false;
        }
        if (process->state == MICA_PROCESS_UNUSED) {
            if (process->pid != 0u) {
                return false;
            }
            continue;
        }
        if (process->pid == 0u) {
            return false;
        }
        if (process->state == MICA_PROCESS_RUNNING) {
            running++;
            if (running > 1u) {
                return false;
            }
        }
        for (j = i + 1u; j < MICA_MAX_PROCESSES; j++) {
            if (scheduler->processes[j].state != MICA_PROCESS_UNUSED &&
                scheduler->processes[j].pid == process->pid) {
                return false;
            }
        }
    }
    return true;
}

static bool find_process(const mica_scheduler_t *scheduler,
                         mica_pid_t pid,
                         size_t *out_index)
{
    size_t i;

    for (i = 0u; i < MICA_MAX_PROCESSES; i++) {
        if (scheduler->processes[i].state != MICA_PROCESS_UNUSED &&
            scheduler->processes[i].pid == pid) {
            *out_index = i;
            return true;
        }
    }
    return false;
}

void mica_scheduler_init(mica_scheduler_t *scheduler)
{
    size_t i;

    if (scheduler == NULL) {
        return;
    }
    for (i = 0u; i < MICA_MAX_PROCESSES; i++) {
        scheduler->processes[i].pid = 0u;
        scheduler->processes[i].state = MICA_PROCESS_UNUSED;
        scheduler->processes[i].exit_code = 0;
    }
    scheduler->next_pid = 1u;
    scheduler->cursor = MICA_MAX_PROCESSES - 1u;
}

mica_status_t mica_scheduler_spawn(mica_scheduler_t *scheduler,
                                   mica_pid_t *out_pid)
{
    size_t i;
    mica_pid_t pid;

    if (scheduler == NULL || out_pid == NULL) {
        return MICA_ERR_ARG;
    }
    if (!scheduler_is_valid(scheduler)) {
        return MICA_ERR_STATE;
    }
    for (i = 0u; i < MICA_MAX_PROCESSES; i++) {
        if (scheduler->processes[i].state == MICA_PROCESS_UNUSED) {
            break;
        }
    }
    if (i == MICA_MAX_PROCESSES) {
        return MICA_ERR_FULL;
    }

    pid = choose_pid(scheduler);
    if (pid == 0u) {
        return MICA_ERR_FULL;
    }
    scheduler->processes[i].pid = pid;
    scheduler->processes[i].state = MICA_PROCESS_READY;
    scheduler->processes[i].exit_code = 0;
    scheduler->next_pid = increment_pid(pid);
    *out_pid = pid;
    return MICA_OK;
}

mica_status_t mica_scheduler_schedule(mica_scheduler_t *scheduler,
                                      mica_pid_t *out_pid)
{
    size_t step;
    size_t selected = MICA_MAX_PROCESSES;
    size_t i;

    if (scheduler == NULL || out_pid == NULL) {
        return MICA_ERR_ARG;
    }
    if (!scheduler_is_valid(scheduler)) {
        return MICA_ERR_STATE;
    }
    for (step = 1u; step <= MICA_MAX_PROCESSES; step++) {
        i = (scheduler->cursor + step) % MICA_MAX_PROCESSES;
        if (scheduler->processes[i].state == MICA_PROCESS_READY ||
            scheduler->processes[i].state == MICA_PROCESS_RUNNING) {
            selected = i;
            break;
        }
    }
    if (selected == MICA_MAX_PROCESSES) {
        return MICA_ERR_NOT_FOUND;
    }

    for (i = 0u; i < MICA_MAX_PROCESSES; i++) {
        if (i != selected &&
            scheduler->processes[i].state == MICA_PROCESS_RUNNING) {
            scheduler->processes[i].state = MICA_PROCESS_READY;
        }
    }
    scheduler->processes[selected].state = MICA_PROCESS_RUNNING;
    scheduler->cursor = selected;
    *out_pid = scheduler->processes[selected].pid;
    return MICA_OK;
}

mica_status_t mica_scheduler_block(mica_scheduler_t *scheduler,
                                   mica_pid_t pid)
{
    size_t index;

    if (scheduler == NULL || pid == 0u) {
        return MICA_ERR_ARG;
    }
    if (!scheduler_is_valid(scheduler)) {
        return MICA_ERR_STATE;
    }
    if (!find_process(scheduler, pid, &index)) {
        return MICA_ERR_NOT_FOUND;
    }
    if (scheduler->processes[index].state != MICA_PROCESS_READY &&
        scheduler->processes[index].state != MICA_PROCESS_RUNNING) {
        return MICA_ERR_STATE;
    }
    scheduler->processes[index].state = MICA_PROCESS_BLOCKED;
    return MICA_OK;
}

mica_status_t mica_scheduler_wake(mica_scheduler_t *scheduler,
                                  mica_pid_t pid)
{
    size_t index;

    if (scheduler == NULL || pid == 0u) {
        return MICA_ERR_ARG;
    }
    if (!scheduler_is_valid(scheduler)) {
        return MICA_ERR_STATE;
    }
    if (!find_process(scheduler, pid, &index)) {
        return MICA_ERR_NOT_FOUND;
    }
    if (scheduler->processes[index].state != MICA_PROCESS_BLOCKED) {
        return MICA_ERR_STATE;
    }
    scheduler->processes[index].state = MICA_PROCESS_READY;
    return MICA_OK;
}

mica_status_t mica_scheduler_exit(mica_scheduler_t *scheduler,
                                  mica_pid_t pid,
                                  int exit_code)
{
    size_t index;

    if (scheduler == NULL || pid == 0u) {
        return MICA_ERR_ARG;
    }
    if (!scheduler_is_valid(scheduler)) {
        return MICA_ERR_STATE;
    }
    if (!find_process(scheduler, pid, &index)) {
        return MICA_ERR_NOT_FOUND;
    }
    if (scheduler->processes[index].state == MICA_PROCESS_EXITED) {
        return MICA_ERR_STATE;
    }
    scheduler->processes[index].state = MICA_PROCESS_EXITED;
    scheduler->processes[index].exit_code = exit_code;
    return MICA_OK;
}

mica_status_t mica_scheduler_reap(mica_scheduler_t *scheduler,
                                  mica_pid_t pid,
                                  int *out_exit_code)
{
    size_t index;
    int exit_code;

    if (scheduler == NULL || pid == 0u || out_exit_code == NULL) {
        return MICA_ERR_ARG;
    }
    if (!scheduler_is_valid(scheduler)) {
        return MICA_ERR_STATE;
    }
    if (!find_process(scheduler, pid, &index)) {
        return MICA_ERR_NOT_FOUND;
    }
    if (scheduler->processes[index].state != MICA_PROCESS_EXITED) {
        return MICA_ERR_STATE;
    }

    exit_code = scheduler->processes[index].exit_code;
    scheduler->processes[index].pid = 0u;
    scheduler->processes[index].state = MICA_PROCESS_UNUSED;
    scheduler->processes[index].exit_code = 0;
    *out_exit_code = exit_code;
    return MICA_OK;
}

mica_status_t mica_scheduler_inspect(const mica_scheduler_t *scheduler,
                                     mica_pid_t pid,
                                     mica_process_info_t *out_info)
{
    size_t index;

    if (scheduler == NULL || pid == 0u || out_info == NULL) {
        return MICA_ERR_ARG;
    }
    if (!scheduler_is_valid(scheduler)) {
        return MICA_ERR_STATE;
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
