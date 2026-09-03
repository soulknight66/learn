#include <stdio.h>
#include <string.h>
#include <unistd.h>

int main(int argc, char **argv)
{
    long expected;

    if (argc != 2) {
        return 2;
    }
    if (strcmp(argv[1], "emit-pgid") == 0) {
        (void)printf("%ld\n", (long)getpgrp());
        return 0;
    }
    if (strcmp(argv[1], "check-pgid") == 0) {
        if (scanf("%ld", &expected) != 1) {
            return 3;
        }
        return expected == (long)getpgrp() ? 0 : 4;
    }
    return 2;
}
