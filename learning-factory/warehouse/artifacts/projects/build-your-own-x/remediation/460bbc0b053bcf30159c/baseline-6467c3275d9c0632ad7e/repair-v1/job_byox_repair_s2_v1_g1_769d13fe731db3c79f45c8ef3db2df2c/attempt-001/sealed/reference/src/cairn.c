#include "cairn.h"

static void clear_bytes(void *destination, cairn_size count)
{
    cairn_u8 *bytes = (cairn_u8 *)destination;
    cairn_size i;

    for (i = 0; i < count; ++i) {
        bytes[i] = 0U;
    }
}

static void copy_bytes(void *destination, const void *source, cairn_size count)
{
    cairn_u8 *to = (cairn_u8 *)destination;
    const cairn_u8 *from = (const cairn_u8 *)source;
    cairn_size i;

    for (i = 0; i < count; ++i) {
        to[i] = from[i];
    }
}

static int valid_name(const char *name, cairn_size *length_out)
{
    cairn_size i;

    if (name == (const char *)0) {
        return 0;
    }
    for (i = 0; i < CAIRN_NAME_CAP; ++i) {
        if (name[i] == '\0') {
            if (i == 0U) {
                return 0;
            }
            if (length_out != (cairn_size *)0) {
                *length_out = i;
            }
            return 1;
        }
        if (name[i] == '/') {
            return 0;
        }
    }
    return 0;
}

static int names_equal(const char *left, const char *right)
{
    cairn_size i;

    for (i = 0; i < CAIRN_NAME_CAP; ++i) {
        if (left[i] != right[i]) {
            return 0;
        }
        if (left[i] == '\0') {
            return 1;
        }
    }
    return 0;
}

static int find_process(const struct cairn_kernel *kernel, int pid)
{
    int i;

    for (i = 0; i < CAIRN_MAX_PROCESSES; ++i) {
        if (kernel->processes[i].state != CAIRN_PROCESS_EMPTY &&
            kernel->processes[i].pid == pid) {
            return i;
        }
    }
    return -1;
}

static int process_is_live(const struct cairn_process *process)
{
    return process->state == CAIRN_PROCESS_READY ||
           process->state == CAIRN_PROCESS_RUNNING ||
           process->state == CAIRN_PROCESS_BLOCKED;
}

static int find_inode(const struct cairn_kernel *kernel, const char *name)
{
    int i;

    for (i = 0; i < CAIRN_MAX_FILES; ++i) {
        if (kernel->inodes[i].in_use == 1 && names_equal(kernel->inodes[i].name, name)) {
            return i;
        }
    }
    return -1;
}

static int descriptor_for(struct cairn_kernel *kernel, int pid, int fd,
                          struct cairn_process **process_out,
                          struct cairn_descriptor **descriptor_out,
                          struct cairn_inode **inode_out)
{
    int process_slot;
    struct cairn_process *process;
    struct cairn_descriptor *descriptor;

    if (kernel == (struct cairn_kernel *)0 || pid <= 0 || fd < 0 || fd >= CAIRN_MAX_FDS) {
        return CAIRN_ERR_INVALID;
    }
    process_slot = find_process(kernel, pid);
    if (process_slot < 0) {
        return CAIRN_ERR_NOT_FOUND;
    }
    process = &kernel->processes[process_slot];
    if (!process_is_live(process)) {
        return CAIRN_ERR_BAD_STATE;
    }
    descriptor = &process->descriptors[fd];
    if (descriptor->in_use != 1) {
        return CAIRN_ERR_NOT_FOUND;
    }
    if (descriptor->inode_slot < 0 || descriptor->inode_slot >= CAIRN_MAX_FILES ||
        kernel->inodes[descriptor->inode_slot].in_use != 1) {
        return CAIRN_ERR_CORRUPT;
    }
    if (process_out != (struct cairn_process **)0) {
        *process_out = process;
    }
    if (descriptor_out != (struct cairn_descriptor **)0) {
        *descriptor_out = descriptor;
    }
    if (inode_out != (struct cairn_inode **)0) {
        *inode_out = &kernel->inodes[descriptor->inode_slot];
    }
    return CAIRN_OK;
}

