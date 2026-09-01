#include <stdint.h>

/* TODO: initialize the board and launch tasks on independent stacks. */
void arm_kernel_main(void) {
    for (;;) {
        __asm__ volatile("wfi");
    }
}
