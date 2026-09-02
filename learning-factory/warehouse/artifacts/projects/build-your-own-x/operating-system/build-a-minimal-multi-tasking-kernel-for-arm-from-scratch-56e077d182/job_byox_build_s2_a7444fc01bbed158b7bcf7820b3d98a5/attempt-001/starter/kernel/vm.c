#include "kernel/vm.h"

#include <stddef.h>

/* Stage 3: implement frame ownership and mapping operations. These stubs make
 * no allocation or mapping appear successful. */
bool lf_frame_pool_init(lf_frame_pool_t *pool, uint32_t base, uint32_t count) {
    (void)pool;
    (void)base;
    (void)count;
    return false;
}

uint32_t lf_frame_alloc(lf_frame_pool_t *pool) {
    (void)pool;
    return LF_INVALID_PADDR;
}

bool lf_frame_retain(lf_frame_pool_t *pool, uint32_t physical_address) {
    (void)pool;
    (void)physical_address;
    return false;
}

bool lf_frame_release(lf_frame_pool_t *pool, uint32_t physical_address) {
    (void)pool;
    (void)physical_address;
    return false;
}

uint16_t lf_frame_refcount(const lf_frame_pool_t *pool,
                           uint32_t physical_address) {
    (void)pool;
    (void)physical_address;
    return 0u;
}

void lf_vm_space_init(lf_vm_space_t *space) {
    uint32_t slot;
    if (space == (lf_vm_space_t *)0) {
        return;
    }
    for (slot = 0u; slot < LF_MAX_MAPPINGS; ++slot) {
        space->mappings[slot].used = false;
        space->mappings[slot].virtual_base = 0u;
        space->mappings[slot].physical_base = 0u;
        space->mappings[slot].flags = 0u;
    }
}

bool lf_vm_map(lf_vm_space_t *space, uint32_t virtual_base,
               uint32_t physical_base, uint8_t flags) {
    (void)space;
    (void)virtual_base;
    (void)physical_base;
    (void)flags;
    return false;
}

bool lf_vm_unmap(lf_vm_space_t *space, uint32_t virtual_base) {
    (void)space;
    (void)virtual_base;
    return false;
}

bool lf_vm_translate(const lf_vm_space_t *space, uint32_t virtual_address,
                     uint8_t requested_access, uint32_t *physical_address) {
    (void)space;
    (void)virtual_address;
    (void)requested_access;
    (void)physical_address;
    return false;
}
