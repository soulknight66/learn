#define _POSIX_C_SOURCE 200809L

#include <stdio.h>
#include <stdlib.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

static void fail_child(const char *operation)
{
    perror(operation);
    _exit(127);
}

int main(void)
{
    int channel[2];
    pid_t producer;
    pid_t consumer;
    int status;

    if (pipe(channel) == -1) {
        perror("pipe");
        return 1;
    }

    producer = fork();
    if (producer == -1) {
        perror("fork producer");
        return 1;
    }
    if (producer == 0) {
        close(channel[0]);
        if (dup2(channel[1], STDOUT_FILENO) == -1) {
            fail_child("dup2 producer");
        }
        close(channel[1]);
        execlp("printf", "printf", "payload\n", (char *)NULL);
        fail_child("exec printf");
    }

    consumer = fork();
    if (consumer == -1) {
        perror("fork consumer");
        return 1;
    }
    if (consumer == 0) {
        close(channel[1]);
        if (dup2(channel[0], STDIN_FILENO) == -1) {
            fail_child("dup2 consumer");
        }
        close(channel[0]);
        execlp("cat", "cat", (char *)NULL);
        fail_child("exec cat");
    }

    close(channel[0]);

    if (waitpid(producer, &status, 0) == -1) {
        perror("wait producer");
        return 1;
    }
    if (waitpid(consumer, &status, 0) == -1) {
        perror("wait consumer");
        return 1;
    }
    return 0;
}
