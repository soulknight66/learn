#include <stdio.h>
#include <time.h>
#include <unistd.h>

int main(int argc, char **argv)
{
    const char *label = argc > 1 ? argv[1] : "probe";
    const struct timespec pause_time = {0, 50000000L};

    (void)fprintf(stderr, "PG_PROBE %s %ld %ld\n", label,
                  (long)getpid(), (long)getpgrp());
    (void)fflush(stderr);
    (void)nanosleep(&pause_time, NULL);
    return 0;
}
