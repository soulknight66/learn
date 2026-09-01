#include "micaos.h"

static void zero_frame(mica_vm_t *vm, size_t frame)
{
    size_t offset;

    for (offset = 0u; offset < MICA_PAGE_SIZE; offset++) {
        vm->frames[frame][offset] = 0u;
    }
}

static mica_status_t resolve_address(const mica_vm_t *vm,
                                     const mica_address_space_t *space,
                                     size_t virtual_address,
                                     size_t *out_frame,
                                     size_t *out_offset)
{
    size_t virtual_page;
    const mica_page_entry_t *entry;

    if (virtual_address >= MICA_VIRTUAL_PAGES * MICA_PAGE_SIZE) {
        return MICA_ERR_RANGE;
    }
    virtual_page = virtual_address / MICA_PAGE_SIZE;
    entry = &space->pages[virtual_page];
    if (!entry->mapped) {
        return MICA_ERR_NOT_FOUND;
    }
    if ((size_t)entry->frame >= MICA_PHYSICAL_FRAMES ||
        !vm->frame_used[entry->frame]) {
        return MICA_ERR_STATE;
    }
    *out_frame = entry->frame;
    *out_offset = virtual_address % MICA_PAGE_SIZE;
    return MICA_OK;
}

void mica_vm_init(mica_vm_t *vm)
{
    size_t frame;

    if (vm == NULL) {
        return;
    }
    for (frame = 0u; frame < MICA_PHYSICAL_FRAMES; frame++) {
        vm->frame_used[frame] = false;
        zero_frame(vm, frame);
    }
}

void mica_vm_space_init(mica_address_space_t *space)
{
    size_t page;

    if (space == NULL) {
        return;
    }
    for (page = 0u; page < MICA_VIRTUAL_PAGES; page++) {
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

    if (vm == NULL || space == NULL) {
        return MICA_ERR_ARG;
    }
    if (virtual_page >= MICA_VIRTUAL_PAGES) {
        return MICA_ERR_RANGE;
    }
    if (space->pages[virtual_page].mapped) {
        return MICA_ERR_EXISTS;
    }
    for (frame = 0u; frame < MICA_PHYSICAL_FRAMES; frame++) {
        if (!vm->frame_used[frame]) {
            break;
        }
    }
    if (frame == MICA_PHYSICAL_FRAMES) {
        return MICA_ERR_FULL;
    }

    zero_frame(vm, frame);
    vm->frame_used[frame] = true;
    space->pages[virtual_page].frame = (uint8_t)frame;
    space->pages[virtual_page].writable = writable;
    space->pages[virtual_page].mapped = true;
    return MICA_OK;
}

mica_status_t mica_vm_unmap(mica_vm_t *vm,
                            mica_address_space_t *space,
                            size_t virtual_page)
{
    mica_page_entry_t *entry;
    size_t frame;

    if (vm == NULL || space == NULL) {
        return MICA_ERR_ARG;
    }
    if (virtual_page >= MICA_VIRTUAL_PAGES) {
        return MICA_ERR_RANGE;
    }
    entry = &space->pages[virtual_page];
    if (!entry->mapped) {
        return MICA_ERR_NOT_FOUND;
    }
    frame = entry->frame;
    if (frame >= MICA_PHYSICAL_FRAMES || !vm->frame_used[frame]) {
        return MICA_ERR_STATE;
    }

    zero_frame(vm, frame);
    vm->frame_used[frame] = false;
    entry->mapped = false;
    entry->writable = false;
    entry->frame = 0u;
    return MICA_OK;
}

mica_status_t mica_vm_read_u8(const mica_vm_t *vm,
                              const mica_address_space_t *space,
                              size_t virtual_address,
                              uint8_t *out_value)
{
    size_t frame;
    size_t offset;
    mica_status_t status;

    if (vm == NULL || space == NULL || out_value == NULL) {
        return MICA_ERR_ARG;
    }
    status = resolve_address(vm, space, virtual_address, &frame, &offset);
    if (status != MICA_OK) {
        return status;
    }
    *out_value = vm->frames[frame][offset];
    return MICA_OK;
}

mica_status_t mica_vm_write_u8(mica_vm_t *vm,
                               const mica_address_space_t *space,
                               size_t virtual_address,
                               uint8_t value)
{
    size_t frame;
    size_t offset;
    size_t virtual_page;
    mica_status_t status;

    if (vm == NULL || space == NULL) {
        return MICA_ERR_ARG;
    }
    status = resolve_address(vm, space, virtual_address, &frame, &offset);
    if (status != MICA_OK) {
        return status;
    }
    virtual_page = virtual_address / MICA_PAGE_SIZE;
    if (!space->pages[virtual_page].writable) {
        return MICA_ERR_PERM;
    }
    vm->frames[frame][offset] = value;
    return MICA_OK;
}
