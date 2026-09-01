#ifndef KEYSTROKE_KERNEL_REFERENCE_TEST_H
#define KEYSTROKE_KERNEL_REFERENCE_TEST_H

#include <stdio.h>

extern unsigned int test_checks;
extern unsigned int test_failures;

#define CHECK(condition)                                                        \
    do {                                                                        \
        ++test_checks;                                                          \
        if (!(condition)) {                                                     \
            fprintf(stderr, "%s:%d: check failed: %s\n",                      \
                    __FILE__, __LINE__, #condition);                            \
            ++test_failures;                                                    \
        }                                                                       \
    } while (0)

#endif