void cairn_init(struct cairn_kernel *kernel)
{
    int i;

    if (kernel == (struct cairn_kernel *)0) {
        return;
    }
    clear_bytes(kernel, (cairn_size)sizeof(*kernel));
    kernel->next_pid = 1;
    kernel->current_slot = -1;
    for (i = 0; i < CAIRN_MAX_FRAMES; ++i) {
        kernel->frame_owner[i] = -1;
    }
}

int cairn_spawn(struct cairn_kernel *kernel, cairn_u32 entry, int *pid_out)
{
    int slot = -1;
    int i;
    int pid;

    if (kernel == (struct cairn_kernel *)0 || pid_out == (int *)0 ||
        entry >= CAIRN_USER_TOP) {
        return CAIRN_ERR_INVALID;
    }
    if (kernel->next_pid <= 0) {
        return CAIRN_ERR_CORRUPT;
    }
    if (kernel->next_pid == 2147483647) {
        return CAIRN_ERR_NO_SPACE;
    }
    for (i = 0; i < CAIRN_MAX_PROCESSES; ++i) {
        if (kernel->processes[i].state == CAIRN_PROCESS_EMPTY ||
            kernel->processes[i].state == CAIRN_PROCESS_EXITED) {
            slot = i;
            break;
        }
    }
    if (slot < 0) {
        return CAIRN_ERR_NO_SPACE;
    }

    pid = kernel->next_pid;
    clear_bytes(&kernel->processes[slot], (cairn_size)sizeof(kernel->processes[slot]));
    kernel->processes[slot].pid = pid;
    kernel->processes[slot].state = CAIRN_PROCESS_READY;
    kernel->processes[slot].entry = entry;
    kernel->next_pid = pid + 1;
    *pid_out = pid;
    return CAIRN_OK;
}

int cairn_schedule(struct cairn_kernel *kernel, int *pid_out)
{
    int cursor;
    int chosen = -1;
    int step;

    if (kernel == (struct cairn_kernel *)0 || pid_out == (int *)0) {
        return CAIRN_ERR_INVALID;
    }
    cursor = kernel->current_slot;
    if (cursor < -1 || cursor >= CAIRN_MAX_PROCESSES) {
        return CAIRN_ERR_CORRUPT;
    }

    for (step = 1; step <= CAIRN_MAX_PROCESSES; ++step) {
        int slot = (cursor + step) % CAIRN_MAX_PROCESSES;
        enum cairn_process_state state = kernel->processes[slot].state;

        if (state == CAIRN_PROCESS_READY ||
            (slot == cursor && state == CAIRN_PROCESS_RUNNING)) {
            chosen = slot;
            break;
        }
    }
    if (chosen < 0) {
        return CAIRN_ERR_NO_RUNNABLE;
    }
    if (cursor >= 0 && kernel->processes[cursor].state == CAIRN_PROCESS_RUNNING) {
        kernel->processes[cursor].state = CAIRN_PROCESS_READY;
    }
    kernel->processes[chosen].state = CAIRN_PROCESS_RUNNING;
    kernel->current_slot = chosen;
    *pid_out = kernel->processes[chosen].pid;
    return CAIRN_OK;
}

int cairn_block_current(struct cairn_kernel *kernel)
{
    int slot;

    if (kernel == (struct cairn_kernel *)0) {
        return CAIRN_ERR_INVALID;
    }
    slot = kernel->current_slot;
    if (slot < 0 || slot >= CAIRN_MAX_PROCESSES ||
        kernel->processes[slot].state != CAIRN_PROCESS_RUNNING) {
        return CAIRN_ERR_BAD_STATE;
    }
    kernel->processes[slot].state = CAIRN_PROCESS_BLOCKED;
    return CAIRN_OK;
}

