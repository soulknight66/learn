#define _POSIX_C_SOURCE 200809L

#include <signal.h>
#include <stdlib.h>
#include <sys/wait.h>
#include <unistd.h>

int launch(char *const left[], char *const right[])
{
    int channel[2];
    pid_t first;
    pid_t second;
    int status;

    if (pipe(channel) < 0) {
        return 125;
    }
    first = fork();
    if (first == 0) {
        (void)setpgid(0, 0);
        (void)dup2(channel[1], STDOUT_FILENO);
        (void)close(channel[0]);
        (void)close(channel[1]);
        execvp(left[0], left);
        exit(127);
    }
    second = fork();
    if (second == 0) {
        (void)setpgid(0, first);
        (void)dup2(channel[0], STDIN_FILENO);
        (void)close(channel[0]);
        (void)close(channel[1]);
        execvp(right[0], right);
        exit(127);
    }
    (void)close(channel[0]);
    (void)close(channel[1]);
    (void)waitpid(second, &status, 0);
    return WIFEXITED(status) ? WEXITSTATUS(status) : 125;
}
