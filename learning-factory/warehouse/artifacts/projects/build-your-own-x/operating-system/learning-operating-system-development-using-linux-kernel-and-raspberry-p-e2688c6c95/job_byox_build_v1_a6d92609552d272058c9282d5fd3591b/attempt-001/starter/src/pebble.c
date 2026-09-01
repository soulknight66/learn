#include "pebble.h"

#include <string.h>

void pebble_init(pebble_kernel_t *kernel)
{
    if (kernel == NULL) {
        return;
    }
    memset(kernel, 0, sizeof(*kernel));
    kernel->current_slot = -1;
    kernel->next_pid = 1u;
}

int32_t pebble_process_create(pebble_kernel_t *kernel)
{
    (void)kernel;
    return PEBBLE_ERR_NOT_IMPLEMENTED;
}

int32_t pebble_process_fork(pebble_kernel_t *kernel, int32_t parent_pid)
{
    (void)kernel;
    (void)parent_pid;
    return PEBBLE_ERR_NOT_IMPLEMENTED;
}

int pebble_process_block(pebble_kernel_t *kernel, int32_t pid)
{
    (void)kernel;
    (void)pid;
    return PEBBLE_ERR_NOT_IMPLEMENTED;
}

int pebble_process_wake(pebble_kernel_t *kernel, int32_t pid)
{
    (void)kernel;
    (void)pid;
    return PEBBLE_ERR_NOT_IMPLEMENTED;
}

int pebble_process_exit(pebble_kernel_t *kernel, int32_t pid, int32_t status)
{
    (void)kernel;
    (void)pid;
    (void)status;
    return PEBBLE_ERR_NOT_IMPLEMENTED;
}

int pebble_process_reap(pebble_kernel_t *kernel, int32_t pid, int32_t *status_out)
{
    (void)kernel;
    (void)pid;
    (void)status_out;
    return PEBBLE_ERR_NOT_IMPLEMENTED;
}

int32_t pebble_process_state(const pebble_kernel_t *kernel, int32_t pid)
{
    size_t index;

    if (kernel == NULL || pid <= 0) {
        return PEBBLE_ERR_INVALID;
    }
    for (index = 0u; index < PEBBLE_MAX_PROCESSES; ++index) {
        if (kernel->processes[index].state != PEBBLE_PROC_UNUSED &&
            kernel->processes[index].pid == pid) {
            return (int32_t)kernel->processes[index].state;
        }
    }
    return PEBBLE_ERR_NOT_FOUND;
}

int32_t pebble_schedule(pebble_kernel_t *kernel)
{
    (void)kernel;
    return PEBBLE_ERR_NOT_IMPLEMENTED;
}

int pebble_vm_map(pebble_kernel_t *kernel, int32_t pid, uint16_t virtual_page,
                  uint8_t permissions)
{
    (void)kernel;
    (void)pid;
    (void)virtual_page;
    (void)permissions;
    return PEBBLE_ERR_NOT_IMPLEMENTED;
}

int pebble_vm_unmap(pebble_kernel_t *kernel, int32_t pid, uint16_t virtual_page)
{
    (void)kernel;
    (void)pid;
    (void)virtual_page;
    return PEBBLE_ERR_NOT_IMPLEMENTED;
}

int32_t pebble_vm_read(const pebble_kernel_t *kernel, int32_t pid, uint32_t address,
                       void *destination, size_t length)
{
    (void)kernel;
    (void)pid;
    (void)address;
    (void)destination;
    (void)length;
    return PEBBLE_ERR_NOT_IMPLEMENTED;
}

int32_t pebble_vm_write(pebble_kernel_t *kernel, int32_t pid, uint32_t address,
                        const void *source, size_t length)
{
    (void)kernel;
    (void)pid;
    (void)address;
    (void)source;
    (void)length;
    return PEBBLE_ERR_NOT_IMPLEMENTED;
}

int32_t pebble_fs_open(pebble_kernel_t *kernel, int32_t pid, const char *name,
                       uint8_t flags)
{
    (void)kernel;
    (void)pid;
    (void)name;
    (void)flags;
    return PEBBLE_ERR_NOT_IMPLEMENTED;
}

int pebble_fs_close(pebble_kernel_t *kernel, int32_t pid, int32_t fd)
{
    (void)kernel;
    (void)pid;
    (void)fd;
    return PEBBLE_ERR_NOT_IMPLEMENTED;
}

int32_t pebble_fs_read(pebble_kernel_t *kernel, int32_t pid, int32_t fd,
                       void *destination, size_t length)
{
    (void)kernel;
    (void)pid;
    (void)fd;
    (void)destination;
    (void)length;
    return PEBBLE_ERR_NOT_IMPLEMENTED;
}

int32_t pebble_fs_write(pebble_kernel_t *kernel, int32_t pid, int32_t fd,
                        const void *source, size_t length)
{
    (void)kernel;
    (void)pid;
    (void)fd;
    (void)source;
    (void)length;
    return PEBBLE_ERR_NOT_IMPLEMENTED;
}

int pebble_fs_seek(pebble_kernel_t *kernel, int32_t pid, int32_t fd,
                   size_t position)
{
    (void)kernel;
    (void)pid;
    (void)fd;
    (void)position;
    return PEBBLE_ERR_NOT_IMPLEMENTED;
}

int pebble_fs_size(const pebble_kernel_t *kernel, int32_t pid, int32_t fd,
                   size_t *size_out)
{
    (void)kernel;
    (void)pid;
    (void)fd;
    (void)size_out;
    return PEBBLE_ERR_NOT_IMPLEMENTED;
}

int pebble_fs_unlink(pebble_kernel_t *kernel, const char *name)
{
    (void)kernel;
    (void)name;
    return PEBBLE_ERR_NOT_IMPLEMENTED;
}

int pebble_check(const pebble_kernel_t *kernel, char *why, size_t why_capacity)
{
    if (why != NULL && why_capacity > 0u) {
        why[0] = '\0';
    }
    if (kernel == NULL) {
        return PEBBLE_ERR_CORRUPT;
    }
    if (kernel->current_slot != -1 || kernel->schedule_cursor != 0u ||
        kernel->next_pid != 1u || kernel->ticks != 0u) {
        return PEBBLE_ERR_NOT_IMPLEMENTED;
    }
    return PEBBLE_OK;
}
