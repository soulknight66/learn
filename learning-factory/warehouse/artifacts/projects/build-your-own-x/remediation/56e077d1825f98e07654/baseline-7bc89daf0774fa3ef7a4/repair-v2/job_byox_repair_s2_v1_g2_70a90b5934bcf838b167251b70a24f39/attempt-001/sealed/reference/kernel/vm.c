#include "kernel/vm.h"

#include <stddef.h>

static void clear_object(void *object, size_t size) {
    uint8_t *byte = (uint8_t *)object;
    size_t index;

    for (index = 0u; index < size; ++index) {
        byte[index] = 0u;
    }
}

static bool pool_index(const lf_frame_pool_t *pool, uint32_t address,
                       uint32_t *index) {
    uint32_t delta;

    if (pool == (const lf_frame_pool_t *)0 || !pool->initialized ||
        (address & (LF_PAGE_SIZE - 1u)) != 0u || address < pool->base) {
        return false;
    }
    delta = address - pool->base;
    if ((delta / LF_PAGE_SIZE) >= pool->count) {
        return false;
    }
    *index = delta / LF_PAGE_SIZE;
    return true;
}

bool lf_frame_pool_init(lf_frame_pool_t *pool, uint32_t base,
                        uint32_t count) {
    uint64_t end;

    if (pool == (lf_frame_pool_t *)0 || count == 0u || count > LF_MAX_FRAMES ||
        (base & (LF_PAGE_SIZE - 1u)) != 0u) {
        return false;
    }
    end = (uint64_t)base + (uint64_t)count * (uint64_t)LF_PAGE_SIZE;
    if (end > (UINT64_C(1) << 32)) {
        return false;
    }
    clear_object(pool, sizeof(*pool));
    pool->base = base;
    pool->count = count;
    pool->initialized = true;
    return true;
}

uint32_t lf_frame_alloc(lf_frame_pool_t *pool) {
    uint32_t frame;

    if (pool == (lf_frame_pool_t *)0 || !pool->initialized) {
        return LF_INVALID_PADDR;
    }
    for (frame = 0u; frame < pool->count; ++frame) {
        if (pool->references[frame] == 0u) {
            pool->references[frame] = 1u;
            return pool->base + frame * LF_PAGE_SIZE;
        }
    }
    return LF_INVALID_PADDR;
}

bool lf_frame_retain(lf_frame_pool_t *pool, uint32_t physical_address) {
    uint32_t frame;

    if (!pool_index(pool, physical_address, &frame) ||
        pool->references[frame] == 0u || pool->references[frame] == UINT16_MAX) {
        return false;
    }
    ++pool->references[frame];
    return true;
}

bool lf_frame_release(lf_frame_pool_t *pool, uint32_t physical_address) {
    uint32_t frame;

    if (!pool_index(pool, physical_address, &frame) ||
        pool->references[frame] == 0u) {
        return false;
    }
    --pool->references[frame];
    return true;
}

uint16_t lf_frame_refcount(const lf_frame_pool_t *pool,
                           uint32_t physical_address) {
    uint32_t frame;

    if (!pool_index(pool, physical_address, &frame)) {
        return 0u;
    }
    return pool->references[frame];
}

void lf_vm_space_init(lf_vm_space_t *space) {
    if (space == (lf_vm_space_t *)0) {
        return;
    }
    clear_object(space, sizeof(*space));
}

bool lf_vm_map(lf_vm_space_t *space, uint32_t virtual_base,
               uint32_t physical_base, uint8_t flags) {
    uint32_t slot;
    uint32_t free_slot = LF_MAX_MAPPINGS;

    if (space == (lf_vm_space_t *)0 ||
        (virtual_base & (LF_PAGE_SIZE - 1u)) != 0u ||
        (physical_base & (LF_PAGE_SIZE - 1u)) != 0u || flags == 0u ||
        (flags & (uint8_t)~LF_VM_ALL) != 0u) {
        return false;
    }
    for (slot = 0u; slot < LF_MAX_MAPPINGS; ++slot) {
        if (space->mappings[slot].used) {
            if (space->mappings[slot].virtual_base == virtual_base) {
                return false;
            }
        } else if (free_slot == LF_MAX_MAPPINGS) {
            free_slot = slot;
        }
    }
    if (free_slot == LF_MAX_MAPPINGS) {
        return false;
    }
    space->mappings[free_slot].virtual_base = virtual_base;
    space->mappings[free_slot].physical_base = physical_base;
    space->mappings[free_slot].flags = flags;
    space->mappings[free_slot].used = true;
    return true;
}

bool lf_vm_unmap(lf_vm_space_t *space, uint32_t virtual_base) {
    uint32_t slot;

    if (space == (lf_vm_space_t *)0 ||
        (virtual_base & (LF_PAGE_SIZE - 1u)) != 0u) {
        return false;
    }
    for (slot = 0u; slot < LF_MAX_MAPPINGS; ++slot) {
        if (space->mappings[slot].used &&
            space->mappings[slot].virtual_base == virtual_base) {
            space->mappings[slot].used = false;
            space->mappings[slot].virtual_base = 0u;
            space->mappings[slot].physical_base = 0u;
            space->mappings[slot].flags = 0u;
            return true;
        }
    }
    return false;
}

bool lf_vm_translate(const lf_vm_space_t *space, uint32_t virtual_address,
                     uint8_t requested_access, uint32_t *physical_address) {
    uint32_t virtual_base;
    uint32_t offset;
    uint32_t slot;

    if (space == (const lf_vm_space_t *)0 ||
        physical_address == (uint32_t *)0 || requested_access == 0u ||
        (requested_access & (uint8_t)~LF_VM_ALL) != 0u) {
        return false;
    }
    virtual_base = virtual_address & ~(LF_PAGE_SIZE - 1u);
    offset = virtual_address & (LF_PAGE_SIZE - 1u);
    for (slot = 0u; slot < LF_MAX_MAPPINGS; ++slot) {
        const lf_vm_mapping_t *mapping = &space->mappings[slot];
        if (mapping->used && mapping->virtual_base == virtual_base) {
            if ((mapping->flags & requested_access) != requested_access ||
                mapping->physical_base > UINT32_MAX - offset) {
                return false;
            }
            *physical_address = mapping->physical_base + offset;
            return true;
        }
    }
    return false;
}