int cairn_wake(struct cairn_kernel *kernel, int pid)
{
    int slot;

    if (kernel == (struct cairn_kernel *)0 || pid <= 0) {
        return CAIRN_ERR_INVALID;
    }
    slot = find_process(kernel, pid);
    if (slot < 0) {
        return CAIRN_ERR_NOT_FOUND;
    }
    if (kernel->processes[slot].state != CAIRN_PROCESS_BLOCKED) {
        return CAIRN_ERR_BAD_STATE;
    }
    kernel->processes[slot].state = CAIRN_PROCESS_READY;
    return CAIRN_OK;
}

int cairn_exit_current(struct cairn_kernel *kernel, int exit_code)
{
    int slot;
    int i;
    struct cairn_process *process;

    if (kernel == (struct cairn_kernel *)0) {
        return CAIRN_ERR_INVALID;
    }
    slot = kernel->current_slot;
    if (slot < 0 || slot >= CAIRN_MAX_PROCESSES ||
        kernel->processes[slot].state != CAIRN_PROCESS_RUNNING) {
        return CAIRN_ERR_BAD_STATE;
    }
    process = &kernel->processes[slot];
    for (i = 0; i < CAIRN_MAX_MAPPINGS; ++i) {
        if (process->mappings[i].present == 1) {
            cairn_u32 frame = process->mappings[i].frame;
            if (frame >= CAIRN_MAX_FRAMES || kernel->frame_owner[frame] != process->pid) {
                return CAIRN_ERR_CORRUPT;
            }
        }
    }
    for (i = 0; i < CAIRN_MAX_MAPPINGS; ++i) {
        if (process->mappings[i].present == 1) {
            kernel->frame_owner[process->mappings[i].frame] = -1;
            clear_bytes(&process->mappings[i],
                        (cairn_size)sizeof(process->mappings[i]));
        }
    }
    for (i = 0; i < CAIRN_MAX_FDS; ++i) {
        clear_bytes(&process->descriptors[i],
                    (cairn_size)sizeof(process->descriptors[i]));
    }
    process->exit_code = exit_code;
    process->state = CAIRN_PROCESS_EXITED;
    return CAIRN_OK;
}

int cairn_process_state(const struct cairn_kernel *kernel, int pid,
                        enum cairn_process_state *state_out)
{
    int slot;

    if (kernel == (const struct cairn_kernel *)0 || pid <= 0 ||
        state_out == (enum cairn_process_state *)0) {
        return CAIRN_ERR_INVALID;
    }
    slot = find_process(kernel, pid);
    if (slot < 0) {
        return CAIRN_ERR_NOT_FOUND;
    }
    *state_out = kernel->processes[slot].state;
    return CAIRN_OK;
}

int cairn_map(struct cairn_kernel *kernel, int pid, cairn_u32 virtual_address,
              cairn_u32 frame, int writable)
{
    int slot;
    int free_mapping = -1;
    int i;
    cairn_u32 virtual_page;
    struct cairn_process *process;

    if (kernel == (struct cairn_kernel *)0 || pid <= 0 ||
        virtual_address >= CAIRN_USER_TOP ||
        (virtual_address % CAIRN_PAGE_SIZE) != 0U || frame >= CAIRN_MAX_FRAMES ||
        (writable != 0 && writable != 1)) {
        return CAIRN_ERR_INVALID;
    }
    slot = find_process(kernel, pid);
    if (slot < 0) {
        return CAIRN_ERR_NOT_FOUND;
    }
    process = &kernel->processes[slot];
    if (!process_is_live(process)) {
        return CAIRN_ERR_BAD_STATE;
    }
    virtual_page = virtual_address / CAIRN_PAGE_SIZE;
    for (i = 0; i < CAIRN_MAX_MAPPINGS; ++i) {
        if (process->mappings[i].present == 1 &&
            process->mappings[i].virtual_page == virtual_page) {
            return CAIRN_ERR_EXISTS;
        }
        if (process->mappings[i].present == 0 && free_mapping < 0) {
            free_mapping = i;
        }
    }
    if (kernel->frame_owner[frame] != -1) {
        return CAIRN_ERR_BUSY;
    }
    if (free_mapping < 0) {
        return CAIRN_ERR_NO_SPACE;
    }
    process->mappings[free_mapping].virtual_page = virtual_page;
    process->mappings[free_mapping].frame = frame;
    process->mappings[free_mapping].writable = writable;
    process->mappings[free_mapping].present = 1;
    kernel->frame_owner[frame] = pid;
    return CAIRN_OK;
}

