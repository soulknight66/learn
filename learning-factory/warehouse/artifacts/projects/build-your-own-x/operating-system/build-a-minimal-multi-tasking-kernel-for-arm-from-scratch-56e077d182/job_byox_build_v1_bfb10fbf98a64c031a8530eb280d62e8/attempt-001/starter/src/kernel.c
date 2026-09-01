#include "tinyarm.h"

/*
 * Compiling placeholders only. Implement every function from REQUIREMENTS.md.
 * The stubs intentionally do not encode reference algorithms.
 */

mk_status_t mk_init(mk_kernel_t *kernel, uint32_t quantum) {
    (void)kernel;
    (void)quantum;
    return MK_ERR_UNIMPLEMENTED;
}

mk_pid_t mk_spawn(mk_kernel_t *kernel, mk_task_fn step, void *userdata) {
    (void)kernel;
    (void)step;
    (void)userdata;
    return 0u;
}

mk_status_t mk_kill(mk_kernel_t *kernel, mk_pid_t pid, int exit_code) {
    (void)kernel;
    (void)pid;
    (void)exit_code;
    return MK_ERR_UNIMPLEMENTED;
}

mk_status_t mk_exit_current(mk_kernel_t *kernel, int exit_code) {
    (void)kernel;
    (void)exit_code;
    return MK_ERR_UNIMPLEMENTED;
}

mk_status_t mk_reap(mk_kernel_t *kernel, mk_pid_t pid, int *out_exit_code) {
    (void)kernel;
    (void)pid;
    (void)out_exit_code;
    return MK_ERR_UNIMPLEMENTED;
}

mk_status_t mk_sleep_current(mk_kernel_t *kernel, uint64_t delay) {
    (void)kernel;
    (void)delay;
    return MK_ERR_UNIMPLEMENTED;
}

mk_status_t mk_tick(mk_kernel_t *kernel) {
    (void)kernel;
    return MK_ERR_UNIMPLEMENTED;
}

size_t mk_run(mk_kernel_t *kernel, size_t limit) {
    (void)kernel;
    (void)limit;
    return 0u;
}

bool mk_has_live_tasks(const mk_kernel_t *kernel) {
    (void)kernel;
    return false;
}

mk_pid_t mk_current_pid(const mk_kernel_t *kernel) {
    (void)kernel;
    return 0u;
}

const mk_task_t *mk_task(const mk_kernel_t *kernel, mk_pid_t pid) {
    (void)kernel;
    (void)pid;
    return NULL;
}

mk_status_t mk_vm_map(mk_kernel_t *kernel, mk_pid_t pid, uintptr_t virtual_address,
                      uint8_t flags) {
    (void)kernel;
    (void)pid;
    (void)virtual_address;
    (void)flags;
    return MK_ERR_UNIMPLEMENTED;
}

mk_status_t mk_vm_unmap(mk_kernel_t *kernel, mk_pid_t pid, uintptr_t virtual_address) {
    (void)kernel;
    (void)pid;
    (void)virtual_address;
    return MK_ERR_UNIMPLEMENTED;
}

mk_status_t mk_vm_read(const mk_kernel_t *kernel, mk_pid_t pid, uintptr_t virtual_address,
                       void *destination, size_t length) {
    (void)kernel;
    (void)pid;
    (void)virtual_address;
    (void)destination;
    (void)length;
    return MK_ERR_UNIMPLEMENTED;
}

mk_status_t mk_vm_write(mk_kernel_t *kernel, mk_pid_t pid, uintptr_t virtual_address,
                        const void *source, size_t length) {
    (void)kernel;
    (void)pid;
    (void)virtual_address;
    (void)source;
    (void)length;
    return MK_ERR_UNIMPLEMENTED;
}

size_t mk_vm_free_frames(const mk_kernel_t *kernel) {
    (void)kernel;
    return 0u;
}

mk_status_t mk_fs_format(mk_kernel_t *kernel) {
    (void)kernel;
    return MK_ERR_UNIMPLEMENTED;
}

mk_status_t mk_fs_create(mk_kernel_t *kernel, const char *path) {
    (void)kernel;
    (void)path;
    return MK_ERR_UNIMPLEMENTED;
}

mk_status_t mk_fs_write(mk_kernel_t *kernel, const char *path, const void *data,
                        size_t length) {
    (void)kernel;
    (void)path;
    (void)data;
    (void)length;
    return MK_ERR_UNIMPLEMENTED;
}

mk_status_t mk_fs_read(const mk_kernel_t *kernel, const char *path, size_t offset,
                       void *destination, size_t capacity, size_t *out_read) {
    (void)kernel;
    (void)path;
    (void)offset;
    (void)destination;
    (void)capacity;
    (void)out_read;
    return MK_ERR_UNIMPLEMENTED;
}

mk_status_t mk_fs_stat(const mk_kernel_t *kernel, const char *path, size_t *out_size) {
    (void)kernel;
    (void)path;
    (void)out_size;
    return MK_ERR_UNIMPLEMENTED;
}

mk_status_t mk_fs_unlink(mk_kernel_t *kernel, const char *path) {
    (void)kernel;
    (void)path;
    return MK_ERR_UNIMPLEMENTED;
}

size_t mk_fs_free_blocks(const mk_kernel_t *kernel) {
    (void)kernel;
    return 0u;
}
