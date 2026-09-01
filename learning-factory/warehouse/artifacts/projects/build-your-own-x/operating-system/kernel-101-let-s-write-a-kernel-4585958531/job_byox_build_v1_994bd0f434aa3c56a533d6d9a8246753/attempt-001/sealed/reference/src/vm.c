#include "tinykernel.h"

#define TK_VM_ALL_FLAGS (TK_VM_READ | TK_VM_WRITE | TK_VM_EXEC | TK_VM_USER)

void tk_vm_init(tk_address_space_t *space, tk_frame_allocator_t *frames)
{
    size_t index;

    if (space == NULL) {
        return;
    }
    for (index = 0; index < TK_MAX_MAPPINGS; ++index) {
        space->mappings[index].virtual_page = 0u;
        space->mappings[index].frame = 0u;
        space->mappings[index].flags = 0u;
        space->mappings[index].present = 0u;
    }
    space->frames = frames;
}

int tk_vm_map(tk_address_space_t *space, uint32_t virtual_address, uint8_t flags)
{
    size_t index;
    size_t free_index = TK_MAX_MAPPINGS;
    uint32_t page;
    int frame;

    if (space == NULL || space->frames == NULL ||
        virtual_address % TK_PAGE_SIZE != 0u ||
        (flags & TK_VM_READ) == 0u || (flags & (uint8_t)~TK_VM_ALL_FLAGS) != 0u) {
        return -1;
    }
    page = virtual_address / TK_PAGE_SIZE;
    for (index = 0; index < TK_MAX_MAPPINGS; ++index) {
        if (space->mappings[index].present != 0u) {
            if (space->mappings[index].virtual_page == page) {
                return -1;
            }
        } else if (free_index == TK_MAX_MAPPINGS) {
            free_index = index;
        }
    }
    if (free_index == TK_MAX_MAPPINGS) {
        return -1;
    }
    frame = tk_frame_alloc(space->frames);
    if (frame < 0) {
        return -1;
    }
    space->mappings[free_index].virtual_page = page;
    space->mappings[free_index].frame = (uint16_t)frame;
    space->mappings[free_index].flags = flags;
    space->mappings[free_index].present = 1u;
    return 0;
}

int tk_vm_translate(const tk_address_space_t *space, uint32_t virtual_address,
                    uint8_t required_flags, uint32_t *physical_out)
{
    size_t index;
    uint32_t page;
    uint32_t offset;

    if (space == NULL || physical_out == NULL ||
        (required_flags & (uint8_t)~TK_VM_ALL_FLAGS) != 0u) {
        return -1;
    }
    page = virtual_address / TK_PAGE_SIZE;
    offset = virtual_address % TK_PAGE_SIZE;
    for (index = 0; index < TK_MAX_MAPPINGS; ++index) {
        const tk_mapping_t *mapping = &space->mappings[index];
        if (mapping->present != 0u && mapping->virtual_page == page) {
            if ((mapping->flags & required_flags) != required_flags) {
                return -1;
            }
            *physical_out = (uint32_t)mapping->frame * TK_PAGE_SIZE + offset;
            return 0;
        }
    }
    return -1;
}

int tk_vm_unmap(tk_address_space_t *space, uint32_t virtual_address)
{
    size_t index;
    uint32_t page;

    if (space == NULL || space->frames == NULL ||
        virtual_address % TK_PAGE_SIZE != 0u) {
        return -1;
    }
    page = virtual_address / TK_PAGE_SIZE;
    for (index = 0; index < TK_MAX_MAPPINGS; ++index) {
        tk_mapping_t *mapping = &space->mappings[index];
        if (mapping->present != 0u && mapping->virtual_page == page) {
            if (tk_frame_free(space->frames, mapping->frame) != 0) {
                return -1;
            }
            mapping->virtual_page = 0u;
            mapping->frame = 0u;
            mapping->flags = 0u;
            mapping->present = 0u;
            return 0;
        }
    }
    return -1;
}

size_t tk_vm_mapping_count(const tk_address_space_t *space)
{
    size_t index;
    size_t count = 0u;

    if (space == NULL) {
        return 0u;
    }
    for (index = 0; index < TK_MAX_MAPPINGS; ++index) {
        if (space->mappings[index].present != 0u) {
            ++count;
        }
    }
    return count;
}
