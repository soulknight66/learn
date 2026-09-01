#include "minic.h"

#include <inttypes.h>
#include <stdio.h>

int minic_run(const MinicSource *source, uint64_t max_steps) {
    /* TODO: lex, compile, resolve calls, and execute the source. */
    fprintf(stderr,
            "%s:1: interpreter not implemented (budget=%" PRIu64 ", bytes=%zu)\n",
            source->path, max_steps, source->length);
    return MINIC_SOURCE_ERROR;
}
