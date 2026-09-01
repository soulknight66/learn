#ifndef PEBBLE_H
#define PEBBLE_H

#include <stddef.h>
#include <stdint.h>

#define PEBBLE_MAX_PROCESSES 8u
#define PEBBLE_PAGE_SIZE 256u
#define PEBBLE_VIRTUAL_PAGES 16u
#define PEBBLE_PHYSICAL_FRAMES 32u
#define PEBBLE_MAX_FILES 8u
#define PEBBLE_MAX_FDS 4u
#define PEBBLE_MAX_NAME 31u
#define PEBBLE_MAX_FILE_BYTES 1024u

typedef enum {
    PEBBLE_OK = 0,
    PEBBLE_ERR_INVALID = -1,
    PEBBLE_ERR_NOT_FOUND = -2,
    PEBBLE_ERR_NO_SPACE = -3,
    PEBBLE_ERR_STATE = -4,
    PEBBLE_ERR_PERMISSION = -5,
    PEBBLE_ERR_BAD_FD = -6,
    PEBBLE_ERR_BUSY = -7,
    PEBBLE_ERR_OVERFLOW = -8,
    PEBBLE_ERR_CORRUPT = -9,
    PEBBLE_ERR_NOT_IMPLEMENTED = -10
} pebble_status_t;

typedef enum {
    PEBBLE_PROC_UNUSED = 0,
    PEBBLE_PROC_READY = 1,
    PEBBLE_PROC_RUNNING = 2,
    PEBBLE_PROC_BLOCKED = 3,
    PEBBLE_PROC_ZOMBIE = 4
} pebble_process_state_t;

enum {
    PEBBLE_PAGE_READ = 1u << 0,
    PEBBLE_PAGE_WRITE = 1u << 1,
    PEBBLE_PAGE_COW = 1u << 2,
    PEBBLE_PAGE_PRESENT = 1u << 7
};

enum {
    PEBBLE_OPEN_READ = 1u << 0,
    PEBBLE_OPEN_WRITE = 1u << 1,
    PEBBLE_OPEN_CREATE = 1u << 2,
    PEBBLE_OPEN_TRUNCATE = 1u << 3
};

typedef struct {
    uint16_t frame;
    uint8_t flags;
    uint8_t reserved;
} pebble_pte_t;

typedef struct {
    uint8_t used;
    uint8_t flags;
    uint16_t file_index;
    uint16_t cursor;
    uint16_t reserved;
} pebble_fd_t;

typedef struct {
    int32_t pid;
    int32_t exit_status;
    pebble_process_state_t state;
    pebble_pte_t pages[PEBBLE_VIRTUAL_PAGES];
    pebble_fd_t fds[PEBBLE_MAX_FDS];
} pebble_process_t;

typedef struct {
    uint16_t refs;
    uint16_t reserved;
    uint8_t data[PEBBLE_PAGE_SIZE];
} pebble_frame_t;

typedef struct {
    uint8_t used;
    uint8_t reserved0;
    uint16_t size;
    uint16_t open_count;
    uint16_t reserved1;
    char name[PEBBLE_MAX_NAME + 1u];
    uint8_t data[PEBBLE_MAX_FILE_BYTES];
} pebble_file_t;

typedef struct {
    pebble_process_t processes[PEBBLE_MAX_PROCESSES];
    pebble_frame_t frames[PEBBLE_PHYSICAL_FRAMES];
    pebble_file_t files[PEBBLE_MAX_FILES];
    int16_t current_slot;
    uint16_t schedule_cursor;
    uint32_t next_pid;
    uint64_t ticks;
} pebble_kernel_t;

void pebble_init(pebble_kernel_t *kernel);

int32_t pebble_process_create(pebble_kernel_t *kernel);
int32_t pebble_process_fork(pebble_kernel_t *kernel, int32_t parent_pid);
int pebble_process_block(pebble_kernel_t *kernel, int32_t pid);
int pebble_process_wake(pebble_kernel_t *kernel, int32_t pid);
int pebble_process_exit(pebble_kernel_t *kernel, int32_t pid, int32_t status);
int pebble_process_reap(pebble_kernel_t *kernel, int32_t pid, int32_t *status_out);
int32_t pebble_process_state(const pebble_kernel_t *kernel, int32_t pid);
int32_t pebble_schedule(pebble_kernel_t *kernel);

int pebble_vm_map(pebble_kernel_t *kernel, int32_t pid, uint16_t virtual_page,
                  uint8_t permissions);
int pebble_vm_unmap(pebble_kernel_t *kernel, int32_t pid, uint16_t virtual_page);
int32_t pebble_vm_read(const pebble_kernel_t *kernel, int32_t pid, uint32_t address,
                       void *destination, size_t length);
int32_t pebble_vm_write(pebble_kernel_t *kernel, int32_t pid, uint32_t address,
                        const void *source, size_t length);

int32_t pebble_fs_open(pebble_kernel_t *kernel, int32_t pid, const char *name,
                       uint8_t flags);
int pebble_fs_close(pebble_kernel_t *kernel, int32_t pid, int32_t fd);
int32_t pebble_fs_read(pebble_kernel_t *kernel, int32_t pid, int32_t fd,
                       void *destination, size_t length);
int32_t pebble_fs_write(pebble_kernel_t *kernel, int32_t pid, int32_t fd,
                        const void *source, size_t length);
int pebble_fs_seek(pebble_kernel_t *kernel, int32_t pid, int32_t fd,
                   size_t position);
int pebble_fs_size(const pebble_kernel_t *kernel, int32_t pid, int32_t fd,
                   size_t *size_out);
int pebble_fs_unlink(pebble_kernel_t *kernel, const char *name);

int pebble_check(const pebble_kernel_t *kernel, char *why, size_t why_capacity);

#endif
