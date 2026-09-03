#ifndef CAIRN_H
#define CAIRN_H

/* Deliberately freestanding types: these declarations do not include libc headers. */
typedef unsigned char cairn_u8;
typedef unsigned int cairn_u32;
typedef unsigned long cairn_size;

#define CAIRN_MAX_PROCESSES 8
#define CAIRN_MAX_MAPPINGS 8
#define CAIRN_MAX_FRAMES 32
#define CAIRN_MAX_FDS 4
#define CAIRN_MAX_FILES 16
#define CAIRN_NAME_CAP 24
#define CAIRN_FILE_CAP 256
#define CAIRN_PAGE_SIZE 4096U
#define CAIRN_USER_TOP 0x01000000U

enum cairn_status {
    CAIRN_OK = 0,
    CAIRN_ERR_INVALID = -1,
    CAIRN_ERR_NOT_FOUND = -2,
    CAIRN_ERR_EXISTS = -3,
    CAIRN_ERR_NO_SPACE = -4,
    CAIRN_ERR_BAD_STATE = -5,
    CAIRN_ERR_PERMISSION = -6,
    CAIRN_ERR_BUSY = -7,
    CAIRN_ERR_NO_RUNNABLE = -8,
    CAIRN_ERR_CORRUPT = -9,
    CAIRN_ERR_UNIMPLEMENTED = -10
};

enum cairn_process_state {
    CAIRN_PROCESS_EMPTY = 0,
    CAIRN_PROCESS_READY = 1,
    CAIRN_PROCESS_RUNNING = 2,
    CAIRN_PROCESS_BLOCKED = 3,
    CAIRN_PROCESS_EXITED = 4
};

struct cairn_mapping {
    cairn_u32 virtual_page;
    cairn_u32 frame;
    int writable;
    int present;
};

struct cairn_descriptor {
    int inode_slot;
    cairn_size offset;
    int in_use;
};

struct cairn_process {
    int pid;
    enum cairn_process_state state;
    cairn_u32 entry;
    int exit_code;
    struct cairn_mapping mappings[CAIRN_MAX_MAPPINGS];
    struct cairn_descriptor descriptors[CAIRN_MAX_FDS];
};

struct cairn_inode {
    int in_use;
    char name[CAIRN_NAME_CAP];
    cairn_size size;
    cairn_u8 data[CAIRN_FILE_CAP];
};

struct cairn_kernel {
    int next_pid;
    int current_slot;
    struct cairn_process processes[CAIRN_MAX_PROCESSES];
    int frame_owner[CAIRN_MAX_FRAMES];
    struct cairn_inode inodes[CAIRN_MAX_FILES];
};

void cairn_init(struct cairn_kernel *kernel);

int cairn_spawn(struct cairn_kernel *kernel, cairn_u32 entry, int *pid_out);
int cairn_schedule(struct cairn_kernel *kernel, int *pid_out);
int cairn_block_current(struct cairn_kernel *kernel);
int cairn_wake(struct cairn_kernel *kernel, int pid);
int cairn_exit_current(struct cairn_kernel *kernel, int exit_code);
int cairn_process_state(const struct cairn_kernel *kernel, int pid,
                        enum cairn_process_state *state_out);

int cairn_map(struct cairn_kernel *kernel, int pid, cairn_u32 virtual_address,
              cairn_u32 frame, int writable);
int cairn_unmap(struct cairn_kernel *kernel, int pid, cairn_u32 virtual_address);
int cairn_translate(const struct cairn_kernel *kernel, int pid, cairn_u32 virtual_address,
                    int write, cairn_u32 *physical_out);

int cairn_create(struct cairn_kernel *kernel, const char *name);
int cairn_unlink(struct cairn_kernel *kernel, const char *name);
int cairn_open(struct cairn_kernel *kernel, int pid, const char *name, int *fd_out);
int cairn_close(struct cairn_kernel *kernel, int pid, int fd);
int cairn_seek(struct cairn_kernel *kernel, int pid, int fd, cairn_size offset);
int cairn_write(struct cairn_kernel *kernel, int pid, int fd, const void *data,
                cairn_size count, cairn_size *written_out);
int cairn_read(struct cairn_kernel *kernel, int pid, int fd, void *data,
               cairn_size count, cairn_size *read_out);

int cairn_validate(const struct cairn_kernel *kernel);

#endif
