#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <unistd.h>

pid_t launch_candidate(char *const argv[])
{
    pid_t child = fork();

    if (child < 0) {
        printf("fork failed: %s\n", strerror(errno));
        return -1;
    }
    if (child == 0) {
        execvp(argv[0], argv);
        printf("could not run %s: %s\n", argv[0], strerror(errno));
        exit(1);
    }

    if (setpgid(child, child) < 0) {
        printf("setpgid failed: %s\n", strerror(errno));
    }
    return child;
}
