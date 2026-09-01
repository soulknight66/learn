#include "bytehist.h"

#include <inttypes.h>
#include <signal.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>

enum { INPUT_CHUNK_SIZE = 4096 };

typedef enum {
    READ_OK,
    READ_STREAM_ERROR,
    READ_COUNT_OVERFLOW
} ReadStatus;

static int report_failure(const char *message)
{
    (void)fprintf(stderr, "bytehist: %s\n", message);
    return 1;
}

static ReadStatus read_input(FILE *input, ByteHistogram *histogram)
{
    unsigned char buffer[INPUT_CHUNK_SIZE];

    for (;;) {
        size_t bytes_read = fread(buffer, 1, sizeof(buffer), input);
        size_t index;

        for (index = 0; index < bytes_read; ++index) {
            if (!bytehist_add(histogram, buffer[index], UINT64_C(1))) {
                return READ_COUNT_OVERFLOW;
            }
        }

        if (ferror(input)) {
            return READ_STREAM_ERROR;
        }
        if (feof(input)) {
            return READ_OK;
        }
        if (bytes_read == 0) {
            /* A nonempty request made no progress and set no stream state. */
            return READ_STREAM_ERROR;
        }
        /* A short read with progress and no terminal state is not an error. */
    }
}

static bool emit_report(const ByteHistogram *histogram)
{
    unsigned int value;

    if (fprintf(stdout, "total %" PRIu64 "\n",
                bytehist_total(histogram)) < 0) {
        return false;
    }

    for (value = 0; value < BYTEHIST_BUCKET_COUNT; ++value) {
        uint64_t count = bytehist_count(histogram, (unsigned char)value);

        if (count != 0 &&
            fprintf(stdout, "%02X %" PRIu64 "\n", value, count) < 0) {
            return false;
        }
    }

    return fflush(stdout) != EOF;
}

int main(int argc, char **argv)
{
    ByteHistogram *histogram;
    FILE *input = stdin;
    bool owns_input = false;
    ReadStatus read_status;
    bool close_failed = false;

    if (argc > 2) {
        (void)fputs("usage: bytehist [INPUT]\n", stderr);
        return 2;
    }

#ifdef SIGPIPE
    /* Convert a closed output pipe into a checked stdio failure. */
    if (signal(SIGPIPE, SIG_IGN) == SIG_ERR) {
        return report_failure("cannot configure output handling");
    }
#endif

    histogram = bytehist_create();
    if (histogram == NULL) {
        return report_failure("cannot initialize histogram");
    }

    if (argc == 2) {
        input = fopen(argv[1], "rb");
        if (input == NULL) {
            bytehist_destroy(histogram);
            return report_failure("cannot open input");
        }
        owns_input = true;
    }

    read_status = read_input(input, histogram);
    if (owns_input && fclose(input) != 0) {
        close_failed = true;
    }

    if (read_status == READ_STREAM_ERROR) {
        bytehist_destroy(histogram);
        return report_failure("input read failed");
    }
    if (read_status == READ_COUNT_OVERFLOW) {
        bytehist_destroy(histogram);
        return report_failure("count overflow");
    }
    if (close_failed) {
        bytehist_destroy(histogram);
        return report_failure("input close failed");
    }

    if (!emit_report(histogram)) {
        bytehist_destroy(histogram);
        return report_failure("output failed");
    }

    bytehist_destroy(histogram);
    return 0;
}
