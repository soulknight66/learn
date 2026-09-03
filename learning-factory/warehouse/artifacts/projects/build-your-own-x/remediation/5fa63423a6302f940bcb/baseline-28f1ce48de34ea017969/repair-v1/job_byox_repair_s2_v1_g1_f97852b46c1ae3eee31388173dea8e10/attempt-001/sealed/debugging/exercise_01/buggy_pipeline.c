#define _POSIX_C_SOURCE 200809L

#include <stdlib.h>
#include <sys/wait.h>
#include <unistd.h>

int main(void)
{
    int channel[2];
    pid_t producer;
    pid_t consumer;
    int status;

    if (pipe(channel) < 0) {
        return 1;
    }
    producer = fork();
    if (producer == 0) {
        (void)dup2(channel[1], STDOUT_FILENO);
        (void)close(channel[0]);
        (void)close(channel[1]);
        execl("/usr/bin/printf", "printf", "payload", (char *)NULL);
        _exit(127);
    }
    consumer = fork();
    if (consumer == 0) {
        (void)dup2(channel[0], STDIN_FILENO);
        (void)close(channel[0]);
        (void)close(channel[1]);
        execl("/bin/cat", "cat", (char *)NULL);
        _exit(127);
    }

    (void)close(channel[0]);
    /* One inherited reference is intentionally left open here. */
    (void)waitpid(producer, &status, 0);
    (void)waitpid(consumer, &status, 0);
    return EXIT_SUCCESS;
}
