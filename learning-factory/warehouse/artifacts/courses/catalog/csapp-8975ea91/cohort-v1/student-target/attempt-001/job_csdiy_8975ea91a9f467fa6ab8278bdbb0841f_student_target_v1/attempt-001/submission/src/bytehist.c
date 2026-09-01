#include "bytehist.h"

#include <stdint.h>
#include <stdlib.h>

struct ByteHistogram {
    uint64_t total;
    uint64_t counts[BYTEHIST_BUCKET_COUNT];
};

ByteHistogram *bytehist_create(void)
{
    return calloc(1, sizeof(ByteHistogram));
}

void bytehist_destroy(ByteHistogram *histogram)
{
    free(histogram);
}

bool bytehist_add(ByteHistogram *histogram,
                  unsigned char byte_value,
                  uint64_t occurrences)
{
    uint64_t current_count;

    if (histogram == NULL) {
        return false;
    }

    current_count = histogram->counts[byte_value];
    if (occurrences > UINT64_MAX - histogram->total ||
        occurrences > UINT64_MAX - current_count) {
        return false;
    }

    histogram->total += occurrences;
    histogram->counts[byte_value] = current_count + occurrences;
    return true;
}

uint64_t bytehist_total(const ByteHistogram *histogram)
{
    return histogram->total;
}

uint64_t bytehist_count(const ByteHistogram *histogram,
                        unsigned char byte_value)
{
    return histogram->counts[byte_value];
}
