#include <stdint.h>
#include <stdio.h>

size_t proposed_round_request(size_t bytes, size_t alignment);

int main(void) {
    size_t rounded = proposed_round_request(SIZE_MAX, 16U);
    if (rounded != 0U) {
        fputs("fixture assumption changed\n", stderr);
        return 1;
    }
    puts("reproduced request-size overflow: SIZE_MAX rounded down to zero");
    return 0;
}
