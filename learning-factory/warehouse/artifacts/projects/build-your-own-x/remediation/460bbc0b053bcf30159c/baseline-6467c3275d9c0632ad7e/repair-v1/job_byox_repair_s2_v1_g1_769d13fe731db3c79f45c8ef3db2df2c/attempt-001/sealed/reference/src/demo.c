#include <stdio.h>

#include "cairn.h"

int main(void)
{
    struct cairn_kernel kernel;
    const char message[] = "scheduler + pages + files";
    char result[sizeof(message)] = {0};
    cairn_size transferred = 0U;
    int pid;
    int fd;
    int running;

    cairn_init(&kernel);
    if (cairn_spawn(&kernel, 0x1000U, &pid) != CAIRN_OK ||
        cairn_schedule(&kernel, &running) != CAIRN_OK || running != pid ||
        cairn_map(&kernel, pid, 0x4000U, 3U, 1) != CAIRN_OK ||
        cairn_create(&kernel, "boot.log") != CAIRN_OK ||
        cairn_open(&kernel, pid, "boot.log", &fd) != CAIRN_OK ||
        cairn_write(&kernel, pid, fd, message, sizeof(message), &transferred) != CAIRN_OK ||
        transferred != sizeof(message) || cairn_seek(&kernel, pid, fd, 0U) != CAIRN_OK ||
        cairn_read(&kernel, pid, fd, result, sizeof(result), &transferred) != CAIRN_OK ||
        transferred != sizeof(result) || cairn_validate(&kernel) != CAIRN_OK) {
        fputs("CairnOS reference demo failed\n", stderr);
        return 1;
    }
    printf("CairnOS reference demo: pid=%d file=%s\n", pid, result);
    return 0;
}
