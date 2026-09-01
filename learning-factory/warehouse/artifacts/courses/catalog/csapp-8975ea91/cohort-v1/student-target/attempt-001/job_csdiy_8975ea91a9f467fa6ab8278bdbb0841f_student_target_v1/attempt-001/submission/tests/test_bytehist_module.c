#include "bytehist.h"

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#define CHECK(condition)                                                       \
    do {                                                                       \
        if (!(condition)) {                                                    \
            (void)fprintf(stderr, "module check failed at line %d: %s\n",    \
                          __LINE__, #condition);                               \
            bytehist_destroy(histogram);                                      \
            return EXIT_FAILURE;                                              \
        }                                                                      \
    } while (0)

int main(void)
{
    ByteHistogram *histogram = bytehist_create();

    if (histogram == NULL) {
        (void)fputs("module check could not allocate a histogram\n", stderr);
        return EXIT_FAILURE;
    }

    CHECK(bytehist_total(histogram) == UINT64_C(0));
    CHECK(bytehist_count(histogram, (unsigned char)0x41) == UINT64_C(0));
    CHECK(bytehist_add(histogram, (unsigned char)0x41, UINT64_C(2)));
    CHECK(bytehist_add(histogram, (unsigned char)0x42, UINT64_C(3)));
    CHECK(bytehist_total(histogram) == UINT64_C(5));
    CHECK(bytehist_count(histogram, (unsigned char)0x41) == UINT64_C(2));
    CHECK(bytehist_count(histogram, (unsigned char)0x42) == UINT64_C(3));

    bytehist_destroy(histogram);
    histogram = bytehist_create();
    if (histogram == NULL) {
        (void)fputs("module check could not allocate a histogram\n", stderr);
        return EXIT_FAILURE;
    }

    CHECK(bytehist_add(histogram, (unsigned char)0xFF, UINT64_MAX));
    CHECK(bytehist_total(histogram) == UINT64_MAX);
    CHECK(bytehist_count(histogram, (unsigned char)0xFF) == UINT64_MAX);
    CHECK(!bytehist_add(histogram, (unsigned char)0x00, UINT64_C(1)));
    CHECK(!bytehist_add(histogram, (unsigned char)0xFF, UINT64_C(1)));
    CHECK(bytehist_total(histogram) == UINT64_MAX);
    CHECK(bytehist_count(histogram, (unsigned char)0x00) == UINT64_C(0));
    CHECK(bytehist_count(histogram, (unsigned char)0xFF) == UINT64_MAX);

    bytehist_destroy(histogram);
    (void)puts("bytehist module checks passed");
    return EXIT_SUCCESS;
}