int cairn_unmap(struct cairn_kernel *kernel, int pid, cairn_u32 virtual_address)
{
    int slot;
    int i;
    cairn_u32 virtual_page;
    struct cairn_process *process;

    if (kernel == (struct cairn_kernel *)0 || pid <= 0 ||
        virtual_address >= CAIRN_USER_TOP ||
        (virtual_address % CAIRN_PAGE_SIZE) != 0U) {
        return CAIRN_ERR_INVALID;
    }
    slot = find_process(kernel, pid);
    if (slot < 0) {
        return CAIRN_ERR_NOT_FOUND;
    }
    process = &kernel->processes[slot];
    if (!process_is_live(process)) {
        return CAIRN_ERR_BAD_STATE;
    }
    virtual_page = virtual_address / CAIRN_PAGE_SIZE;
    for (i = 0; i < CAIRN_MAX_MAPPINGS; ++i) {
        struct cairn_mapping *mapping = &process->mappings[i];
        if (mapping->present == 1 && mapping->virtual_page == virtual_page) {
            if (mapping->frame >= CAIRN_MAX_FRAMES ||
                kernel->frame_owner[mapping->frame] != pid) {
                return CAIRN_ERR_CORRUPT;
            }
            kernel->frame_owner[mapping->frame] = -1;
            clear_bytes(mapping, (cairn_size)sizeof(*mapping));
            return CAIRN_OK;
        }
    }
    return CAIRN_ERR_NOT_FOUND;
}

int cairn_translate(const struct cairn_kernel *kernel, int pid, cairn_u32 virtual_address,
                    int write, cairn_u32 *physical_out)
{
    int slot;
    int i;
    cairn_u32 virtual_page;
    cairn_u32 offset;
    const struct cairn_process *process;

    if (kernel == (const struct cairn_kernel *)0 || pid <= 0 ||
        physical_out == (cairn_u32 *)0 || virtual_address >= CAIRN_USER_TOP ||
        (write != 0 && write != 1)) {
        return CAIRN_ERR_INVALID;
    }
    slot = find_process(kernel, pid);
    if (slot < 0) {
        return CAIRN_ERR_NOT_FOUND;
    }
    process = &kernel->processes[slot];
    if (!process_is_live(process)) {
        return CAIRN_ERR_BAD_STATE;
    }
    virtual_page = virtual_address / CAIRN_PAGE_SIZE;
    offset = virtual_address % CAIRN_PAGE_SIZE;
    for (i = 0; i < CAIRN_MAX_MAPPINGS; ++i) {
        const struct cairn_mapping *mapping = &process->mappings[i];
        if (mapping->present == 1 && mapping->virtual_page == virtual_page) {
            if (mapping->frame >= CAIRN_MAX_FRAMES ||
                kernel->frame_owner[mapping->frame] != pid) {
                return CAIRN_ERR_CORRUPT;
            }
            if (write == 1 && mapping->writable != 1) {
                return CAIRN_ERR_PERMISSION;
            }
            *physical_out = mapping->frame * CAIRN_PAGE_SIZE + offset;
            return CAIRN_OK;
        }
    }
    return CAIRN_ERR_NOT_FOUND;
}

