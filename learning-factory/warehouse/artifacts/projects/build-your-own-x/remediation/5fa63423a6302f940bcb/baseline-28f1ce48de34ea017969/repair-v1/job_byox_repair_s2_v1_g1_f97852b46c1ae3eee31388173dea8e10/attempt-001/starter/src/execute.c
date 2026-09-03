#include "minish.h"

#include <errno.h>
#include <stdio.h>

int execute_pipeline(const Pipeline *pipeline, const ShellContext *context)
{
    (void)pipeline;
    (void)context;
    errno = ENOSYS;
    (void)fprintf(stderr, "minish: execution is not implemented\n");

    /* TODO: create pipes, children, a process group, and wait/reap safely. */
    return 125;
}

size_t shell_reap_background(void)
{
    /* TODO: use waitpid with WNOHANG and account for stopped children. */
    return 0;
}
