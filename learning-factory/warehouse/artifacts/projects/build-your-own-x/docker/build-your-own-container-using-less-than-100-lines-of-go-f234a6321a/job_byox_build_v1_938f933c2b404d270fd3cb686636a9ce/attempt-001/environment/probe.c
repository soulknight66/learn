#define _GNU_SOURCE

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/statfs.h>
#include <sys/types.h>
#include <unistd.h>

#ifndef PROC_SUPER_MAGIC
#define PROC_SUPER_MAGIC 0x9fa0
#endif

int main(int argc, char **argv) {
    char hostname[256] = {0};
    struct statfs proc_info;
    const char *check;

    if (gethostname(hostname, sizeof(hostname) - 1) != 0) {
        perror("gethostname");
        return 70;
    }
    printf("hostname=%s\n", hostname);
    printf("pid=%ld\n", (long)getpid());
    if (statfs("/proc", &proc_info) == 0 && (unsigned long)proc_info.f_type == PROC_SUPER_MAGIC) {
        puts("proc=mounted");
    } else {
        puts("proc=missing");
    }
    check = getenv("CHECK");
    if (check != NULL) {
        printf("CHECK=%s\n", check);
    }
    fflush(stdout);

    if (argc == 3 && strcmp(argv[1], "--exit") == 0) {
        char *end = NULL;
        long code;
        errno = 0;
        code = strtol(argv[2], &end, 10);
        if (errno != 0 || end == argv[2] || *end != '\0' || code < 0 || code > 255) {
            fputs("invalid exit status\n", stderr);
            return 64;
        }
        return (int)code;
    }
    if (argc != 1) {
        fputs("usage: probe [--exit 0..255]\n", stderr);
        return 64;
    }
    return 0;
}
