#ifndef MSH_H
#define MSH_H

#include <stddef.h>
#include <stdio.h>
#include <sys/types.h>

typedef struct {
    char **argv;
    size_t argc;
} msh_command;

typedef struct {
    msh_command *commands;
    size_t count;
    int background;
} msh_pipeline;

typedef enum {
    MSH_PARSE_OK = 0,
    MSH_PARSE_EMPTY = 1,
    MSH_PARSE_ERROR = 2
} msh_parse_result;

msh_parse_result msh_parse_line(const char *line, msh_pipeline *out,
                                char *error, size_t error_size);
void msh_pipeline_destroy(msh_pipeline *pipeline);

typedef enum {
    MSH_PROCESS_RUNNING = 0,
    MSH_PROCESS_STOPPED = 1,
    MSH_PROCESS_DONE = 2
} msh_process_state;

typedef struct {
    unsigned id;
    pid_t pgid;
    char *text;
    pid_t *pids;
    msh_process_state *process_states;
    size_t process_count;
    int last_wait_status;
} msh_job;

typedef struct {
    msh_job *items;
    size_t count;
    size_t capacity;
    unsigned next_id;
} msh_job_table;

void msh_jobs_init(msh_job_table *table);
void msh_jobs_destroy(msh_job_table *table);
int msh_jobs_add(msh_job_table *table, pid_t pgid, const pid_t *pids,
                 size_t process_count, const char *text);
void msh_jobs_note_status(msh_job_table *table, pid_t pid, int wait_status);
void msh_jobs_reap(msh_job_table *table);
void msh_jobs_print(msh_job_table *table, FILE *stream);
int msh_jobs_wait_all(msh_job_table *table);
size_t msh_jobs_active(const msh_job_table *table);

#endif
