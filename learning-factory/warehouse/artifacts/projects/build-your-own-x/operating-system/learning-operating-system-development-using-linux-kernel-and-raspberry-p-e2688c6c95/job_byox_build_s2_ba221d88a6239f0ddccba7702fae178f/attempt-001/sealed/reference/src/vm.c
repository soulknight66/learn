#include "minios.h"

static int permissions_valid(uint8_t permissions)
{
    unsigned int bits = (unsigned int)permissions;
    return bits != 0u &&
           (bits & ~(unsigned int)VM_ALL_PERMISSIONS) == 0u;
}

static int virtual_page_valid(uint32_t address)
{
    return address < MINIOS_VIRTUAL_PAGES * MINIOS_PAGE_SIZE &&
           address % MINIOS_PAGE_SIZE == 0u;
}

static int physical_frame_valid(uint32_t address)
{
    return address < MINIOS_PHYSICAL_FRAMES * MINIOS_PAGE_SIZE &&
           address % MINIOS_PAGE_SIZE == 0u;
}

void vm_space_init(vm_space_t *space)
{
    size_t i;

    if (space == NULL) {
        return;
    }
    for (i = 0; i < MINIOS_MAX_MAPPINGS; ++i) {
        space->mappings[i].virtual_page = 0u;
        space->mappings[i].physical_frame = 0u;
        space->mappings[i].permissions = 0u;
        space->mappings[i].present = 0u;
        space->mappings[i].reserved = 0u;
    }
}

os_status_t vm_map(vm_space_t *space, uint32_t virtual_page,
                   uint32_t physical_frame, uint8_t permissions)
{
    size_t i;
    size_t free_index = MINIOS_MAX_MAPPINGS;

    if (space == NULL) {
        return OS_ERR_INVALID;
    }
    if (!virtual_page_valid(virtual_page) ||
        !physical_frame_valid(physical_frame) ||
        !permissions_valid(permissions)) {
        return OS_ERR_INVALID;
    }
    for (i = 0; i < MINIOS_MAX_MAPPINGS; ++i) {
        if (space->mappings[i].present != 0u) {
            if (space->mappings[i].virtual_page == virtual_page) {
                return OS_ERR_EXISTS;
            }
        } else if (free_index == MINIOS_MAX_MAPPINGS) {
            free_index = i;
        }
    }
    if (free_index == MINIOS_MAX_MAPPINGS) {
        return OS_ERR_FULL;
    }

    space->mappings[free_index].virtual_page = virtual_page;
    space->mappings[free_index].physical_frame = physical_frame;
    space->mappings[free_index].permissions = permissions;
    space->mappings[free_index].reserved = 0u;
    space->mappings[free_index].present = 1u;
    return OS_OK;
}

os_status_t vm_translate(const vm_space_t *space, uint32_t virtual_address,
                         uint8_t required_permissions,
                         uint32_t *out_physical_address)
{
    uint32_t virtual_page;
    uint32_t page_offset;
    size_t i;

    if (out_physical_address != NULL) {
        *out_physical_address = 0u;
    }
    if (space == NULL || out_physical_address == NULL) {
        return OS_ERR_INVALID;
    }
    if (virtual_address >= MINIOS_VIRTUAL_PAGES * MINIOS_PAGE_SIZE ||
        !permissions_valid(required_permissions)) {
        return OS_ERR_INVALID;
    }
    virtual_page = virtual_address - (virtual_address % MINIOS_PAGE_SIZE);
    page_offset = virtual_address % MINIOS_PAGE_SIZE;

    for (i = 0; i < MINIOS_MAX_MAPPINGS; ++i) {
        const vm_mapping_t *mapping = &space->mappings[i];
        if (mapping->present != 0u &&
            mapping->virtual_page == virtual_page) {
            if ((mapping->permissions & required_permissions) !=
                required_permissions) {
                return OS_ERR_PERM;
            }
            *out_physical_address = mapping->physical_frame + page_offset;
            return OS_OK;
        }
    }
    return OS_ERR_NOT_FOUND;
}

os_status_t vm_unmap(vm_space_t *space, uint32_t virtual_page)
{
    size_t i;

    if (space == NULL || !virtual_page_valid(virtual_page)) {
        return OS_ERR_INVALID;
    }
    for (i = 0; i < MINIOS_MAX_MAPPINGS; ++i) {
        vm_mapping_t *mapping = &space->mappings[i];
        if (mapping->present != 0u &&
            mapping->virtual_page == virtual_page) {
            mapping->virtual_page = 0u;
            mapping->physical_frame = 0u;
            mapping->permissions = 0u;
            mapping->present = 0u;
            mapping->reserved = 0u;
            return OS_OK;
        }
    }
    return OS_ERR_NOT_FOUND;
}
