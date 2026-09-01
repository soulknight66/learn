#include "tinyarm.h"

#include <limits.h>
#include <string.h>

static bool state_is_live(mk_task_state_t state) {
    return state == MK_TASK_READY || state == MK_TASK_RUNNING ||
           state == MK_TASK_BLOCKED;
}

static int task_slot(const mk_kernel_t *kernel, mk_pid_t pid) {
    size_t index;
    if (kernel == NULL || pid == 0u) {
        return -1;
    }
    for (index = 0u; index < MK_MAX_TASKS; ++index) {
        if (kernel->tasks[index].state != MK_TASK_UNUSED &&
            kernel->tasks[index].pid == pid) {
            return (int)index;
        }
    }
    return -1;
}

static int live_task_slot(const mk_kernel_t *kernel, mk_pid_t pid) {
    int slot = task_slot(kernel, pid);
    if (slot < 0 || !state_is_live(kernel->tasks[slot].state)) {
        return -1;
    }
    return slot;
}

static void release_task_frames(mk_kernel_t *kernel, mk_task_t *task) {
    size_t page;
    for (page = 0u; page < MK_USER_PAGE_COUNT; ++page) {
        mk_pte_t *pte = &task->pages[page];
        if (pte->present != 0u) {
            size_t frame = pte->frame;
            if (frame < MK_FRAME_COUNT) {
                memset(kernel->frames[frame], 0, MK_PAGE_SIZE);
                kernel->frame_used[frame] = 0u;
            }
            memset(pte, 0, sizeof(*pte));
        }
    }
}

static void make_zombie(mk_kernel_t *kernel, int slot, int exit_code) {
    mk_task_t *task = &kernel->tasks[slot];
    release_task_frames(kernel, task);
    task->state = MK_TASK_ZOMBIE;
    task->exit_code = exit_code;
    task->wake_tick = 0u;
    task->quantum_left = 0u;
    if (kernel->current_slot == slot) {
        kernel->current_slot = -1;
    }
}

mk_status_t mk_init(mk_kernel_t *kernel, uint32_t quantum) {
    if (kernel == NULL || quantum == 0u || quantum > MK_MAX_QUANTUM) {
        return MK_ERR_INVALID;
    }
    memset(kernel, 0, sizeof(*kernel));
    kernel->current_slot = -1;
    kernel->last_slot = -1;
    kernel->next_pid = 1u;
    kernel->quantum = quantum;
    return mk_fs_format(kernel);
}

mk_pid_t mk_spawn(mk_kernel_t *kernel, mk_task_fn step, void *userdata) {
    size_t index;
    mk_task_t *task;
    mk_pid_t pid;
    if (kernel == NULL || step == NULL || kernel->next_pid == 0u) {
        return 0u;
    }
    for (index = 0u; index < MK_MAX_TASKS; ++index) {
        if (kernel->tasks[index].state == MK_TASK_UNUSED) {
            break;
        }
    }
    if (index == MK_MAX_TASKS) {
        return 0u;
    }
    pid = kernel->next_pid;
    kernel->next_pid += 1u;
    task = &kernel->tasks[index];
    memset(task, 0, sizeof(*task));
    task->pid = pid;
    task->state = MK_TASK_READY;
    task->step = step;
    task->userdata = userdata;
    return pid;
}

mk_status_t mk_kill(mk_kernel_t *kernel, mk_pid_t pid, int exit_code) {
    int slot;
    if (kernel == NULL || pid == 0u) {
        return MK_ERR_INVALID;
    }
    slot = task_slot(kernel, pid);
    if (slot < 0) {
        return MK_ERR_NOT_FOUND;
    }
    if (!state_is_live(kernel->tasks[slot].state)) {
        return MK_ERR_STATE;
    }
    make_zombie(kernel, slot, exit_code);
    return MK_OK;
}

mk_status_t mk_exit_current(mk_kernel_t *kernel, int exit_code) {
    int slot;
    if (kernel == NULL) {
        return MK_ERR_INVALID;
    }
    slot = kernel->current_slot;
    if (slot < 0 || slot >= (int)MK_MAX_TASKS ||
        kernel->tasks[slot].state != MK_TASK_RUNNING) {
        return MK_ERR_STATE;
    }
    make_zombie(kernel, slot, exit_code);
    return MK_OK;
}

