#define _POSIX_C_SOURCE 200809L

#include <errno.h>
#include <stdio.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

static void sleep_milliseconds(long milliseconds)
{
    struct timespec delay;
    delay.tv_sec = milliseconds / 1000;
    delay.tv_nsec = (milliseconds % 1000) * 1000000L;
    while (nanosleep(&delay, &delay) < 0 && errno == EINTR)
        ;
}

static int exit_code(int status)
{
    if (WIFEXITED(status))
        return WEXITSTATUS(status);
    if (WIFSIGNALED(status))
        return 128 + WTERMSIG(status);
    return -1;
}

int main(void)
{
    pid_t background = fork();
    if (background < 0) {
        perror("fork background");
        return 1;
    }
    if (background == 0)
        _exit(7);

    pid_t foreground = fork();
    if (foreground < 0) {
        perror("fork foreground");
        return 1;
    }
    if (foreground == 0) {
        sleep_milliseconds(250);
        _exit(42);
    }

    printf("background pid=%ld, foreground pid=%ld\n",
           (long)background, (long)foreground);

    int status;
    pid_t reaped;
    do {
        reaped = waitpid(foreground, &status, 0);
    } while (reaped < 0 && errno == EINTR);
    if (reaped < 0) {
        perror("waitpid foreground");
        return 1;
    }
    printf("foreground result=%d (collected pid=%ld)\n",
           exit_code(status), (long)reaped);

    do {
        reaped = waitpid(background, &status, 0);
    } while (reaped < 0 && errno == EINTR);
    if (reaped < 0) {
        perror("waitpid background");
        return 1;
    }
    return 0;
}
