#include "msh.h"

#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>

#define CHECK(condition)                                                        \
    do {                                                                        \
        if (!(condition)) {                                                     \
            (void)fprintf(stderr, "CHECK failed at %s:%d: %s\n",             \
                          __FILE__, __LINE__, #condition);                       \
            exit(1);                                                            \
        }                                                                       \
    } while (0)

static int encoded_exit(int status)
{
    return status << 8;
}

static int encoded_stop(int signal_number)
{
    return (signal_number << 8) | 0x7f;
}

static void test_lifecycle_and_last_status(void)
{
    msh_job_table table;
    const pid_t first_pids[] = {101, 102};
    const pid_t second_pids[] = {201};

    msh_jobs_init(&table);
    CHECK(table.next_id == 1);
    CHECK(msh_jobs_add(&table, 101, first_pids, 2, "first | second") == 1);
    CHECK(msh_jobs_active(&table) == 1);
    msh_jobs_note_status(&table, 101, encoded_exit(3));
    CHECK(msh_jobs_active(&table) == 1);
    msh_jobs_note_status(&table, 102, encoded_exit(9));
    CHECK(msh_jobs_active(&table) == 0);
    CHECK(msh_jobs_wait_all(&table) == 9);
    CHECK(table.count == 0);

    CHECK(msh_jobs_add(&table, 201, second_pids, 1, "third") == 2);
    msh_jobs_note_status(&table, 201, encoded_exit(0));
    CHECK(msh_jobs_wait_all(&table) == 0);
    CHECK(table.count == 0);
    msh_jobs_destroy(&table);
}

static void test_stopped_state_is_retained(void)
{
    msh_job_table table;
    const pid_t pids[] = {301};
    FILE *capture;
    char *output = NULL;
    size_t bytes = 0;

    msh_jobs_init(&table);
    CHECK(msh_jobs_add(&table, 301, pids, 1, "stopped-command") == 1);
    msh_jobs_note_status(&table, 301, encoded_stop(SIGTSTP));
    CHECK(msh_jobs_active(&table) == 1);

    capture = open_memstream(&output, &bytes);
    CHECK(capture != NULL);
    msh_jobs_print(&table, capture);
    CHECK(fclose(capture) == 0);
    CHECK(bytes > 0);
    CHECK(strstr(output, "[1] Stopped 301 stopped-command") != NULL);
    free(output);
    msh_jobs_destroy(&table);
}

static void test_invalid_add_is_atomic(void)
{
    msh_job_table table;

    msh_jobs_init(&table);
    CHECK(msh_jobs_add(&table, 1, NULL, 0, "bad") == -1);
    CHECK(table.count == 0);
    CHECK(table.next_id == 1);
    msh_jobs_destroy(&table);
}

int main(void)
{
    test_lifecycle_and_last_status();
    test_stopped_state_is_retained();
    test_invalid_add_is_atomic();
    (void)puts("jobs_tests: 3 cases passed");
    return 0;
}
