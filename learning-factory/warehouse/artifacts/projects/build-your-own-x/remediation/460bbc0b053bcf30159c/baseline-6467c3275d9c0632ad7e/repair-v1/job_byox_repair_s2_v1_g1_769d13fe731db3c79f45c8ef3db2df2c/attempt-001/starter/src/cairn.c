#include "cairn.h"

void cairn_init(struct cairn_kernel *kernel)
{
    int i;
    cairn_size byte;

    if (kernel == (struct cairn_kernel *)0) {
        return;
    }
    for (byte = 0; byte < (cairn_size)sizeof(*kernel); ++byte) {
        ((cairn_u8 *)kernel)[byte] = 0U;
    }
    kernel->next_pid = 1;
    kernel->current_slot = -1;
    for (i = 0; i < CAIRN_MAX_FRAMES; ++i) {
        kernel->frame_owner[i] = -1;
    }
}

/* TODO: implement the state transitions specified in REQUIREMENTS.md. */
int cairn_spawn(struct cairn_kernel *kernel, cairn_u32 entry, int *pid_out)
{
    (void)kernel;
    (void)entry;
    (void)pid_out;
    return CAIRN_ERR_UNIMPLEMENTED;
}

int cairn_schedule(struct cairn_kernel *kernel, int *pid_out)
{
    (void)kernel;
    (void)pid_out;
    return CAIRN_ERR_UNIMPLEMENTED;
}

int cairn_block_current(struct cairn_kernel *kernel)
{
    (void)kernel;
    return CAIRN_ERR_UNIMPLEMENTED;
}

int cairn_wake(struct cairn_kernel *kernel, int pid)
{
    (void)kernel;
    (void)pid;
    return CAIRN_ERR_UNIMPLEMENTED;
}

int cairn_exit_current(struct cairn_kernel *kernel, int exit_code)
{
    (void)kernel;
    (void)exit_code;
    return CAIRN_ERR_UNIMPLEMENTED;
}

int cairn_process_state(const struct cairn_kernel *kernel, int pid,
                        enum cairn_process_state *state_out)
{
    (void)kernel;
    (void)pid;
    (void)state_out;
    return CAIRN_ERR_UNIMPLEMENTED;
}

/* TODO: implement exclusive frame ownership and byte-address translation. */
int cairn_map(struct cairn_kernel *kernel, int pid, cairn_u32 virtual_address,
              cairn_u32 frame, int writable)
{
    (void)kernel;
    (void)pid;
    (void)virtual_address;
    (void)frame;
    (void)writable;
    return CAIRN_ERR_UNIMPLEMENTED;
}

int cairn_unmap(struct cairn_kernel *kernel, int pid, cairn_u32 virtual_address)
{
    (void)kernel;
    (void)pid;
    (void)virtual_address;
    return CAIRN_ERR_UNIMPLEMENTED;
}

int cairn_translate(const struct cairn_kernel *kernel, int pid, cairn_u32 virtual_address,
                    int write, cairn_u32 *physical_out)
{
    (void)kernel;
    (void)pid;
    (void)virtual_address;
    (void)write;
    (void)physical_out;
    return CAIRN_ERR_UNIMPLEMENTED;
}

/* TODO: implement bounded inode storage and per-process descriptor cursors. */
int cairn_create(struct cairn_kernel *kernel, const char *name)
{
    (void)kernel;
    (void)name;
    return CAIRN_ERR_UNIMPLEMENTED;
}

int cairn_unlink(struct cairn_kernel *kernel, const char *name)
{
    (void)kernel;
    (void)name;
    return CAIRN_ERR_UNIMPLEMENTED;
}

int cairn_open(struct cairn_kernel *kernel, int pid, const char *name, int *fd_out)
{
    (void)kernel;
    (void)pid;
    (void)name;
    (void)fd_out;
    return CAIRN_ERR_UNIMPLEMENTED;
}

int cairn_close(struct cairn_kernel *kernel, int pid, int fd)
{
    (void)kernel;
    (void)pid;
    (void)fd;
    return CAIRN_ERR_UNIMPLEMENTED;
}

int cairn_seek(struct cairn_kernel *kernel, int pid, int fd, cairn_size offset)
{
    (void)kernel;
    (void)pid;
    (void)fd;
    (void)offset;
    return CAIRN_ERR_UNIMPLEMENTED;
}

int cairn_write(struct cairn_kernel *kernel, int pid, int fd, const void *data,
                cairn_size count, cairn_size *written_out)
{
    (void)kernel;
    (void)pid;
    (void)fd;
    (void)data;
    (void)count;
    (void)written_out;
    return CAIRN_ERR_UNIMPLEMENTED;
}

int cairn_read(struct cairn_kernel *kernel, int pid, int fd, void *data,
               cairn_size count, cairn_size *read_out)
{
    (void)kernel;
    (void)pid;
    (void)fd;
    (void)data;
    (void)count;
    (void)read_out;
    return CAIRN_ERR_UNIMPLEMENTED;
}

int cairn_validate(const struct cairn_kernel *kernel)
{
    (void)kernel;
    return CAIRN_ERR_UNIMPLEMENTED;
}
