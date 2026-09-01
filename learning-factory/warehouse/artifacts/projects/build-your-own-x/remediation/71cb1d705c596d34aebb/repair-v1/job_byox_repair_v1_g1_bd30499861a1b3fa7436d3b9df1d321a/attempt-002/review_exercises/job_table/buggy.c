#define _POSIX_C_SOURCE 200809L

#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

enum job_state {
    JOB_RUNNING,
    JOB_STOPPED
};

struct job {
    pid_t pid;
    enum job_state state;
    char *description;
};

static struct job jobs[8];
static volatile sig_atomic_t job_count;

static void child_changed(int signal_number)
{
    (void)signal_number;
    int status;
    pid_t pid = waitpid(-1, &status, WNOHANG | WUNTRACED | WCONTINUED);
    if (pid <= 0)
        return;

    for (sig_atomic_t index = 0; index < job_count; ++index) {
        if (jobs[index].pid != pid)
            continue;
        if (WIFSTOPPED(status)) {
            jobs[index].state = JOB_STOPPED;
        } else if (WIFCONTINUED(status)) {
            jobs[index].state = JOB_RUNNING;
        } else {
            printf("completed: %s\n", jobs[index].description);
            free(jobs[index].description);
            jobs[index] = jobs[job_count - 1];
            --job_count;
        }
        break;
    }
}

static void launch_short_job(int number)
{
    pid_t child = fork();
    if (child == 0)
        _exit(number & 1);

    char label[32];
    snprintf(label, sizeof(label), "job-%d", number);
    jobs[job_count].pid = child;
    jobs[job_count].state = JOB_RUNNING;
    jobs[job_count].description = strdup(label);
    ++job_count;
}

int main(void)
{
    signal(SIGCHLD, child_changed);

    for (int index = 0; index < 8; ++index)
        launch_short_job(index);

    while (job_count > 0)
        pause();
    return 0;
}
