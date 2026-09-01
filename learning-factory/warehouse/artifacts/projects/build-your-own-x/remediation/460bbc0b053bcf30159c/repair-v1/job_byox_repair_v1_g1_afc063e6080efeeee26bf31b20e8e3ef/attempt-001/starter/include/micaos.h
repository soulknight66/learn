#ifndef MICAOS_H
#define MICAOS_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define MICA_MAX_PROCESSES 8u
#define MICA_VIRTUAL_PAGES 16u
#define MICA_PHYSICAL_FRAMES 8u
#define MICA_PAGE_SIZE 64u
#define MICA_MAX_FILES 8u
#define MICA_NAME_MAX 15u
#define MICA_FILE_CAPACITY 128u

typedef enum mica_status {
    MICA_OK = 0,
    MICA_ERR_ARG = -1,
    MICA_ERR_FULL = -2,
    MICA_ERR_NOT_FOUND = -3,
    MICA_ERR_STATE = -4,
    MICA_ERR_EXISTS = -5,
    MICA_ERR_RANGE = -6,
    MICA_ERR_PERM = -7
} mica_status_t;

/* Scheduler */

typedef uint32_t mica_pid_t;

typedef enum mica_process_state {
    MICA_PROCESS_UNUSED = 0,
    MICA_PROCESS_READY,
    MICA_PROCESS_RUNNING,
    MICA_PROCESS_BLOCKED,
    MICA_PROCESS_EXITED
} mica_process_state_t;

typedef struct mica_process_info {
    mica_pid_t pid;
    mica_process_state_t state;
    int exit_code;
} mica_process_info_t;

typedef struct mica_scheduler {
    mica_process_info_t processes[MICA_MAX_PROCESSES];
    mica_pid_t next_pid;
    size_t cursor;
} mica_scheduler_t;

/* All three void initializers accept NULL as a no-op. */
void mica_scheduler_init(mica_scheduler_t *scheduler);
mica_status_t mica_scheduler_spawn(mica_scheduler_t *scheduler,
                                   mica_pid_t *out_pid);
mica_status_t mica_scheduler_schedule(mica_scheduler_t *scheduler,
                                      mica_pid_t *out_pid);
mica_status_t mica_scheduler_block(mica_scheduler_t *scheduler,
                                   mica_pid_t pid);
mica_status_t mica_scheduler_wake(mica_scheduler_t *scheduler,
                                  mica_pid_t pid);
mica_status_t mica_scheduler_exit(mica_scheduler_t *scheduler,
                                  mica_pid_t pid,
                                  int exit_code);
mica_status_t mica_scheduler_reap(mica_scheduler_t *scheduler,
                                  mica_pid_t pid,
                                  int *out_exit_code);
mica_status_t mica_scheduler_inspect(const mica_scheduler_t *scheduler,
                                     mica_pid_t pid,
                                     mica_process_info_t *out_info);

/* A short spelling of inspect, with identical behavior. */
mica_status_t mica_scheduler_get(const mica_scheduler_t *scheduler,
                                 mica_pid_t pid,
                                 mica_process_info_t *out_info);

/* Virtual memory */

typedef struct mica_page_entry {
    bool mapped;
    bool writable;
    uint8_t frame;
} mica_page_entry_t;

typedef struct mica_address_space {
    mica_page_entry_t pages[MICA_VIRTUAL_PAGES];
} mica_address_space_t;

typedef struct mica_vm {
    uint8_t frames[MICA_PHYSICAL_FRAMES][MICA_PAGE_SIZE];
    bool frame_used[MICA_PHYSICAL_FRAMES];
} mica_vm_t;

/* NULL is a no-op; initialize the allocator and each fresh space separately. */
void mica_vm_init(mica_vm_t *vm);
void mica_vm_space_init(mica_address_space_t *space);
mica_status_t mica_vm_map(mica_vm_t *vm,
                          mica_address_space_t *space,
                          size_t virtual_page,
                          bool writable);
mica_status_t mica_vm_unmap(mica_vm_t *vm,
                            mica_address_space_t *space,
                            size_t virtual_page);
mica_status_t mica_vm_read_u8(const mica_vm_t *vm,
                              const mica_address_space_t *space,
                              size_t virtual_address,
                              uint8_t *out_value);
mica_status_t mica_vm_write_u8(mica_vm_t *vm,
                               const mica_address_space_t *space,
                               size_t virtual_address,
                               uint8_t value);

/* RAM filesystem */

typedef struct mica_ramfs_file {
    bool used;
    char name[MICA_NAME_MAX + 1u];
    uint8_t data[MICA_FILE_CAPACITY];
    size_t size;
} mica_ramfs_file_t;

typedef struct mica_ramfs {
    mica_ramfs_file_t files[MICA_MAX_FILES];
} mica_ramfs_t;

typedef struct mica_ramfs_stat {
    size_t size;
} mica_ramfs_stat_t;

/* NULL is a no-op. */
void mica_ramfs_init(mica_ramfs_t *fs);
/* Names contain 1..MICA_NAME_MAX non-slash characters; "." and ".." are invalid. */
mica_status_t mica_ramfs_create(mica_ramfs_t *fs, const char *name);
/*
 * Writes are all-or-nothing. Positive-length writes may extend a file and
 * leave a zero-filled gap. A zero-length write never changes the file size.
 * data may overlap a file data array; its input bytes are snapshotted first.
 */
mica_status_t mica_ramfs_write(mica_ramfs_t *fs,
                               const char *name,
                               size_t offset,
                               const uint8_t *data,
                               size_t length);
/* Reads at most capacity bytes; out may be NULL only when capacity is zero. */
mica_status_t mica_ramfs_read(const mica_ramfs_t *fs,
                              const char *name,
                              size_t offset,
                              uint8_t *out,
                              size_t capacity,
                              size_t *out_read);
mica_status_t mica_ramfs_unlink(mica_ramfs_t *fs, const char *name);
mica_status_t mica_ramfs_stat(const mica_ramfs_t *fs,
                              const char *name,
                              mica_ramfs_stat_t *out_stat);

#endif
