#include "byosh.h"

#include <stdio.h>

int byosh_execute_pipeline(const struct byosh_pipeline *pipeline, int interactive)
{
    /* TODO(milestone 2+): add built-ins, process launch, pipelines, and jobs. */
    (void)pipeline;
    (void)interactive;
    (void)fprintf(stderr,
                  "byosh: execution is not implemented; continue with milestone 2\n");
    return 125;
}
