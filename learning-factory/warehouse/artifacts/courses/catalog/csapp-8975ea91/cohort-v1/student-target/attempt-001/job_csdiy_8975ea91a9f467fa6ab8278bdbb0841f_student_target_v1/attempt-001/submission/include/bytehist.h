#ifndef BYTEHIST_H
#define BYTEHIST_H

#include <stdbool.h>
#include <stdint.h>

enum { BYTEHIST_BUCKET_COUNT = 256 };

typedef struct ByteHistogram ByteHistogram;

/* Returns a new empty histogram, or NULL when allocation fails. */
ByteHistogram *bytehist_create(void);

/* Releases a histogram returned by bytehist_create. NULL is permitted. */
void bytehist_destroy(ByteHistogram *histogram);

/*
 * Adds occurrences of byte_value. On range failure, returns false and leaves
 * the histogram unchanged. The histogram argument must be non-NULL.
 */
bool bytehist_add(ByteHistogram *histogram,
                  unsigned char byte_value,
                  uint64_t occurrences);

/* The histogram argument to each observer must be non-NULL. */
uint64_t bytehist_total(const ByteHistogram *histogram);
uint64_t bytehist_count(const ByteHistogram *histogram,
                        unsigned char byte_value);

#endif
