#define _POSIX_C_SOURCE 200809L

#include <stdio.h>
#include <stdlib.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

int main(int argc, char **argv)
{
    pid_t child;
    int status;

    if (argc < 2) {
        fprintf(stderr, "usage: %s PROGRAM [ARG ...]\n", argv[0]);
        return 2;
    }

    child = fork();
    if (child == -1) {
        perror("fork");
        return 1;
    }
    if (child == 0) {
        execvp(argv[1], &argv[1]);
        perror("execvp");
        _exit(127);
    }

    if (waitpid(child, &status, 0) == -1) {
        perror("waitpid");
        return 1;
    }

    if (status != 0) {
        fprintf(stderr, "command failed with status %d\n", status);
    }
    return status;
}

