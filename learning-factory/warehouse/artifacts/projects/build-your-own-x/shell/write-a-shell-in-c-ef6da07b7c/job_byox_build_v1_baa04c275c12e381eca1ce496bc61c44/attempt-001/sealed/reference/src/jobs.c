#include "msh.h"

#include <errno.h>
#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>

typedef enum {
    JOB_RUNNING,
    JOB_STOPPED,
    JOB_DONE
} derived_job_state;

static derived_job_state derive_state(const msh_job *job)
{
    size_t index;
    int saw_running = 0;
    int saw_stopped = 0;

    for (index = 0; index < job->process_count; ++index) {
        if (job->process_states[index] == MSH_PROCESS_RUNNING) {
            saw_running = 1;
        } else if (job->process_states[index] == MSH_PROCESS_STOPPED) {
            saw_stopped = 1;
        }
    }
    if (saw_running) {
        return JOB_RUNNING;
    }
    if (saw_stopped) {
        return JOB_STOPPED;
    }
    return JOB_DONE;
}

static int normalize_status(int status)
{
    if (WIFEXITED(status)) {
        return WEXITSTATUS(status);
    }
    if (WIFSIGNALED(status)) {
        return 128 + WTERMSIG(status);
    }
    if (WIFSTOPPED(status)) {
        return 128 + WSTOPSIG(status);
    }
    return 1;
}

static void free_job(msh_job *job)
{
    free(job->text);
    free(job->pids);
    free(job->process_states);
    memset(job, 0, sizeof(*job));
}

static int ensure_capacity(msh_job_table *table)
{
    size_t next;
    msh_job *replacement;

    if (table->count < table->capacity) {
        return 0;
    }
    next = table->capacity == 0 ? 8 : table->capacity * 2;
    if (next < table->capacity || next > SIZE_MAX / sizeof(*table->items)) {
        return -1;
    }
    replacement = realloc(table->items, next * sizeof(*table->items));
    if (replacement == NULL) {
        return -1;
    }
    table->items = replacement;
    table->capacity = next;
    return 0;
}

void msh_jobs_init(msh_job_table *table)
{
    table->items = NULL;
    table->count = 0;
    table->capacity = 0;
    table->next_id = 1;
}

void msh_jobs_destroy(msh_job_table *table)
{
    size_t index;

    for (index = 0; index < table->count; ++index) {
        free_job(&table->items[index]);
    }
    free(table->items);
    msh_jobs_init(table);
}

int msh_jobs_add(msh_job_table *table, pid_t pgid, const pid_t *pids,
                 size_t process_count, const char *text)
{
    msh_job pending;
    size_t bytes;
    size_t index;

    if (table == NULL || pids == NULL || process_count == 0 || text == NULL ||
        table->next_id == 0 || table->next_id > (unsigned)INT_MAX ||
        process_count > SIZE_MAX / sizeof(*pending.pids) ||
        process_count > SIZE_MAX / sizeof(*pending.process_states)) {
        return -1;
    }

    memset(&pending, 0, sizeof(pending));
    bytes = process_count * sizeof(*pending.pids);
    pending.pids = malloc(bytes);
    pending.process_states = malloc(process_count * sizeof(*pending.process_states));
    pending.text = strdup(text);
    if (pending.pids == NULL || pending.process_states == NULL || pending.text == NULL) {
        free_job(&pending);
        return -1;
    }
    memcpy(pending.pids, pids, bytes);
    for (index = 0; index < process_count; ++index) {
        pending.process_states[index] = MSH_PROCESS_RUNNING;
    }
    if (ensure_capacity(table) < 0) {
        free_job(&pending);
        return -1;
    }

    pending.id = table->next_id++;
    pending.pgid = pgid;
    pending.process_count = process_count;
    pending.last_wait_status = 0;
    table->items[table->count++] = pending;
    return (int)pending.id;
}

