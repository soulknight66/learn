#include "micaos.h"

void mica_vm_init(mica_vm_t *vm)
{
    size_t frame;
    size_t offset;

    if (vm == NULL) {
        return;
    }
    for (frame = 0u; frame < MICA_PHYSICAL_FRAMES; ++frame) {
        vm->frame_used[frame] = false;
        for (offset = 0u; offset < MICA_PAGE_SIZE; ++offset) {
            vm->frames[frame][offset] = 0u;
        }
    }
}

void mica_vm_space_init(mica_address_space_t *space)
{
    size_t page;

    if (space == NULL) {
        return;
    }
    for (page = 0u; page < MICA_VIRTUAL_PAGES; ++page) {
        space->pages[page].mapped = false;
        space->pages[page].writable = false;
        space->pages[page].frame = 0u;
    }
}

mica_status_t mica_vm_map(mica_vm_t *vm,
                          mica_address_space_t *space,
                          size_t virtual_page,
                          bool writable)
{
    size_t frame;

    (void)writable;
    if (vm == NULL || space == NULL) {
        return MICA_ERR_ARG;
    }
    if (virtual_page >= MICA_VIRTUAL_PAGES) {
        return MICA_ERR_RANGE;
    }
    if (space->pages[virtual_page].mapped) {
        return MICA_ERR_EXISTS;
    }
    for (frame = 0u; frame < MICA_PHYSICAL_FRAMES; ++frame) {
        if (!vm->frame_used[frame]) {
            /* TODO: allocate and zero this frame, then install the mapping. */
            return MICA_ERR_STATE;
        }
    }
    return MICA_ERR_FULL;
}

mica_status_t mica_vm_unmap(mica_vm_t *vm,
                            mica_address_space_t *space,
                            size_t virtual_page)
{
    uint8_t frame;

    if (vm == NULL || space == NULL) {
        return MICA_ERR_ARG;
    }
    if (virtual_page >= MICA_VIRTUAL_PAGES) {
        return MICA_ERR_RANGE;
    }
    if (!space->pages[virtual_page].mapped) {
        return MICA_ERR_NOT_FOUND;
    }
    frame = space->pages[virtual_page].frame;
    if (frame >= MICA_PHYSICAL_FRAMES || !vm->frame_used[frame]) {
        return MICA_ERR_STATE;
    }
    /* TODO: remove the mapping and release its frame. */
    return MICA_ERR_STATE;
}

mica_status_t mica_vm_read_u8(const mica_vm_t *vm,
                              const mica_address_space_t *space,
                              size_t virtual_address,
                              uint8_t *out_value)
{
    size_t page;
    uint8_t frame;

    if (vm == NULL || space == NULL || out_value == NULL) {
        return MICA_ERR_ARG;
    }
    if (virtual_address >= MICA_VIRTUAL_PAGES * MICA_PAGE_SIZE) {
        return MICA_ERR_RANGE;
    }
    page = virtual_address / MICA_PAGE_SIZE;
    if (!space->pages[page].mapped) {
        return MICA_ERR_NOT_FOUND;
    }
    frame = space->pages[page].frame;
    if (frame >= MICA_PHYSICAL_FRAMES || !vm->frame_used[frame]) {
        return MICA_ERR_STATE;
    }
    /* TODO: translate and read the requested byte. */
    return MICA_ERR_STATE;
}

mica_status_t mica_vm_write_u8(mica_vm_t *vm,
                               const mica_address_space_t *space,
                               size_t virtual_address,
                               uint8_t value)
{
    size_t page;
    uint8_t frame;

    (void)value;
    if (vm == NULL || space == NULL) {
        return MICA_ERR_ARG;
    }
    if (virtual_address >= MICA_VIRTUAL_PAGES * MICA_PAGE_SIZE) {
        return MICA_ERR_RANGE;
    }
    page = virtual_address / MICA_PAGE_SIZE;
    if (!space->pages[page].mapped) {
        return MICA_ERR_NOT_FOUND;
    }
    if (!space->pages[page].writable) {
        return MICA_ERR_PERM;
    }
    frame = space->pages[page].frame;
    if (frame >= MICA_PHYSICAL_FRAMES || !vm->frame_used[frame]) {
        return MICA_ERR_STATE;
    }
    /* TODO: translate and write the requested byte. */
    return MICA_ERR_STATE;
}