mk_status_t mk_reap(mk_kernel_t *kernel, mk_pid_t pid, int *out_exit_code) {
    int slot;
    int exit_code;
    if (kernel == NULL || pid == 0u) {
        return MK_ERR_INVALID;
    }
    slot = task_slot(kernel, pid);
    if (slot < 0) {
        return MK_ERR_NOT_FOUND;
    }
    if (kernel->tasks[slot].state != MK_TASK_ZOMBIE) {
        return MK_ERR_STATE;
    }
    exit_code = kernel->tasks[slot].exit_code;
    memset(&kernel->tasks[slot], 0, sizeof(kernel->tasks[slot]));
    if (out_exit_code != NULL) {
        *out_exit_code = exit_code;
    }
    return MK_OK;
}

mk_status_t mk_sleep_current(mk_kernel_t *kernel, uint64_t delay) {
    int slot;
    if (kernel == NULL || delay == 0u) {
        return MK_ERR_INVALID;
    }
    slot = kernel->current_slot;
    if (slot < 0 || slot >= (int)MK_MAX_TASKS ||
        kernel->tasks[slot].state != MK_TASK_RUNNING) {
        return MK_ERR_STATE;
    }
    if (UINT64_MAX - kernel->now < delay) {
        return MK_ERR_RANGE;
    }
    kernel->tasks[slot].wake_tick = kernel->now + delay;
    kernel->tasks[slot].state = MK_TASK_BLOCKED;
    kernel->tasks[slot].quantum_left = 0u;
    kernel->current_slot = -1;
    return MK_OK;
}

bool mk_has_live_tasks(const mk_kernel_t *kernel) {
    size_t index;
    if (kernel == NULL) {
        return false;
    }
    for (index = 0u; index < MK_MAX_TASKS; ++index) {
        if (state_is_live(kernel->tasks[index].state)) {
            return true;
        }
    }
    return false;
}

mk_pid_t mk_current_pid(const mk_kernel_t *kernel) {
    int slot;
    if (kernel == NULL) {
        return 0u;
    }
    slot = kernel->current_slot;
    if (slot < 0 || slot >= (int)MK_MAX_TASKS ||
        kernel->tasks[slot].state != MK_TASK_RUNNING) {
        return 0u;
    }
    return kernel->tasks[slot].pid;
}

const mk_task_t *mk_task(const mk_kernel_t *kernel, mk_pid_t pid) {
    int slot = task_slot(kernel, pid);
    return slot < 0 ? NULL : &kernel->tasks[slot];
}

static void wake_due_tasks(mk_kernel_t *kernel) {
    size_t index;
    for (index = 0u; index < MK_MAX_TASKS; ++index) {
        mk_task_t *task = &kernel->tasks[index];
        if (task->state == MK_TASK_BLOCKED && task->wake_tick <= kernel->now) {
            task->state = MK_TASK_READY;
            task->wake_tick = 0u;
        }
    }
}

static int select_task(mk_kernel_t *kernel) {
    size_t distance;
    if (kernel->current_slot >= 0 &&
        kernel->current_slot < (int)MK_MAX_TASKS &&
        kernel->tasks[kernel->current_slot].state == MK_TASK_RUNNING) {
        return kernel->current_slot;
    }
    kernel->current_slot = -1;
    for (distance = 1u; distance <= MK_MAX_TASKS; ++distance) {
        int slot = (kernel->last_slot + (int)distance) % (int)MK_MAX_TASKS;
        if (kernel->tasks[slot].state == MK_TASK_READY) {
            kernel->tasks[slot].state = MK_TASK_RUNNING;
            kernel->tasks[slot].quantum_left = kernel->quantum;
            kernel->current_slot = slot;
            kernel->last_slot = slot;
            return slot;
        }
    }
    return -1;
}