void msh_jobs_note_status(msh_job_table *table, pid_t pid, int wait_status)
{
    size_t job_index;

    for (job_index = 0; job_index < table->count; ++job_index) {
        msh_job *job = &table->items[job_index];
        size_t process_index;

        for (process_index = 0; process_index < job->process_count; ++process_index) {
            if (job->pids[process_index] != pid) {
                continue;
            }
            if (WIFSTOPPED(wait_status)) {
                job->process_states[process_index] = MSH_PROCESS_STOPPED;
#ifdef WIFCONTINUED
            } else if (WIFCONTINUED(wait_status)) {
                job->process_states[process_index] = MSH_PROCESS_RUNNING;
#endif
            } else if (WIFEXITED(wait_status) || WIFSIGNALED(wait_status)) {
                job->process_states[process_index] = MSH_PROCESS_DONE;
            }
            if (process_index + 1 == job->process_count &&
                !WIFCONTINUED(wait_status)) {
                job->last_wait_status = wait_status;
            }
            return;
        }
    }
}

void msh_jobs_reap(msh_job_table *table)
{
    for (;;) {
        int status;
        pid_t pid = waitpid(-1, &status, WNOHANG | WUNTRACED | WCONTINUED);

        if (pid > 0) {
            msh_jobs_note_status(table, pid, status);
            continue;
        }
        if (pid < 0 && errno == EINTR) {
            continue;
        }
        return;
    }
}

void msh_jobs_print(msh_job_table *table, FILE *stream)
{
    size_t index;

    msh_jobs_reap(table);
    for (index = 0; index < table->count; ++index) {
        const msh_job *job = &table->items[index];
        const derived_job_state state = derive_state(job);
        const char *label = state == JOB_RUNNING ? "Running" :
                            state == JOB_STOPPED ? "Stopped" : "Done";

        (void)fprintf(stream, "[%u] %s %ld %s\n", job->id, label,
                      (long)job->pgid, job->text);
    }
    (void)fflush(stream);
}

size_t msh_jobs_active(const msh_job_table *table)
{
    size_t index;
    size_t active = 0;

    for (index = 0; index < table->count; ++index) {
        if (derive_state(&table->items[index]) != JOB_DONE) {
            ++active;
        }
    }
    return active;
}

static int has_running_process(const msh_job_table *table)
{
    size_t job_index;

    for (job_index = 0; job_index < table->count; ++job_index) {
        const msh_job *job = &table->items[job_index];
        size_t process_index;

        for (process_index = 0; process_index < job->process_count; ++process_index) {
            if (job->process_states[process_index] == MSH_PROCESS_RUNNING) {
                return 1;
            }
        }
    }
    return 0;
}

static int last_retained_status(const msh_job_table *table)
{
    size_t index;
    const msh_job *selected = NULL;

    for (index = 0; index < table->count; ++index) {
        const msh_job *candidate = &table->items[index];
        if (derive_state(candidate) == JOB_DONE &&
            (selected == NULL || candidate->id > selected->id)) {
            selected = candidate;
        }
    }
    return selected == NULL ? 0 : normalize_status(selected->last_wait_status);
}

static void discard_done_jobs(msh_job_table *table)
{
    size_t source;
    size_t destination = 0;

    for (source = 0; source < table->count; ++source) {
        if (derive_state(&table->items[source]) == JOB_DONE) {
            free_job(&table->items[source]);
        } else {
            if (destination != source) {
                table->items[destination] = table->items[source];
                memset(&table->items[source], 0, sizeof(table->items[source]));
            }
            ++destination;
        }
    }
    table->count = destination;
}

int msh_jobs_wait_all(msh_job_table *table)
{
    int result;

    msh_jobs_reap(table);
    while (msh_jobs_active(table) > 0 && has_running_process(table)) {
        int status;
        pid_t pid = waitpid(-1, &status, WUNTRACED | WCONTINUED);

        if (pid > 0) {
            msh_jobs_note_status(table, pid, status);
            continue;
        }
        if (pid < 0 && errno == EINTR) {
            continue;
        }
        if (pid < 0 && errno == ECHILD) {
            break;
        }
        if (pid < 0) {
            (void)fprintf(stderr, "msh: waitpid: %s\n", strerror(errno));
            return 1;
        }
    }

    result = last_retained_status(table);
    discard_done_jobs(table);
    if (msh_jobs_active(table) > 0 && !has_running_process(table)) {
        (void)fprintf(stderr, "msh: wait: remaining jobs are stopped\n");
        return 1;
    }
    return result;
}