int cairn_create(struct cairn_kernel *kernel, const char *name)
{
    int free_slot = -1;
    int i;
    cairn_size length;

    if (kernel == (struct cairn_kernel *)0 || !valid_name(name, &length)) {
        return CAIRN_ERR_INVALID;
    }
    if (find_inode(kernel, name) >= 0) {
        return CAIRN_ERR_EXISTS;
    }
    for (i = 0; i < CAIRN_MAX_FILES; ++i) {
        if (kernel->inodes[i].in_use == 0) {
            free_slot = i;
            break;
        }
    }
    if (free_slot < 0) {
        return CAIRN_ERR_NO_SPACE;
    }
    clear_bytes(&kernel->inodes[free_slot], (cairn_size)sizeof(kernel->inodes[free_slot]));
    copy_bytes(kernel->inodes[free_slot].name, name, length + 1U);
    kernel->inodes[free_slot].in_use = 1;
    return CAIRN_OK;
}

int cairn_unlink(struct cairn_kernel *kernel, const char *name)
{
    int inode_slot;
    int process_slot;
    int fd;

    if (kernel == (struct cairn_kernel *)0 || !valid_name(name, (cairn_size *)0)) {
        return CAIRN_ERR_INVALID;
    }
    inode_slot = find_inode(kernel, name);
    if (inode_slot < 0) {
        return CAIRN_ERR_NOT_FOUND;
    }
    for (process_slot = 0; process_slot < CAIRN_MAX_PROCESSES; ++process_slot) {
        for (fd = 0; fd < CAIRN_MAX_FDS; ++fd) {
            const struct cairn_descriptor *descriptor =
                &kernel->processes[process_slot].descriptors[fd];
            if (descriptor->in_use == 1 && descriptor->inode_slot == inode_slot) {
                return CAIRN_ERR_BUSY;
            }
        }
    }
    clear_bytes(&kernel->inodes[inode_slot],
                (cairn_size)sizeof(kernel->inodes[inode_slot]));
    return CAIRN_OK;
}

int cairn_open(struct cairn_kernel *kernel, int pid, const char *name, int *fd_out)
{
    int process_slot;
    int inode_slot;
    int fd;
    struct cairn_process *process;

    if (kernel == (struct cairn_kernel *)0 || pid <= 0 || fd_out == (int *)0 ||
        !valid_name(name, (cairn_size *)0)) {
        return CAIRN_ERR_INVALID;
    }
    process_slot = find_process(kernel, pid);
    if (process_slot < 0) {
        return CAIRN_ERR_NOT_FOUND;
    }
    process = &kernel->processes[process_slot];
    if (!process_is_live(process)) {
        return CAIRN_ERR_BAD_STATE;
    }
    inode_slot = find_inode(kernel, name);
    if (inode_slot < 0) {
        return CAIRN_ERR_NOT_FOUND;
    }
    for (fd = 0; fd < CAIRN_MAX_FDS; ++fd) {
        if (process->descriptors[fd].in_use == 0) {
            process->descriptors[fd].inode_slot = inode_slot;
            process->descriptors[fd].offset = 0U;
            process->descriptors[fd].in_use = 1;
            *fd_out = fd;
            return CAIRN_OK;
        }
    }
    return CAIRN_ERR_NO_SPACE;
}

int cairn_close(struct cairn_kernel *kernel, int pid, int fd)
{
    struct cairn_descriptor *descriptor;
    int status = descriptor_for(kernel, pid, fd, (struct cairn_process **)0,
                                &descriptor, (struct cairn_inode **)0);

    if (status != CAIRN_OK) {
        return status;
    }
    clear_bytes(descriptor, (cairn_size)sizeof(*descriptor));
    return CAIRN_OK;
}

int cairn_seek(struct cairn_kernel *kernel, int pid, int fd, cairn_size offset)
{
    struct cairn_descriptor *descriptor;
    struct cairn_inode *inode;
    int status = descriptor_for(kernel, pid, fd, (struct cairn_process **)0,
                                &descriptor, &inode);

    if (status != CAIRN_OK) {
        return status;
    }
    if (offset > inode->size) {
        return CAIRN_ERR_INVALID;
    }
    descriptor->offset = offset;
    return CAIRN_OK;
}

