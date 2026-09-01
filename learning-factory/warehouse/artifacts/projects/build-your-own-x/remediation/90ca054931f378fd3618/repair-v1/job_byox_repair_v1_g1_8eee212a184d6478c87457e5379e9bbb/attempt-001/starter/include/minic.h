#ifndef MINIC_H
#define MINIC_H

#include <stddef.h>
#include <stdint.h>

enum {
    MINIC_OK = 0,
    MINIC_USAGE_ERROR = 64,
    MINIC_SOURCE_ERROR = 65,
    MINIC_INPUT_ERROR = 66,
    MINIC_RUNTIME_ERROR = 70
};

typedef struct {
    char *bytes;
    size_t length;
    const char *path;
} MinicSource;

int minic_load_source(const char *path, MinicSource *out);
void minic_free_source(MinicSource *source);
int minic_run(const MinicSource *source, uint64_t max_steps);

#endif
