#include <stdio.h>

#include "cairn.h"

int main(void)
{
    struct cairn_kernel kernel;
    int pid = -1;
    int status;

    cairn_init(&kernel);
    status = cairn_spawn(&kernel, 0x1000U, &pid);
    if (status == CAIRN_ERR_UNIMPLEMENTED) {
        puts("CairnOS starter built: implementation TODOs remain.");
        return 0;
    }
    if (status != CAIRN_OK) {
        printf("spawn returned unexpected status %d\n", status);
        return 1;
    }
    printf("CairnOS core created pid %d; run the public tests next.\n", pid);
    return 0;
}