mk_status_t mk_tick(mk_kernel_t *kernel) {
    int slot;
    mk_step_result_t result;
    mk_task_t *task;
    mk_task_fn step;
    mk_pid_t pid;
    void *userdata;
    if (kernel == NULL) {
        return MK_ERR_INVALID;
    }
    if (kernel->now == UINT64_MAX) {
        return MK_ERR_RANGE;
    }
    wake_due_tasks(kernel);
    if (!mk_has_live_tasks(kernel)) {
        return MK_ERR_NOT_FOUND;
    }
    slot = select_task(kernel);
    if (slot < 0) {
        kernel->now += 1u;
        return MK_OK;
    }
    task = &kernel->tasks[slot];
    step = task->step;
    pid = task->pid;
    userdata = task->userdata;
    if (step == NULL) {
        make_zombie(kernel, slot, MK_ERR_STATE);
        kernel->now += 1u;
        return MK_OK;
    }
    result = step(kernel, pid, userdata);
    task = &kernel->tasks[slot];
    if (task->state != MK_TASK_UNUSED && task->pid == pid) {
        task->steps += 1u;
    }
    if (task->state == MK_TASK_RUNNING) {
        if (result == MK_STEP_EXIT) {
            make_zombie(kernel, slot, 0);
        } else if (result == MK_STEP_YIELD) {
            task->state = MK_TASK_READY;
            task->quantum_left = 0u;
            kernel->current_slot = -1;
        } else if (result == MK_STEP_CONTINUE) {
            if (task->quantum_left > 0u) {
                task->quantum_left -= 1u;
            }
            if (task->quantum_left == 0u) {
                task->state = MK_TASK_READY;
                kernel->current_slot = -1;
            }
        } else {
            make_zombie(kernel, slot, MK_ERR_STATE);
        }
    }
    kernel->now += 1u;
    return MK_OK;
}

size_t mk_run(mk_kernel_t *kernel, size_t limit) {
    size_t count = 0u;
    if (kernel == NULL) {
        return 0u;
    }
    while (count < limit && mk_tick(kernel) == MK_OK) {
        count += 1u;
    }
    return count;
}

static mk_status_t validate_vm_range(const mk_kernel_t *kernel, int slot,
                                     uintptr_t virtual_address, size_t length,
                                     uint8_t required_flags) {
    size_t first_page;
    size_t last_page;
    size_t page;
    if (virtual_address > (uintptr_t)MK_USER_SIZE) {
        return MK_ERR_RANGE;
    }
    if (length == 0u) {
        return MK_OK;
    }
    if (virtual_address >= (uintptr_t)MK_USER_SIZE ||
        length > (size_t)((uintptr_t)MK_USER_SIZE - virtual_address)) {
        return MK_ERR_RANGE;
    }
    first_page = (size_t)(virtual_address / MK_PAGE_SIZE);
    last_page = (size_t)((virtual_address + length - 1u) / MK_PAGE_SIZE);
    for (page = first_page; page <= last_page; ++page) {
        const mk_pte_t *pte = &kernel->tasks[slot].pages[page];
        if (pte->present == 0u || pte->frame >= MK_FRAME_COUNT ||
            kernel->frame_used[pte->frame] == 0u) {
            return MK_ERR_NOT_FOUND;
        }
        if ((pte->flags & required_flags) != required_flags) {
            return MK_ERR_PERMISSION;
        }
    }
    return MK_OK;
}

mk_status_t mk_vm_map(mk_kernel_t *kernel, mk_pid_t pid, uintptr_t virtual_address,
                      uint8_t flags) {
    int slot;
    size_t page;
    size_t frame;
    if (kernel == NULL || pid == 0u) {
        return MK_ERR_INVALID;
    }
    if (virtual_address >= (uintptr_t)MK_USER_SIZE ||
        virtual_address % MK_PAGE_SIZE != 0u) {
        return MK_ERR_RANGE;
    }
    if (flags == 0u || (flags & (uint8_t)~(MK_VM_READ | MK_VM_WRITE)) != 0u) {
        return MK_ERR_INVALID;
    }
    slot = live_task_slot(kernel, pid);
    if (slot < 0) {
        return MK_ERR_NOT_FOUND;
    }
    page = (size_t)(virtual_address / MK_PAGE_SIZE);
    if (kernel->tasks[slot].pages[page].present != 0u) {
        return MK_ERR_EXISTS;
    }
    for (frame = 0u; frame < MK_FRAME_COUNT; ++frame) {
        if (kernel->frame_used[frame] == 0u) {
            break;
        }
    }
    if (frame == MK_FRAME_COUNT) {
        return MK_ERR_NO_SPACE;
    }
    memset(kernel->frames[frame], 0, MK_PAGE_SIZE);
    kernel->frame_used[frame] = 1u;
    kernel->tasks[slot].pages[page].present = 1u;
    kernel->tasks[slot].pages[page].flags = flags;
    kernel->tasks[slot].pages[page].frame = (uint16_t)frame;
    return MK_OK;
}

