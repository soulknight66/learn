#include <stddef.h>

int main(void) {
    volatile size_t value = 1U;
    return value == 1U ? 0 : 1;
}
