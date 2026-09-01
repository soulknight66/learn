#include "tinykernel.h"

void tk_vm_init(tk_address_space_t *space, tk_frame_allocator_t *frames)
{
    if (space != NULL) {
        size_t i;
        for (i = 0; i < TK_MAX_MAPPINGS; ++i) {
            space->mappings[i].virtual_page = 0u;
            space->mappings[i].frame = 0u;
            space->mappings[i].flags = 0u;
            space->mappings[i].present = 0u;
        }
        space->frames = frames;
    }
}

int tk_vm_map(tk_address_space_t *space, uint32_t virtual_address, uint8_t flags)
{
    (void)space;
    (void)virtual_address;
    (void)flags;
    /* TODO(stage 3): validate, reserve a frame, and publish a mapping. */
    return -1;
}

int tk_vm_translate(const tk_address_space_t *space, uint32_t virtual_address,
                    uint8_t required_flags, uint32_t *physical_out)
{
    (void)space;
    (void)virtual_address;
    (void)required_flags;
    (void)physical_out;
    return -1;
}

int tk_vm_unmap(tk_address_space_t *space, uint32_t virtual_address)
{
    (void)space;
    (void)virtual_address;
    return -1;
}

size_t tk_vm_mapping_count(const tk_address_space_t *space)
{
    (void)space;
    return 0u;
}
