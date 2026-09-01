#include "msh.h"

#include <stdlib.h>

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
        free(table->items[index].text);
        free(table->items[index].pids);
        free(table->items[index].process_states);
    }
    free(table->items);
    msh_jobs_init(table);
}

int msh_jobs_add(msh_job_table *table, pid_t pgid, const pid_t *pids,
                 size_t process_count, const char *text)
{
    (void)table;
    (void)pgid;
    (void)pids;
    (void)process_count;
    (void)text;
    /* TODO(stage 4): copy owned job data and return a monotonic job ID. */
    return -1;
}

void msh_jobs_note_status(msh_job_table *table, pid_t pid, int wait_status)
{
    (void)table;
    (void)pid;
    (void)wait_status;
    /* TODO(stage 4): map a child status change back to its retained job. */
}

void msh_jobs_reap(msh_job_table *table)
{
    (void)table;
    /* TODO(stage 4): perform nonblocking waitpid calls until drained. */
}

void msh_jobs_print(msh_job_table *table, FILE *stream)
{
    (void)table;
    (void)stream;
    /* TODO(stage 4): derive and print one state per retained job. */
}

int msh_jobs_wait_all(msh_job_table *table)
{
    (void)table;
    /* TODO(stage 4): block without spinning and normalize the last status. */
    return 0;
}

size_t msh_jobs_active(const msh_job_table *table)
{
    (void)table;
    /* TODO(stage 4): count jobs containing at least one non-done process. */
    return 0;
}
