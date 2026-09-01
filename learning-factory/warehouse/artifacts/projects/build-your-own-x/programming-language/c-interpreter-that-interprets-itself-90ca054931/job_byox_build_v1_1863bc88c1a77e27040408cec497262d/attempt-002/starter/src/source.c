#include "minic.h"

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>

#define MAX_SOURCE_BYTES ((size_t)1048576)

int minic_load_source(const char *path, MinicSource *out) {
    FILE *file = fopen(path, "rb");
    long length;
    size_t received;
    char *bytes;

    if (file == NULL) {
        fprintf(stderr, "%s: cannot open input (error %d)\n", path, errno);
        return MINIC_INPUT_ERROR;
    }
    if (fseek(file, 0, SEEK_END) != 0 || (length = ftell(file)) < 0 ||
        fseek(file, 0, SEEK_SET) != 0) {
        fprintf(stderr, "%s: cannot measure input\n", path);
        fclose(file);
        return MINIC_INPUT_ERROR;
    }
    if ((unsigned long)length > (unsigned long)MAX_SOURCE_BYTES) {
        fprintf(stderr, "%s: input exceeds %zu bytes\n", path, MAX_SOURCE_BYTES);
        fclose(file);
        return MINIC_INPUT_ERROR;
    }
    bytes = (char *)malloc((size_t)length + 1);
    if (bytes == NULL) {
        fprintf(stderr, "%s: cannot allocate input buffer\n", path);
        fclose(file);
        return MINIC_INPUT_ERROR;
    }
    received = fread(bytes, 1, (size_t)length, file);
    if (received != (size_t)length || ferror(file)) {
        fprintf(stderr, "%s: cannot read input\n", path);
        free(bytes);
        fclose(file);
        return MINIC_INPUT_ERROR;
    }
    bytes[received] = '\0';
    fclose(file);
    out->bytes = bytes;
    out->length = received;
    out->path = path;
    return MINIC_OK;
}

void minic_free_source(MinicSource *source) {
    free(source->bytes);
    source->bytes = NULL;
    source->length = 0;
}
