#define _POSIX_C_SOURCE 200809L

#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

struct job {
    pid_t pid;
    int live;
};

static struct job jobs[1];

static void child_changed(int signal_number)
{
    pid_t pid;
    int status;

    (void)signal_number;
    while ((pid = waitpid(-1, &status, WNOHANG)) > 0) {
        if (jobs[0].pid == pid) {
            jobs[0].live = 0;
        }
        printf("reaped child %ld\n", (long)pid);
    }
}

int main(void)
{
    struct sigaction action;
    struct timespec widen_window = {0, 20000000L};
    pid_t child;

    action.sa_handler = child_changed;
    sigemptyset(&action.sa_mask);
    action.sa_flags = SA_RESTART | SA_NOCLDSTOP;
    if (sigaction(SIGCHLD, &action, NULL) == -1) {
        perror("sigaction");
        return 1;
    }

    child = fork();
    if (child == -1) {
        perror("fork");
        return 1;
    }
    if (child == 0) {
        _exit(0);
    }

    nanosleep(&widen_window, NULL);
    jobs[0].pid = child;
    jobs[0].live = 1;

    while (jobs[0].live) {
        pause();
    }
    return 0;
}