mk_status_t mk_vm_unmap(mk_kernel_t *kernel, mk_pid_t pid, uintptr_t virtual_address) {
    int slot;
    size_t page;
    mk_pte_t *pte;
    if (kernel == NULL || pid == 0u) {
        return MK_ERR_INVALID;
    }
    if (virtual_address >= (uintptr_t)MK_USER_SIZE ||
        virtual_address % MK_PAGE_SIZE != 0u) {
        return MK_ERR_RANGE;
    }
    slot = live_task_slot(kernel, pid);
    if (slot < 0) {
        return MK_ERR_NOT_FOUND;
    }
    page = (size_t)(virtual_address / MK_PAGE_SIZE);
    pte = &kernel->tasks[slot].pages[page];
    if (pte->present == 0u) {
        return MK_ERR_NOT_FOUND;
    }
    if (pte->frame < MK_FRAME_COUNT) {
        memset(kernel->frames[pte->frame], 0, MK_PAGE_SIZE);
        kernel->frame_used[pte->frame] = 0u;
    }
    memset(pte, 0, sizeof(*pte));
    return MK_OK;
}

mk_status_t mk_vm_read(const mk_kernel_t *kernel, mk_pid_t pid, uintptr_t virtual_address,
                       void *destination, size_t length) {
    int slot;
    mk_status_t status;
    size_t copied = 0u;
    if (kernel == NULL || pid == 0u || (length > 0u && destination == NULL)) {
        return MK_ERR_INVALID;
    }
    slot = live_task_slot(kernel, pid);
    if (slot < 0) {
        return MK_ERR_NOT_FOUND;
    }
    status = validate_vm_range(kernel, slot, virtual_address, length, MK_VM_READ);
    if (status != MK_OK) {
        return status;
    }
    while (copied < length) {
        uintptr_t address = virtual_address + copied;
        size_t page = (size_t)(address / MK_PAGE_SIZE);
        size_t offset = (size_t)(address % MK_PAGE_SIZE);
        size_t chunk = MK_PAGE_SIZE - offset;
        size_t frame = kernel->tasks[slot].pages[page].frame;
        if (chunk > length - copied) {
            chunk = length - copied;
        }
        memmove((uint8_t *)destination + copied, &kernel->frames[frame][offset], chunk);
        copied += chunk;
    }
    return MK_OK;
}

mk_status_t mk_vm_write(mk_kernel_t *kernel, mk_pid_t pid, uintptr_t virtual_address,
                        const void *source, size_t length) {
    int slot;
    mk_status_t status;
    size_t copied = 0u;
    if (kernel == NULL || pid == 0u || (length > 0u && source == NULL)) {
        return MK_ERR_INVALID;
    }
    slot = live_task_slot(kernel, pid);
    if (slot < 0) {
        return MK_ERR_NOT_FOUND;
    }
    status = validate_vm_range(kernel, slot, virtual_address, length, MK_VM_WRITE);
    if (status != MK_OK) {
        return status;
    }
    while (copied < length) {
        uintptr_t address = virtual_address + copied;
        size_t page = (size_t)(address / MK_PAGE_SIZE);
        size_t offset = (size_t)(address % MK_PAGE_SIZE);
        size_t chunk = MK_PAGE_SIZE - offset;
        size_t frame = kernel->tasks[slot].pages[page].frame;
        if (chunk > length - copied) {
            chunk = length - copied;
        }
        memmove(&kernel->frames[frame][offset], (const uint8_t *)source + copied, chunk);
        copied += chunk;
    }
    return MK_OK;
}

size_t mk_vm_free_frames(const mk_kernel_t *kernel) {
    size_t frame;
    size_t count = 0u;
    if (kernel == NULL) {
        return 0u;
    }
    for (frame = 0u; frame < MK_FRAME_COUNT; ++frame) {
        if (kernel->frame_used[frame] == 0u) {
            count += 1u;
        }
    }
    return count;
}

static bool path_character(char value) {
    return (value >= 'a' && value <= 'z') ||
           (value >= 'A' && value <= 'Z') ||
           (value >= '0' && value <= '9') || value == '.' || value == '_' ||
           value == '-';
}

