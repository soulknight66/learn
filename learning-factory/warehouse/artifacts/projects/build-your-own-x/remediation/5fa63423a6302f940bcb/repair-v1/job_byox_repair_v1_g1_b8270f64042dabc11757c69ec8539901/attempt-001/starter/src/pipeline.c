#include "byosh.h"

#include <string.h>

void byosh_pipeline_init(struct byosh_pipeline *pipeline)
{
    if (pipeline != NULL) {
        (void)memset(pipeline, 0, sizeof(*pipeline));
    }
}