int cairn_write(struct cairn_kernel *kernel, int pid, int fd, const void *data,
                cairn_size count, cairn_size *written_out)
{
    struct cairn_descriptor *descriptor;
    struct cairn_inode *inode;
    cairn_size end;
    int status;

    if (written_out == (cairn_size *)0 || (data == (const void *)0 && count != 0U)) {
        return CAIRN_ERR_INVALID;
    }
    status = descriptor_for(kernel, pid, fd, (struct cairn_process **)0,
                            &descriptor, &inode);
    if (status != CAIRN_OK) {
        return status;
    }
    if (descriptor->offset > inode->size || descriptor->offset > CAIRN_FILE_CAP) {
        return CAIRN_ERR_CORRUPT;
    }
    if (count > (cairn_size)CAIRN_FILE_CAP - descriptor->offset) {
        return CAIRN_ERR_NO_SPACE;
    }
    end = descriptor->offset + count;
    copy_bytes(&inode->data[descriptor->offset], data, count);
    descriptor->offset = end;
    if (end > inode->size) {
        inode->size = end;
    }
    *written_out = count;
    return CAIRN_OK;
}

int cairn_read(struct cairn_kernel *kernel, int pid, int fd, void *data,
               cairn_size count, cairn_size *read_out)
{
    struct cairn_descriptor *descriptor;
    struct cairn_inode *inode;
    cairn_size available;
    cairn_size actual;
    int status;

    if (read_out == (cairn_size *)0 || (data == (void *)0 && count != 0U)) {
        return CAIRN_ERR_INVALID;
    }
    status = descriptor_for(kernel, pid, fd, (struct cairn_process **)0,
                            &descriptor, &inode);
    if (status != CAIRN_OK) {
        return status;
    }
    if (descriptor->offset > inode->size || inode->size > CAIRN_FILE_CAP) {
        return CAIRN_ERR_CORRUPT;
    }
    available = inode->size - descriptor->offset;
    actual = count < available ? count : available;
    copy_bytes(data, &inode->data[descriptor->offset], actual);
    descriptor->offset += actual;
    *read_out = actual;
    return CAIRN_OK;
}

