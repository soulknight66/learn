#include "kernel/mmu.h"
#include "kernel/uart.h"

int kernel_main(void) {
    /* Bring up one observable stage at a time. The final marker order is
     * normative in REQUIREMENTS.md. */
    lf_uart_puts("LF-KERNEL boot\n");
    if (!lf_mmu_enable_identity()) {
        return 1;
    }
    return 0;
}