static bool valid_path(const char *path, size_t *out_length) {
    size_t index;
    if (path == NULL || path[0] != '/') {
        return false;
    }
    for (index = 1u; index <= MK_PATH_MAX; ++index) {
        if (path[index] == '\0') {
            if (index == 1u) {
                return false;
            }
            if (out_length != NULL) {
                *out_length = index;
            }
            return true;
        }
        if (!path_character(path[index])) {
            return false;
        }
    }
    if (path[MK_PATH_MAX + 1u] != '\0') {
        return false;
    }
    if (out_length != NULL) {
        *out_length = MK_PATH_MAX + 1u;
    }
    return true;
}

static int inode_slot(const mk_kernel_t *kernel, const char *path) {
    size_t index;
    for (index = 0u; index < MK_MAX_FILES; ++index) {
        if (kernel->inodes[index].used != 0u &&
            strcmp(kernel->inodes[index].path, path) == 0) {
            return (int)index;
        }
    }
    return -1;
}

mk_status_t mk_fs_format(mk_kernel_t *kernel) {
    size_t inode;
    size_t direct;
    if (kernel == NULL) {
        return MK_ERR_INVALID;
    }
    memset(kernel->inodes, 0, sizeof(kernel->inodes));
    memset(kernel->block_used, 0, sizeof(kernel->block_used));
    memset(kernel->blocks, 0, sizeof(kernel->blocks));
    for (inode = 0u; inode < MK_MAX_FILES; ++inode) {
        for (direct = 0u; direct < MK_FS_DIRECT_BLOCKS; ++direct) {
            kernel->inodes[inode].blocks[direct] = -1;
        }
    }
    return MK_OK;
}

mk_status_t mk_fs_create(mk_kernel_t *kernel, const char *path) {
    size_t path_length;
    size_t index;
    size_t direct;
    mk_inode_t *inode;
    if (kernel == NULL || !valid_path(path, &path_length)) {
        return MK_ERR_INVALID;
    }
    if (inode_slot(kernel, path) >= 0) {
        return MK_ERR_EXISTS;
    }
    for (index = 0u; index < MK_MAX_FILES; ++index) {
        if (kernel->inodes[index].used == 0u) {
            break;
        }
    }
    if (index == MK_MAX_FILES) {
        return MK_ERR_NO_SPACE;
    }
    inode = &kernel->inodes[index];
    memset(inode, 0, sizeof(*inode));
    inode->used = 1u;
    memcpy(inode->path, path, path_length + 1u);
    for (direct = 0u; direct < MK_FS_DIRECT_BLOCKS; ++direct) {
        inode->blocks[direct] = -1;
    }
    return MK_OK;
}

static bool block_selected(const int16_t selected[MK_FS_DIRECT_BLOCKS],
                           size_t count, size_t block) {
    size_t index;
    for (index = 0u; index < count; ++index) {
        if (selected[index] == (int16_t)block) {
            return true;
        }
    }
    return false;
}

mk_status_t mk_fs_write(mk_kernel_t *kernel, const char *path, const void *data,
                        size_t length) {
    uint8_t staged[MK_FS_MAX_FILE_SIZE];
    int16_t selected[MK_FS_DIRECT_BLOCKS];
    int slot;
    mk_inode_t *inode;
    size_t old_count;
    size_t needed;
    size_t reused;
    size_t index;
    size_t block;
    size_t copied;
    if (kernel == NULL || !valid_path(path, NULL) ||
        (length > 0u && data == NULL)) {
        return MK_ERR_INVALID;
    }
    if (length > MK_FS_MAX_FILE_SIZE) {
        return MK_ERR_RANGE;
    }
    slot = inode_slot(kernel, path);
    if (slot < 0) {
        return MK_ERR_NOT_FOUND;
    }
    if (length > 0u) {
        memmove(staged, data, length);
    }
    inode = &kernel->inodes[slot];
    old_count = (inode->size + MK_FS_BLOCK_SIZE - 1u) / MK_FS_BLOCK_SIZE;
    needed = (length + MK_FS_BLOCK_SIZE - 1u) / MK_FS_BLOCK_SIZE;
    for (index = 0u; index < MK_FS_DIRECT_BLOCKS; ++index) {
        selected[index] = -1;
    }
    reused = old_count < needed ? old_count : needed;
    for (index = 0u; index < reused; ++index) {
        selected[index] = inode->blocks[index];
    }
    for (index = reused; index < needed; ++index) {
        for (block = 0u; block < MK_FS_BLOCK_COUNT; ++block) {
            if (kernel->block_used[block] == 0u &&
                !block_selected(selected, index, block)) {
                break;
            }
        }
        if (block == MK_FS_BLOCK_COUNT) {
            return MK_ERR_NO_SPACE;
        }
        selected[index] = (int16_t)block;
    }
    copied = 0u;
    for (index = 0u; index < needed; ++index) {
        size_t chunk = length - copied;
        block = (size_t)selected[index];
        if (chunk > MK_FS_BLOCK_SIZE) {
            chunk = MK_FS_BLOCK_SIZE;
        }
        memset(kernel->blocks[block], 0, MK_FS_BLOCK_SIZE);
        if (chunk > 0u) {
            memcpy(kernel->blocks[block], &staged[copied], chunk);
        }
        kernel->block_used[block] = 1u;
        copied += chunk;
    }
    for (index = needed; index < old_count; ++index) {
        block = (size_t)inode->blocks[index];
        if (block < MK_FS_BLOCK_COUNT) {
            memset(kernel->blocks[block], 0, MK_FS_BLOCK_SIZE);
            kernel->block_used[block] = 0u;
        }
    }
    for (index = 0u; index < MK_FS_DIRECT_BLOCKS; ++index) {
        inode->blocks[index] = selected[index];
    }
    inode->size = length;
    return MK_OK;
}

