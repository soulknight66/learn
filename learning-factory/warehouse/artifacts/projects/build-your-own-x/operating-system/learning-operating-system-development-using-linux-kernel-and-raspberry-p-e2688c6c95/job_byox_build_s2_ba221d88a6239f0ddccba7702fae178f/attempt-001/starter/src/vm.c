#include "minios.h"

void vm_space_init(vm_space_t *space)
{
    size_t i;

    if (space == NULL) {
        return;
    }
    for (i = 0; i < MINIOS_MAX_MAPPINGS; ++i) {
        space->mappings[i].virtual_page = 0;
        space->mappings[i].physical_frame = 0;
        space->mappings[i].permissions = 0;
        space->mappings[i].present = 0;
        space->mappings[i].reserved = 0;
    }
}

os_status_t vm_map(vm_space_t *space, uint32_t virtual_page,
                   uint32_t physical_frame, uint8_t permissions)
{
    /* TODO: validate both ranges and insert a unique virtual-page mapping. */
    (void)space;
    (void)virtual_page;
    (void)physical_frame;
    (void)permissions;
    return OS_ERR_FULL;
}

os_status_t vm_translate(const vm_space_t *space, uint32_t virtual_address,
                         uint8_t required_permissions,
                         uint32_t *out_physical_address)
{
    /* TODO: check permissions and preserve the within-page byte offset. */
    (void)space;
    (void)virtual_address;
    (void)required_permissions;
    if (out_physical_address != NULL) {
        *out_physical_address = 0;
    }
    return OS_ERR_NOT_FOUND;
}

os_status_t vm_unmap(vm_space_t *space, uint32_t virtual_page)
{
    /* TODO: remove exactly one aligned virtual-page mapping. */
    (void)space;
    (void)virtual_page;
    return OS_ERR_NOT_FOUND;
}
