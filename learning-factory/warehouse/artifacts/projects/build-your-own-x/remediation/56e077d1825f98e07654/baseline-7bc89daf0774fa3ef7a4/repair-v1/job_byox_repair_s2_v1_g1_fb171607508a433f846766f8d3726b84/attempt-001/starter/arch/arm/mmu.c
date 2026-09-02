#include "kernel/mmu.h"

/* Stage 3 (ARM half): create aligned descriptors and enable CP15 translation
 * only after all executing code, data, stack, and UART addresses are mapped. */
bool lf_mmu_enable_identity(void) {
    return false;
}