mk_status_t mk_fs_read(const mk_kernel_t *kernel, const char *path, size_t offset,
                       void *destination, size_t capacity, size_t *out_read) {
    int slot;
    const mk_inode_t *inode;
    size_t amount;
    size_t copied = 0u;
    if (kernel == NULL || !valid_path(path, NULL) || out_read == NULL ||
        (capacity > 0u && destination == NULL)) {
        return MK_ERR_INVALID;
    }
    slot = inode_slot(kernel, path);
    if (slot < 0) {
        return MK_ERR_NOT_FOUND;
    }
    inode = &kernel->inodes[slot];
    amount = offset < inode->size ? inode->size - offset : 0u;
    if (amount > capacity) {
        amount = capacity;
    }
    while (copied < amount) {
        size_t file_position = offset + copied;
        size_t direct = file_position / MK_FS_BLOCK_SIZE;
        size_t block_offset = file_position % MK_FS_BLOCK_SIZE;
        size_t chunk = MK_FS_BLOCK_SIZE - block_offset;
        size_t block = (size_t)inode->blocks[direct];
        if (chunk > amount - copied) {
            chunk = amount - copied;
        }
        memmove((uint8_t *)destination + copied,
                &kernel->blocks[block][block_offset], chunk);
        copied += chunk;
    }
    *out_read = amount;
    return MK_OK;
}

mk_status_t mk_fs_stat(const mk_kernel_t *kernel, const char *path, size_t *out_size) {
    int slot;
    if (kernel == NULL || !valid_path(path, NULL) || out_size == NULL) {
        return MK_ERR_INVALID;
    }
    slot = inode_slot(kernel, path);
    if (slot < 0) {
        return MK_ERR_NOT_FOUND;
    }
    *out_size = kernel->inodes[slot].size;
    return MK_OK;
}

mk_status_t mk_fs_unlink(mk_kernel_t *kernel, const char *path) {
    int slot;
    mk_inode_t *inode;
    size_t index;
    if (kernel == NULL || !valid_path(path, NULL)) {
        return MK_ERR_INVALID;
    }
    slot = inode_slot(kernel, path);
    if (slot < 0) {
        return MK_ERR_NOT_FOUND;
    }
    inode = &kernel->inodes[slot];
    for (index = 0u; index < MK_FS_DIRECT_BLOCKS; ++index) {
        if (inode->blocks[index] >= 0 &&
            (size_t)inode->blocks[index] < MK_FS_BLOCK_COUNT) {
            size_t block = (size_t)inode->blocks[index];
            memset(kernel->blocks[block], 0, MK_FS_BLOCK_SIZE);
            kernel->block_used[block] = 0u;
        }
    }
    memset(inode, 0, sizeof(*inode));
    for (index = 0u; index < MK_FS_DIRECT_BLOCKS; ++index) {
        inode->blocks[index] = -1;
    }
    return MK_OK;
}

size_t mk_fs_free_blocks(const mk_kernel_t *kernel) {
    size_t block;
    size_t count = 0u;
    if (kernel == NULL) {
        return 0u;
    }
    for (block = 0u; block < MK_FS_BLOCK_COUNT; ++block) {
        if (kernel->block_used[block] == 0u) {
            count += 1u;
        }
    }
    return count;
}
