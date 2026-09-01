#ifndef KEYSTROKE_KERNEL_TEST_COMMON_H
#define KEYSTROKE_KERNEL_TEST_COMMON_H

#include <stdio.h>

extern unsigned int test_failures;

#define CHECK(condition)                                                        \
    do {                                                                        \
        if (!(condition)) {                                                     \
            fprintf(stderr, "%s:%d: check failed: %s\n",                      \
                    __FILE__, __LINE__, #condition);                            \
            ++test_failures;                                                    \
        }                                                                       \
    } while (0)

#endif
