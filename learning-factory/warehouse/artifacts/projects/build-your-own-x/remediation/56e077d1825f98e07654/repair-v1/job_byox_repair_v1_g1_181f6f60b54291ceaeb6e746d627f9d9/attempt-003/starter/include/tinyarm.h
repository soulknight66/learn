#ifndef TINYARM_H
#define TINYARM_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define MK_MAX_TASKS 8u
#define MK_MAX_QUANTUM 16u
#define MK_USER_PAGE_COUNT 8u
#define MK_PAGE_SIZE 256u
#define MK_USER_SIZE (MK_USER_PAGE_COUNT * MK_PAGE_SIZE)
#define MK_FRAME_COUNT 16u
#define MK_MAX_FILES 8u
#define MK_PATH_MAX 23u
#define MK_FS_BLOCK_SIZE 64u
#define MK_FS_BLOCK_COUNT 16u
#define MK_FS_DIRECT_BLOCKS 4u
#define MK_FS_MAX_FILE_SIZE (MK_FS_BLOCK_SIZE * MK_FS_DIRECT_BLOCKS)

typedef uint32_t mk_pid_t;

typedef enum {
    MK_OK = 0,
    MK_ERR_INVALID = -1,
    MK_ERR_NOT_FOUND = -2,
    MK_ERR_NO_SPACE = -3,
    MK_ERR_EXISTS = -4,
    MK_ERR_PERMISSION = -5,
    MK_ERR_STATE = -6,
    MK_ERR_RANGE = -7,
    MK_ERR_UNIMPLEMENTED = -8
} mk_status_t;

typedef enum {
    MK_TASK_UNUSED = 0,
    MK_TASK_READY = 1,
    MK_TASK_RUNNING = 2,
    MK_TASK_BLOCKED = 3,
    MK_TASK_ZOMBIE = 4
} mk_task_state_t;

typedef enum {
    MK_STEP_CONTINUE = 0,
    MK_STEP_YIELD = 1,
    MK_STEP_EXIT = 2
} mk_step_result_t;

enum {
    MK_VM_READ = 1u,
    MK_VM_WRITE = 2u
};

struct mk_kernel;
typedef mk_step_result_t (*mk_task_fn)(struct mk_kernel *kernel, mk_pid_t pid,
                                       void *userdata);

typedef struct {
    uint8_t present;
    uint8_t flags;
    uint16_t frame;
} mk_pte_t;

typedef struct {
    mk_pid_t pid;
    mk_task_state_t state;
    mk_task_fn step;
    void *userdata;
    uint64_t wake_tick;
    uint32_t quantum_left;
    int exit_code;
    uint64_t steps;
    mk_pte_t pages[MK_USER_PAGE_COUNT];
} mk_task_t;

typedef struct {
    uint8_t used;
    char path[MK_PATH_MAX + 2u];
    size_t size;
    int16_t blocks[MK_FS_DIRECT_BLOCKS];
} mk_inode_t;

typedef struct mk_kernel {
    mk_task_t tasks[MK_MAX_TASKS];
    int current_slot;
    int last_slot;
    mk_pid_t next_pid;
    uint32_t quantum;
    uint64_t now;
    uint8_t frame_used[MK_FRAME_COUNT];
    uint8_t frames[MK_FRAME_COUNT][MK_PAGE_SIZE];
    mk_inode_t inodes[MK_MAX_FILES];
    uint8_t block_used[MK_FS_BLOCK_COUNT];
    uint8_t blocks[MK_FS_BLOCK_COUNT][MK_FS_BLOCK_SIZE];
} mk_kernel_t;

mk_status_t mk_init(mk_kernel_t *kernel, uint32_t quantum);
mk_pid_t mk_spawn(mk_kernel_t *kernel, mk_task_fn step, void *userdata);
mk_status_t mk_kill(mk_kernel_t *kernel, mk_pid_t pid, int exit_code);
mk_status_t mk_exit_current(mk_kernel_t *kernel, int exit_code);
mk_status_t mk_reap(mk_kernel_t *kernel, mk_pid_t pid, int *out_exit_code);
mk_status_t mk_sleep_current(mk_kernel_t *kernel, uint64_t delay);
mk_status_t mk_tick(mk_kernel_t *kernel);
size_t mk_run(mk_kernel_t *kernel, size_t limit);

/* Returns false for a null kernel (also the valid result when no task is live). */
bool mk_has_live_tasks(const mk_kernel_t *kernel);

/* Returns 0 for a null kernel or when there is no current running task. */
mk_pid_t mk_current_pid(const mk_kernel_t *kernel);

/* Returns NULL for a null kernel, PID 0, or a PID not present in any task slot. */
const mk_task_t *mk_task(const mk_kernel_t *kernel, mk_pid_t pid);

mk_status_t mk_vm_map(mk_kernel_t *kernel, mk_pid_t pid, uintptr_t virtual_address,
                      uint8_t flags);
mk_status_t mk_vm_unmap(mk_kernel_t *kernel, mk_pid_t pid, uintptr_t virtual_address);
mk_status_t mk_vm_read(const mk_kernel_t *kernel, mk_pid_t pid, uintptr_t virtual_address,
                       void *destination, size_t length);
mk_status_t mk_vm_write(mk_kernel_t *kernel, mk_pid_t pid, uintptr_t virtual_address,
                        const void *source, size_t length);

/* Returns 0 for a null kernel (also the valid count when no frame is free). */
size_t mk_vm_free_frames(const mk_kernel_t *kernel);

mk_status_t mk_fs_format(mk_kernel_t *kernel);
mk_status_t mk_fs_create(mk_kernel_t *kernel, const char *path);
mk_status_t mk_fs_write(mk_kernel_t *kernel, const char *path, const void *data,
                        size_t length);
mk_status_t mk_fs_read(const mk_kernel_t *kernel, const char *path, size_t offset,
                       void *destination, size_t capacity, size_t *out_read);
mk_status_t mk_fs_stat(const mk_kernel_t *kernel, const char *path, size_t *out_size);
mk_status_t mk_fs_unlink(mk_kernel_t *kernel, const char *path);

/* Returns 0 for a null kernel (also the valid count when no block is free). */
size_t mk_fs_free_blocks(const mk_kernel_t *kernel);

#endif
