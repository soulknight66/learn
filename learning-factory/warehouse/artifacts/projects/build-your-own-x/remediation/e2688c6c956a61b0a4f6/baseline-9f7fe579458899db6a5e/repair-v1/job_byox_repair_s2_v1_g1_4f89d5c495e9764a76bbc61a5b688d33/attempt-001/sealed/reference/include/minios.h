#ifndef MINIOS_H
#define MINIOS_H

#include <stddef.h>
#include <stdint.h>

#define MINIOS_MAX_PROCESSES 8u
#define MINIOS_PAGE_SIZE 4096u
#define MINIOS_VIRTUAL_PAGES 16u
#define MINIOS_PHYSICAL_FRAMES 32u
#define MINIOS_MAX_MAPPINGS 8u
#define MINIOS_FS_MAX_FILES 8u
#define MINIOS_FS_NAME_CHARS 30u
#define MINIOS_FS_NAME_STORAGE 32u
#define MINIOS_FS_FILE_CAPACITY 256u

typedef enum {
    OS_OK = 0,
    OS_ERR_INVALID = -1,
    OS_ERR_FULL = -2,
    OS_ERR_NOT_FOUND = -3,
    OS_ERR_STATE = -4,
    OS_ERR_EXISTS = -5,
    OS_ERR_PERM = -6,
    OS_ERR_NO_SPACE = -7
} os_status_t;

typedef enum {
    PROC_UNUSED = 0,
    PROC_READY = 1,
    PROC_RUNNING = 2,
    PROC_BLOCKED = 3,
    PROC_ZOMBIE = 4
} proc_state_t;

typedef struct {
    uint32_t pid;
    uint32_t parent_pid;
    uintptr_t entry_point;
    int32_t exit_code;
    proc_state_t state;
} process_t;

typedef struct {
    process_t slots[MINIOS_MAX_PROCESSES];
    uint32_t next_pid;
    int32_t current_slot;
} proc_table_t;

void proc_table_init(proc_table_t *table);
os_status_t proc_spawn(proc_table_t *table, uint32_t parent_pid,
                       uintptr_t entry_point, uint32_t *out_pid);
os_status_t proc_schedule(proc_table_t *table, uint32_t *out_pid);
os_status_t proc_block(proc_table_t *table, uint32_t pid);
os_status_t proc_wake(proc_table_t *table, uint32_t pid);
os_status_t proc_exit(proc_table_t *table, uint32_t pid, int32_t exit_code);
os_status_t proc_reap(proc_table_t *table, uint32_t pid,
                      int32_t *out_exit_code);
os_status_t proc_get(const proc_table_t *table, uint32_t pid,
                     const process_t **out_process);

enum {
    VM_READ = 1u << 0,
    VM_WRITE = 1u << 1,
    VM_EXEC = 1u << 2,
    VM_USER = 1u << 3,
    VM_ALL_PERMISSIONS = VM_READ | VM_WRITE | VM_EXEC | VM_USER
};

typedef struct {
    uint32_t virtual_page;
    uint32_t physical_frame;
    uint8_t permissions;
    uint8_t present;
    uint16_t reserved;
} vm_mapping_t;

typedef struct {
    vm_mapping_t mappings[MINIOS_MAX_MAPPINGS];
} vm_space_t;

void vm_space_init(vm_space_t *space);
os_status_t vm_map(vm_space_t *space, uint32_t virtual_page,
                   uint32_t physical_frame, uint8_t permissions);
os_status_t vm_translate(const vm_space_t *space, uint32_t virtual_address,
                         uint8_t required_permissions,
                         uint32_t *out_physical_address);
os_status_t vm_unmap(vm_space_t *space, uint32_t virtual_page);

typedef struct {
    uint8_t used;
    char name[MINIOS_FS_NAME_STORAGE];
    uint8_t data[MINIOS_FS_FILE_CAPACITY];
    size_t size;
} fs_file_t;

typedef struct {
    fs_file_t files[MINIOS_FS_MAX_FILES];
} ramfs_t;

void fs_init(ramfs_t *fs);
os_status_t fs_create(ramfs_t *fs, const char *name);
os_status_t fs_stat(const ramfs_t *fs, const char *name, size_t *out_size);
os_status_t fs_write(ramfs_t *fs, const char *name, size_t offset,
                     const uint8_t *data, size_t count, size_t *out_written);
os_status_t fs_read(const ramfs_t *fs, const char *name, size_t offset,
                    uint8_t *data, size_t count, size_t *out_read);
os_status_t fs_unlink(ramfs_t *fs, const char *name);

#endif