int cairn_validate(const struct cairn_kernel *kernel)
{
    int i;
    int j;
    int running_count = 0;

    if (kernel == (const struct cairn_kernel *)0 || kernel->next_pid <= 0 ||
        kernel->current_slot < -1 || kernel->current_slot >= CAIRN_MAX_PROCESSES) {
        return CAIRN_ERR_CORRUPT;
    }

    for (i = 0; i < CAIRN_MAX_PROCESSES; ++i) {
        const struct cairn_process *process = &kernel->processes[i];
        if (process->state < CAIRN_PROCESS_EMPTY || process->state > CAIRN_PROCESS_EXITED) {
            return CAIRN_ERR_CORRUPT;
        }
        if (process->state == CAIRN_PROCESS_EMPTY) {
            if (process->pid != 0) {
                return CAIRN_ERR_CORRUPT;
            }
        } else {
            if (process->pid <= 0 || process->pid >= kernel->next_pid ||
                process->entry >= CAIRN_USER_TOP) {
                return CAIRN_ERR_CORRUPT;
            }
            for (j = i + 1; j < CAIRN_MAX_PROCESSES; ++j) {
                if (kernel->processes[j].state != CAIRN_PROCESS_EMPTY &&
                    kernel->processes[j].pid == process->pid) {
                    return CAIRN_ERR_CORRUPT;
                }
            }
        }
        if (process->state == CAIRN_PROCESS_RUNNING) {
            ++running_count;
            if (kernel->current_slot != i) {
                return CAIRN_ERR_CORRUPT;
            }
        }
        for (j = 0; j < CAIRN_MAX_MAPPINGS; ++j) {
            const struct cairn_mapping *mapping = &process->mappings[j];
            int other;
            if (mapping->present != 0 && mapping->present != 1) {
                return CAIRN_ERR_CORRUPT;
            }
            if (mapping->present == 1) {
                if (!process_is_live(process) ||
                    (mapping->writable != 0 && mapping->writable != 1) ||
                    mapping->virtual_page >= CAIRN_USER_TOP / CAIRN_PAGE_SIZE ||
                    mapping->frame >= CAIRN_MAX_FRAMES ||
                    kernel->frame_owner[mapping->frame] != process->pid) {
                    return CAIRN_ERR_CORRUPT;
                }
                for (other = j + 1; other < CAIRN_MAX_MAPPINGS; ++other) {
                    if (process->mappings[other].present == 1 &&
                        process->mappings[other].virtual_page == mapping->virtual_page) {
                        return CAIRN_ERR_CORRUPT;
                    }
                }
            }
        }
        for (j = 0; j < CAIRN_MAX_FDS; ++j) {
            const struct cairn_descriptor *descriptor = &process->descriptors[j];
            if (descriptor->in_use != 0 && descriptor->in_use != 1) {
                return CAIRN_ERR_CORRUPT;
            }
            if (descriptor->in_use == 1) {
                if (!process_is_live(process) || descriptor->inode_slot < 0 ||
                    descriptor->inode_slot >= CAIRN_MAX_FILES ||
                    kernel->inodes[descriptor->inode_slot].in_use != 1 ||
                    descriptor->offset > kernel->inodes[descriptor->inode_slot].size) {
                    return CAIRN_ERR_CORRUPT;
                }
            }
        }
    }
    if (running_count > 1) {
        return CAIRN_ERR_CORRUPT;
    }
    if (kernel->current_slot >= 0 &&
        kernel->processes[kernel->current_slot].state == CAIRN_PROCESS_EMPTY) {
        return CAIRN_ERR_CORRUPT;
    }

    for (i = 0; i < CAIRN_MAX_FRAMES; ++i) {
        int matches = 0;
        if (kernel->frame_owner[i] < -1 || kernel->frame_owner[i] == 0) {
            return CAIRN_ERR_CORRUPT;
        }
        if (kernel->frame_owner[i] == -1) {
            for (j = 0; j < CAIRN_MAX_PROCESSES; ++j) {
                int mapping_slot;
                for (mapping_slot = 0; mapping_slot < CAIRN_MAX_MAPPINGS; ++mapping_slot) {
                    const struct cairn_mapping *mapping =
                        &kernel->processes[j].mappings[mapping_slot];
                    if (mapping->present == 1 && mapping->frame == (cairn_u32)i) {
                        return CAIRN_ERR_CORRUPT;
                    }
                }
            }
            continue;
        }
        for (j = 0; j < CAIRN_MAX_PROCESSES; ++j) {
            int mapping_slot;
            for (mapping_slot = 0; mapping_slot < CAIRN_MAX_MAPPINGS; ++mapping_slot) {
                const struct cairn_mapping *mapping =
                    &kernel->processes[j].mappings[mapping_slot];
                if (mapping->present == 1 && mapping->frame == (cairn_u32)i &&
                    kernel->processes[j].pid == kernel->frame_owner[i]) {
                    ++matches;
                }
            }
        }
        if (matches != 1) {
            return CAIRN_ERR_CORRUPT;
        }
    }

    for (i = 0; i < CAIRN_MAX_FILES; ++i) {
        const struct cairn_inode *inode = &kernel->inodes[i];
        if (inode->in_use != 0 && inode->in_use != 1) {
            return CAIRN_ERR_CORRUPT;
        }
        if (inode->in_use == 1) {
            if (inode->size > CAIRN_FILE_CAP ||
                !valid_name(inode->name, (cairn_size *)0)) {
                return CAIRN_ERR_CORRUPT;
            }
            for (j = i + 1; j < CAIRN_MAX_FILES; ++j) {
                if (kernel->inodes[j].in_use == 1 &&
                    names_equal(inode->name, kernel->inodes[j].name)) {
                    return CAIRN_ERR_CORRUPT;
                }
            }
        }
    }
    return CAIRN_OK;
}
