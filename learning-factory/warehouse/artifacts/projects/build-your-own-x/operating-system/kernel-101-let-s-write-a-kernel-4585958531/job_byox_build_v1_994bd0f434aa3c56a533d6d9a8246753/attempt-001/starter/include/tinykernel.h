#ifndef TINYKERNEL_H
#define TINYKERNEL_H

#include <stddef.h>
#include <stdint.h>

#define TK_MAX_FRAMES 128u
#define TK_MAX_PROCESSES 16u
#define TK_MAX_MAPPINGS 64u
#define TK_PAGE_SIZE 4096u
#define TK_MAX_FILES 16u
#define TK_NAME_CAPACITY 24u
#define TK_FILE_CAPACITY 256u

typedef struct {
    uint8_t used[TK_MAX_FRAMES];
    uint16_t frame_count;
    uint16_t free_count;
} tk_frame_allocator_t;

void tk_frames_init(tk_frame_allocator_t *allocator, uint16_t frame_count);
int tk_frame_alloc(tk_frame_allocator_t *allocator);
int tk_frame_free(tk_frame_allocator_t *allocator, uint16_t frame);
size_t tk_frame_available(const tk_frame_allocator_t *allocator);

typedef enum {
    TK_UNUSED = 0,
    TK_READY = 1,
    TK_RUNNING = 2,
    TK_BLOCKED = 3,
    TK_EXITED = 4
} tk_process_state_t;

typedef struct {
    uint32_t pid;
    tk_process_state_t state;
    uint32_t quanta;
} tk_process_t;

typedef struct {
    tk_process_t processes[TK_MAX_PROCESSES];
    int current_slot;
    size_t cursor;
    uint32_t next_pid;
} tk_scheduler_t;

void tk_scheduler_init(tk_scheduler_t *scheduler);
int tk_process_spawn(tk_scheduler_t *scheduler);
int tk_schedule(tk_scheduler_t *scheduler);
int tk_process_block(tk_scheduler_t *scheduler, uint32_t pid);
int tk_process_wake(tk_scheduler_t *scheduler, uint32_t pid);
int tk_process_exit(tk_scheduler_t *scheduler, uint32_t pid);
tk_process_state_t tk_process_state(const tk_scheduler_t *scheduler, uint32_t pid);
int tk_current_pid(const tk_scheduler_t *scheduler);

enum {
    TK_VM_READ = 1u << 0,
    TK_VM_WRITE = 1u << 1,
    TK_VM_EXEC = 1u << 2,
    TK_VM_USER = 1u << 3
};

typedef struct {
    uint32_t virtual_page;
    uint16_t frame;
    uint8_t flags;
    uint8_t present;
} tk_mapping_t;

typedef struct {
    tk_mapping_t mappings[TK_MAX_MAPPINGS];
    tk_frame_allocator_t *frames;
} tk_address_space_t;

void tk_vm_init(tk_address_space_t *space, tk_frame_allocator_t *frames);
int tk_vm_map(tk_address_space_t *space, uint32_t virtual_address, uint8_t flags);
int tk_vm_translate(const tk_address_space_t *space, uint32_t virtual_address,
                    uint8_t required_flags, uint32_t *physical_out);
int tk_vm_unmap(tk_address_space_t *space, uint32_t virtual_address);
size_t tk_vm_mapping_count(const tk_address_space_t *space);

typedef struct {
    char name[TK_NAME_CAPACITY];
    uint8_t data[TK_FILE_CAPACITY];
    uint16_t size;
    uint8_t used;
} tk_file_t;

typedef struct {
    tk_file_t files[TK_MAX_FILES];
} tk_fs_t;

void tk_fs_init(tk_fs_t *fs);
int tk_fs_create(tk_fs_t *fs, const char *name);
int tk_fs_write(tk_fs_t *fs, const char *name, const uint8_t *data, size_t length);
int tk_fs_read(const tk_fs_t *fs, const char *name, uint8_t *out, size_t capacity);
int tk_fs_size(const tk_fs_t *fs, const char *name);
int tk_fs_unlink(tk_fs_t *fs, const char *name);
size_t tk_fs_file_count(const tk_fs_t *fs);

#endif
