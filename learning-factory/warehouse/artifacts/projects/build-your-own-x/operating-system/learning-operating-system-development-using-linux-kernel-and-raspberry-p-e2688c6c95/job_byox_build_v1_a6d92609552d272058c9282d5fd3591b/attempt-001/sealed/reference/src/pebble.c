#include "pebble.h"

#include <limits.h>
#include <string.h>

#define PEBBLE_PAGE_PUBLIC_FLAGS (PEBBLE_PAGE_READ | PEBBLE_PAGE_WRITE)
#define PEBBLE_PAGE_ALL_FLAGS                                                   \
    (PEBBLE_PAGE_READ | PEBBLE_PAGE_WRITE | PEBBLE_PAGE_COW |                 \
     PEBBLE_PAGE_PRESENT)
#define PEBBLE_OPEN_ALL_FLAGS                                                   \
    (PEBBLE_OPEN_READ | PEBBLE_OPEN_WRITE | PEBBLE_OPEN_CREATE |              \
     PEBBLE_OPEN_TRUNCATE)

static int state_is_live(pebble_process_state_t state)
{
    return state == PEBBLE_PROC_READY || state == PEBBLE_PROC_RUNNING ||
           state == PEBBLE_PROC_BLOCKED;
}

static pebble_process_t *find_process(pebble_kernel_t *kernel, int32_t pid,
                                      size_t *slot_out)
{
    size_t slot;

    if (kernel == NULL || pid <= 0) {
        return NULL;
    }
    for (slot = 0u; slot < PEBBLE_MAX_PROCESSES; ++slot) {
        if (kernel->processes[slot].state != PEBBLE_PROC_UNUSED &&
            kernel->processes[slot].pid == pid) {
            if (slot_out != NULL) {
                *slot_out = slot;
            }
            return &kernel->processes[slot];
        }
    }
    return NULL;
}

static const pebble_process_t *find_process_const(const pebble_kernel_t *kernel,
                                                  int32_t pid,
                                                  size_t *slot_out)
{
    size_t slot;

    if (kernel == NULL || pid <= 0) {
        return NULL;
    }
    for (slot = 0u; slot < PEBBLE_MAX_PROCESSES; ++slot) {
        if (kernel->processes[slot].state != PEBBLE_PROC_UNUSED &&
            kernel->processes[slot].pid == pid) {
            if (slot_out != NULL) {
                *slot_out = slot;
            }
            return &kernel->processes[slot];
        }
    }
    return NULL;
}

static int find_free_process_slot(const pebble_kernel_t *kernel, size_t *slot_out)
{
    size_t slot;

    for (slot = 0u; slot < PEBBLE_MAX_PROCESSES; ++slot) {
        if (kernel->processes[slot].state == PEBBLE_PROC_UNUSED) {
            *slot_out = slot;
            return PEBBLE_OK;
        }
    }
    return PEBBLE_ERR_NO_SPACE;
}

static int find_free_frame(const pebble_kernel_t *kernel, size_t *frame_out)
{
    size_t frame;

    for (frame = 0u; frame < PEBBLE_PHYSICAL_FRAMES; ++frame) {
        if (kernel->frames[frame].refs == 0u) {
            *frame_out = frame;
            return PEBBLE_OK;
        }
    }
    return PEBBLE_ERR_NO_SPACE;
}

static size_t count_free_frames(const pebble_kernel_t *kernel)
{
    size_t frame;
    size_t count = 0u;

    for (frame = 0u; frame < PEBBLE_PHYSICAL_FRAMES; ++frame) {
        if (kernel->frames[frame].refs == 0u) {
            ++count;
        }
    }
    return count;
}

static void release_page(pebble_kernel_t *kernel, pebble_pte_t *page)
{
    pebble_frame_t *frame;

    if ((page->flags & PEBBLE_PAGE_PRESENT) == 0u) {
        return;
    }
    frame = &kernel->frames[page->frame];
    --frame->refs;
    if (frame->refs == 0u) {
        memset(frame, 0, sizeof(*frame));
    }
    memset(page, 0, sizeof(*page));
}

static void close_descriptor(pebble_kernel_t *kernel, pebble_fd_t *descriptor)
{
    pebble_file_t *file = &kernel->files[descriptor->file_index];

    --file->open_count;
    memset(descriptor, 0, sizeof(*descriptor));
}

static int valid_name(const char *name, size_t *length_out)
{
    size_t length;

    if (name == NULL) {
        return 0;
    }
    for (length = 0u; length <= PEBBLE_MAX_NAME; ++length) {
        if (name[length] == '\0') {
            break;
        }
        if (name[length] == '/') {
            return 0;
        }
    }
    if (length == 0u || length > PEBBLE_MAX_NAME) {
        return 0;
    }
    if ((length == 1u && name[0] == '.') ||
        (length == 2u && name[0] == '.' && name[1] == '.')) {
        return 0;
    }
    if (length_out != NULL) {
        *length_out = length;
    }
    return 1;
}

static int find_file(const pebble_kernel_t *kernel, const char *name,
                     size_t name_length, size_t *file_out)
{
    size_t file;

    for (file = 0u; file < PEBBLE_MAX_FILES; ++file) {
        if (kernel->files[file].used != 0u &&
            memcmp(kernel->files[file].name, name, name_length) == 0 &&
            kernel->files[file].name[name_length] == '\0') {
            *file_out = file;
            return PEBBLE_OK;
        }
    }
    return PEBBLE_ERR_NOT_FOUND;
}

static int find_free_file(const pebble_kernel_t *kernel, size_t *file_out)
{
    size_t file;

    for (file = 0u; file < PEBBLE_MAX_FILES; ++file) {
        if (kernel->files[file].used == 0u) {
            *file_out = file;
            return PEBBLE_OK;
        }
    }
    return PEBBLE_ERR_NO_SPACE;
}

static int find_free_descriptor(const pebble_process_t *process, size_t *fd_out)
{
    size_t fd;

    for (fd = 0u; fd < PEBBLE_MAX_FDS; ++fd) {
        if (process->fds[fd].used == 0u) {
            *fd_out = fd;
            return PEBBLE_OK;
        }
    }
    return PEBBLE_ERR_NO_SPACE;
}

static void reset_file_cursors(pebble_kernel_t *kernel, size_t file_index)
{
    size_t process;

    for (process = 0u; process < PEBBLE_MAX_PROCESSES; ++process) {
        size_t fd;
        for (fd = 0u; fd < PEBBLE_MAX_FDS; ++fd) {
            pebble_fd_t *descriptor = &kernel->processes[process].fds[fd];
            if (descriptor->used != 0u &&
                descriptor->file_index == file_index) {
                descriptor->cursor = 0u;
            }
        }
    }
}

static int validate_range(const pebble_process_t *process, uint32_t address,
                          size_t length, uint8_t permission)
{
    const uint32_t address_space =
        (uint32_t)(PEBBLE_PAGE_SIZE * PEBBLE_VIRTUAL_PAGES);
    size_t first_page;
    size_t last_page;
    size_t page;

    if (address > address_space || length > (size_t)(address_space - address)) {
        return PEBBLE_ERR_INVALID;
    }
    if (length == 0u) {
        return PEBBLE_OK;
    }
    first_page = (size_t)(address / PEBBLE_PAGE_SIZE);
    last_page = (size_t)((address + (uint32_t)length - 1u) / PEBBLE_PAGE_SIZE);
    for (page = first_page; page <= last_page; ++page) {
        uint8_t flags = process->pages[page].flags;
        if ((flags & PEBBLE_PAGE_PRESENT) == 0u) {
            return PEBBLE_ERR_NOT_FOUND;
        }
        if (permission == PEBBLE_PAGE_READ &&
            (flags & PEBBLE_PAGE_READ) == 0u) {
            return PEBBLE_ERR_PERMISSION;
        }
        if (permission == PEBBLE_PAGE_WRITE &&
            (flags & (PEBBLE_PAGE_WRITE | PEBBLE_PAGE_COW)) == 0u) {
            return PEBBLE_ERR_PERMISSION;
        }
    }
    return PEBBLE_OK;
}

static int get_descriptor(pebble_kernel_t *kernel, int32_t pid, int32_t fd,
                          pebble_process_t **process_out,
                          pebble_fd_t **descriptor_out)
{
    pebble_process_t *process;

    if (kernel == NULL || pid <= 0) {
        return PEBBLE_ERR_INVALID;
    }
    process = find_process(kernel, pid, NULL);
    if (process == NULL) {
        return PEBBLE_ERR_NOT_FOUND;
    }
    if (!state_is_live(process->state)) {
        return PEBBLE_ERR_STATE;
    }
    if (fd < 0 || (uint32_t)fd >= PEBBLE_MAX_FDS) {
        return PEBBLE_ERR_BAD_FD;
    }
    if (process->fds[(size_t)fd].used == 0u) {
        return PEBBLE_ERR_BAD_FD;
    }
    if (process->fds[(size_t)fd].file_index >= PEBBLE_MAX_FILES ||
        kernel->files[process->fds[(size_t)fd].file_index].used == 0u) {
        return PEBBLE_ERR_CORRUPT;
    }
    if (process_out != NULL) {
        *process_out = process;
    }
    *descriptor_out = &process->fds[(size_t)fd];
    return PEBBLE_OK;
}

static int get_descriptor_const(const pebble_kernel_t *kernel, int32_t pid,
                                int32_t fd, const pebble_fd_t **descriptor_out)
{
    const pebble_process_t *process;

    if (kernel == NULL || pid <= 0) {
        return PEBBLE_ERR_INVALID;
    }
    process = find_process_const(kernel, pid, NULL);
    if (process == NULL) {
        return PEBBLE_ERR_NOT_FOUND;
    }
    if (!state_is_live(process->state)) {
        return PEBBLE_ERR_STATE;
    }
    if (fd < 0 || (uint32_t)fd >= PEBBLE_MAX_FDS ||
        process->fds[(size_t)fd].used == 0u) {
        return PEBBLE_ERR_BAD_FD;
    }
    if (process->fds[(size_t)fd].file_index >= PEBBLE_MAX_FILES ||
        kernel->files[process->fds[(size_t)fd].file_index].used == 0u) {
        return PEBBLE_ERR_CORRUPT;
    }
    *descriptor_out = &process->fds[(size_t)fd];
    return PEBBLE_OK;
}

void pebble_init(pebble_kernel_t *kernel)
{
    if (kernel == NULL) {
        return;
    }
    memset(kernel, 0, sizeof(*kernel));
    kernel->current_slot = -1;
    kernel->next_pid = 1u;
}

int32_t pebble_process_create(pebble_kernel_t *kernel)
{
    pebble_process_t *process;
    size_t slot;
    int result;

    if (kernel == NULL) {
        return PEBBLE_ERR_INVALID;
    }
    result = find_free_process_slot(kernel, &slot);
    if (result != PEBBLE_OK) {
        return result;
    }
    if (kernel->next_pid == 0u || kernel->next_pid > (uint32_t)INT32_MAX) {
        return PEBBLE_ERR_OVERFLOW;
    }
    process = &kernel->processes[slot];
    memset(process, 0, sizeof(*process));
    process->pid = (int32_t)kernel->next_pid;
    process->state = PEBBLE_PROC_READY;
    ++kernel->next_pid;
    return process->pid;
}

int32_t pebble_process_fork(pebble_kernel_t *kernel, int32_t parent_pid)
{
    pebble_process_t *parent;
    pebble_process_t *child;
    size_t child_slot;
    size_t page;
    size_t fd;
    int result;

    if (kernel == NULL || parent_pid <= 0) {
        return PEBBLE_ERR_INVALID;
    }
    parent = find_process(kernel, parent_pid, NULL);
    if (parent == NULL) {
        return PEBBLE_ERR_NOT_FOUND;
    }
    if (!state_is_live(parent->state)) {
        return PEBBLE_ERR_STATE;
    }
    result = find_free_process_slot(kernel, &child_slot);
    if (result != PEBBLE_OK) {
        return result;
    }
    if (kernel->next_pid == 0u || kernel->next_pid > (uint32_t)INT32_MAX) {
        return PEBBLE_ERR_OVERFLOW;
    }
    for (page = 0u; page < PEBBLE_VIRTUAL_PAGES; ++page) {
        if ((parent->pages[page].flags & PEBBLE_PAGE_PRESENT) != 0u) {
            uint16_t frame = parent->pages[page].frame;
            if (frame >= PEBBLE_PHYSICAL_FRAMES ||
                kernel->frames[frame].refs == 0u) {
                return PEBBLE_ERR_CORRUPT;
            }
            if (kernel->frames[frame].refs == UINT16_MAX) {
                return PEBBLE_ERR_OVERFLOW;
            }
        }
    }
    for (fd = 0u; fd < PEBBLE_MAX_FDS; ++fd) {
        if (parent->fds[fd].used != 0u) {
            uint16_t file = parent->fds[fd].file_index;
            if (file >= PEBBLE_MAX_FILES || kernel->files[file].used == 0u ||
                kernel->files[file].open_count == UINT16_MAX) {
                return PEBBLE_ERR_CORRUPT;
            }
        }
    }

    child = &kernel->processes[child_slot];
    memset(child, 0, sizeof(*child));
    child->pid = (int32_t)kernel->next_pid;
    child->state = PEBBLE_PROC_READY;
    for (page = 0u; page < PEBBLE_VIRTUAL_PAGES; ++page) {
        if ((parent->pages[page].flags & PEBBLE_PAGE_PRESENT) != 0u) {
            if ((parent->pages[page].flags & PEBBLE_PAGE_WRITE) != 0u) {
                parent->pages[page].flags =
                    (uint8_t)((parent->pages[page].flags &
                               (uint8_t)~PEBBLE_PAGE_WRITE) |
                              PEBBLE_PAGE_COW);
            }
            child->pages[page] = parent->pages[page];
            ++kernel->frames[parent->pages[page].frame].refs;
        }
    }
    for (fd = 0u; fd < PEBBLE_MAX_FDS; ++fd) {
        if (parent->fds[fd].used != 0u) {
            child->fds[fd] = parent->fds[fd];
            ++kernel->files[parent->fds[fd].file_index].open_count;
        }
    }
    ++kernel->next_pid;
    return child->pid;
}

int pebble_process_block(pebble_kernel_t *kernel, int32_t pid)
{
    pebble_process_t *process;
    size_t slot;

    if (kernel == NULL || pid <= 0) {
        return PEBBLE_ERR_INVALID;
    }
    process = find_process(kernel, pid, &slot);
    if (process == NULL) {
        return PEBBLE_ERR_NOT_FOUND;
    }
    if (process->state != PEBBLE_PROC_READY &&
        process->state != PEBBLE_PROC_RUNNING) {
        return PEBBLE_ERR_STATE;
    }
    process->state = PEBBLE_PROC_BLOCKED;
    if (kernel->current_slot == (int16_t)slot) {
        kernel->current_slot = -1;
    }
    return PEBBLE_OK;
}

int pebble_process_wake(pebble_kernel_t *kernel, int32_t pid)
{
    pebble_process_t *process;

    if (kernel == NULL || pid <= 0) {
        return PEBBLE_ERR_INVALID;
    }
    process = find_process(kernel, pid, NULL);
    if (process == NULL) {
        return PEBBLE_ERR_NOT_FOUND;
    }
    if (process->state != PEBBLE_PROC_BLOCKED) {
        return PEBBLE_ERR_STATE;
    }
    process->state = PEBBLE_PROC_READY;
    return PEBBLE_OK;
}

int pebble_process_exit(pebble_kernel_t *kernel, int32_t pid, int32_t status)
{
    pebble_process_t *process;
    size_t slot;
    size_t page;
    size_t fd;

    if (kernel == NULL || pid <= 0) {
        return PEBBLE_ERR_INVALID;
    }
    process = find_process(kernel, pid, &slot);
    if (process == NULL) {
        return PEBBLE_ERR_NOT_FOUND;
    }
    if (!state_is_live(process->state)) {
        return PEBBLE_ERR_STATE;
    }
    for (page = 0u; page < PEBBLE_VIRTUAL_PAGES; ++page) {
        release_page(kernel, &process->pages[page]);
    }
    for (fd = 0u; fd < PEBBLE_MAX_FDS; ++fd) {
        if (process->fds[fd].used != 0u) {
            close_descriptor(kernel, &process->fds[fd]);
        }
    }
    process->state = PEBBLE_PROC_ZOMBIE;
    process->exit_status = status;
    if (kernel->current_slot == (int16_t)slot) {
        kernel->current_slot = -1;
    }
    return PEBBLE_OK;
}

int pebble_process_reap(pebble_kernel_t *kernel, int32_t pid, int32_t *status_out)
{
    pebble_process_t *process;
    int32_t status;

    if (kernel == NULL || pid <= 0) {
        return PEBBLE_ERR_INVALID;
    }
    process = find_process(kernel, pid, NULL);
    if (process == NULL) {
        return PEBBLE_ERR_NOT_FOUND;
    }
    if (process->state != PEBBLE_PROC_ZOMBIE) {
        return PEBBLE_ERR_STATE;
    }
    status = process->exit_status;
    memset(process, 0, sizeof(*process));
    if (status_out != NULL) {
        *status_out = status;
    }
    return PEBBLE_OK;
}

int32_t pebble_process_state(const pebble_kernel_t *kernel, int32_t pid)
{
    const pebble_process_t *process;

    if (kernel == NULL || pid <= 0) {
        return PEBBLE_ERR_INVALID;
    }
    process = find_process_const(kernel, pid, NULL);
    if (process == NULL) {
        return PEBBLE_ERR_NOT_FOUND;
    }
    return (int32_t)process->state;
}

int32_t pebble_schedule(pebble_kernel_t *kernel)
{
    size_t offset;

    if (kernel == NULL) {
        return PEBBLE_ERR_INVALID;
    }
    if (kernel->ticks == UINT64_MAX) {
        return PEBBLE_ERR_OVERFLOW;
    }
    if (kernel->schedule_cursor >= PEBBLE_MAX_PROCESSES ||
        kernel->current_slot < -1 ||
        kernel->current_slot >= (int16_t)PEBBLE_MAX_PROCESSES) {
        return PEBBLE_ERR_CORRUPT;
    }
    if (kernel->current_slot >= 0) {
        pebble_process_t *current =
            &kernel->processes[(size_t)kernel->current_slot];
        if (current->state != PEBBLE_PROC_RUNNING) {
            return PEBBLE_ERR_CORRUPT;
        }
        current->state = PEBBLE_PROC_READY;
    }
    ++kernel->ticks;
    kernel->current_slot = -1;
    for (offset = 0u; offset < PEBBLE_MAX_PROCESSES; ++offset) {
        size_t slot = (kernel->schedule_cursor + offset) % PEBBLE_MAX_PROCESSES;
        pebble_process_t *candidate = &kernel->processes[slot];
        if (candidate->state == PEBBLE_PROC_READY) {
            candidate->state = PEBBLE_PROC_RUNNING;
            kernel->current_slot = (int16_t)slot;
            kernel->schedule_cursor =
                (uint16_t)((slot + 1u) % PEBBLE_MAX_PROCESSES);
            return candidate->pid;
        }
    }
    return PEBBLE_ERR_NOT_FOUND;
}

int pebble_vm_map(pebble_kernel_t *kernel, int32_t pid, uint16_t virtual_page,
                  uint8_t permissions)
{
    pebble_process_t *process;
    size_t frame;
    int result;

    if (kernel == NULL || pid <= 0 ||
        virtual_page >= PEBBLE_VIRTUAL_PAGES ||
        permissions == 0u ||
        (permissions & (uint8_t)~PEBBLE_PAGE_PUBLIC_FLAGS) != 0u) {
        return PEBBLE_ERR_INVALID;
    }
    process = find_process(kernel, pid, NULL);
    if (process == NULL) {
        return PEBBLE_ERR_NOT_FOUND;
    }
    if (!state_is_live(process->state)) {
        return PEBBLE_ERR_STATE;
    }
    if ((process->pages[virtual_page].flags & PEBBLE_PAGE_PRESENT) != 0u) {
        return PEBBLE_ERR_STATE;
    }
    result = find_free_frame(kernel, &frame);
    if (result != PEBBLE_OK) {
        return result;
    }
    memset(&kernel->frames[frame], 0, sizeof(kernel->frames[frame]));
    kernel->frames[frame].refs = 1u;
    memset(&process->pages[virtual_page], 0,
           sizeof(process->pages[virtual_page]));
    process->pages[virtual_page].frame = (uint16_t)frame;
    process->pages[virtual_page].flags =
        (uint8_t)(permissions | PEBBLE_PAGE_PRESENT);
    return PEBBLE_OK;
}

int pebble_vm_unmap(pebble_kernel_t *kernel, int32_t pid, uint16_t virtual_page)
{
    pebble_process_t *process;

    if (kernel == NULL || pid <= 0 ||
        virtual_page >= PEBBLE_VIRTUAL_PAGES) {
        return PEBBLE_ERR_INVALID;
    }
    process = find_process(kernel, pid, NULL);
    if (process == NULL) {
        return PEBBLE_ERR_NOT_FOUND;
    }
    if (!state_is_live(process->state)) {
        return PEBBLE_ERR_STATE;
    }
    if ((process->pages[virtual_page].flags & PEBBLE_PAGE_PRESENT) == 0u) {
        return PEBBLE_ERR_NOT_FOUND;
    }
    release_page(kernel, &process->pages[virtual_page]);
    return PEBBLE_OK;
}

int32_t pebble_vm_read(const pebble_kernel_t *kernel, int32_t pid, uint32_t address,
                       void *destination, size_t length)
{
    const pebble_process_t *process;
    uint8_t *output = destination;
    size_t copied = 0u;
    int result;

    if (kernel == NULL || pid <= 0 || (length != 0u && destination == NULL)) {
        return PEBBLE_ERR_INVALID;
    }
    process = find_process_const(kernel, pid, NULL);
    if (process == NULL) {
        return PEBBLE_ERR_NOT_FOUND;
    }
    if (!state_is_live(process->state)) {
        return PEBBLE_ERR_STATE;
    }
    result = validate_range(process, address, length, PEBBLE_PAGE_READ);
    if (result != PEBBLE_OK) {
        return result;
    }
    while (copied < length) {
        uint32_t current = address + (uint32_t)copied;
        size_t page = (size_t)(current / PEBBLE_PAGE_SIZE);
        size_t offset = (size_t)(current % PEBBLE_PAGE_SIZE);
        size_t amount = PEBBLE_PAGE_SIZE - offset;
        const pebble_frame_t *frame;
        if (amount > length - copied) {
            amount = length - copied;
        }
        frame = &kernel->frames[process->pages[page].frame];
        memmove(output + copied, frame->data + offset, amount);
        copied += amount;
    }
    return (int32_t)length;
}

int32_t pebble_vm_write(pebble_kernel_t *kernel, int32_t pid, uint32_t address,
                        const void *source, size_t length)
{
    pebble_process_t *process;
    const uint8_t *input = source;
    size_t first_page;
    size_t last_page;
    size_t page;
    size_t frames_needed = 0u;
    size_t copied = 0u;
    int result;

    if (kernel == NULL || pid <= 0 || (length != 0u && source == NULL)) {
        return PEBBLE_ERR_INVALID;
    }
    process = find_process(kernel, pid, NULL);
    if (process == NULL) {
        return PEBBLE_ERR_NOT_FOUND;
    }
    if (!state_is_live(process->state)) {
        return PEBBLE_ERR_STATE;
    }
    result = validate_range(process, address, length, PEBBLE_PAGE_WRITE);
    if (result != PEBBLE_OK || length == 0u) {
        return result == PEBBLE_OK ? 0 : result;
    }
    first_page = (size_t)(address / PEBBLE_PAGE_SIZE);
    last_page =
        (size_t)((address + (uint32_t)length - 1u) / PEBBLE_PAGE_SIZE);
    for (page = first_page; page <= last_page; ++page) {
        pebble_pte_t *entry = &process->pages[page];
        if ((entry->flags & PEBBLE_PAGE_COW) != 0u &&
            kernel->frames[entry->frame].refs > 1u) {
            ++frames_needed;
        }
    }
    if (frames_needed > count_free_frames(kernel)) {
        return PEBBLE_ERR_NO_SPACE;
    }
    for (page = first_page; page <= last_page; ++page) {
        pebble_pte_t *entry = &process->pages[page];
        if ((entry->flags & PEBBLE_PAGE_COW) != 0u) {
            pebble_frame_t *old_frame = &kernel->frames[entry->frame];
            if (old_frame->refs > 1u) {
                size_t new_frame = 0u;
                result = find_free_frame(kernel, &new_frame);
                if (result != PEBBLE_OK) {
                    return PEBBLE_ERR_CORRUPT;
                }
                memset(&kernel->frames[new_frame], 0,
                       sizeof(kernel->frames[new_frame]));
                memcpy(kernel->frames[new_frame].data, old_frame->data,
                       PEBBLE_PAGE_SIZE);
                kernel->frames[new_frame].refs = 1u;
                --old_frame->refs;
                entry->frame = (uint16_t)new_frame;
            }
            entry->flags =
                (uint8_t)((entry->flags | PEBBLE_PAGE_WRITE) &
                          (uint8_t)~PEBBLE_PAGE_COW);
        }
    }
    while (copied < length) {
        uint32_t current = address + (uint32_t)copied;
        size_t current_page = (size_t)(current / PEBBLE_PAGE_SIZE);
        size_t offset = (size_t)(current % PEBBLE_PAGE_SIZE);
        size_t amount = PEBBLE_PAGE_SIZE - offset;
        pebble_frame_t *frame;
        if (amount > length - copied) {
            amount = length - copied;
        }
        frame = &kernel->frames[process->pages[current_page].frame];
        memmove(frame->data + offset, input + copied, amount);
        copied += amount;
    }
    return (int32_t)length;
}

int32_t pebble_fs_open(pebble_kernel_t *kernel, int32_t pid, const char *name,
                       uint8_t flags)
{
    pebble_process_t *process;
    pebble_file_t *file;
    pebble_fd_t *descriptor;
    size_t name_length;
    size_t fd;
    size_t file_index;
    int file_result;
    int creating = 0;

    if (kernel == NULL || pid <= 0 || !valid_name(name, &name_length) ||
        (flags & (uint8_t)~PEBBLE_OPEN_ALL_FLAGS) != 0u ||
        (flags & (PEBBLE_OPEN_READ | PEBBLE_OPEN_WRITE)) == 0u ||
        ((flags & (PEBBLE_OPEN_CREATE | PEBBLE_OPEN_TRUNCATE)) != 0u &&
         (flags & PEBBLE_OPEN_WRITE) == 0u)) {
        return PEBBLE_ERR_INVALID;
    }
    process = find_process(kernel, pid, NULL);
    if (process == NULL) {
        return PEBBLE_ERR_NOT_FOUND;
    }
    if (!state_is_live(process->state)) {
        return PEBBLE_ERR_STATE;
    }
    if (find_free_descriptor(process, &fd) != PEBBLE_OK) {
        return PEBBLE_ERR_NO_SPACE;
    }
    file_result = find_file(kernel, name, name_length, &file_index);
    if (file_result != PEBBLE_OK) {
        if ((flags & PEBBLE_OPEN_CREATE) == 0u) {
            return PEBBLE_ERR_NOT_FOUND;
        }
        if (find_free_file(kernel, &file_index) != PEBBLE_OK) {
            return PEBBLE_ERR_NO_SPACE;
        }
        creating = 1;
    } else if (kernel->files[file_index].open_count == UINT16_MAX) {
        return PEBBLE_ERR_OVERFLOW;
    }

    file = &kernel->files[file_index];
    if (creating != 0) {
        memset(file, 0, sizeof(*file));
        file->used = 1u;
        memcpy(file->name, name, name_length + 1u);
    } else if ((flags & PEBBLE_OPEN_TRUNCATE) != 0u) {
        file->size = 0u;
        memset(file->data, 0, sizeof(file->data));
        reset_file_cursors(kernel, file_index);
    }
    descriptor = &process->fds[fd];
    memset(descriptor, 0, sizeof(*descriptor));
    descriptor->used = 1u;
    descriptor->flags =
        (uint8_t)(flags & (PEBBLE_OPEN_READ | PEBBLE_OPEN_WRITE));
    descriptor->file_index = (uint16_t)file_index;
    ++file->open_count;
    return (int32_t)fd;
}

int pebble_fs_close(pebble_kernel_t *kernel, int32_t pid, int32_t fd)
{
    pebble_fd_t *descriptor;
    int result = get_descriptor(kernel, pid, fd, NULL, &descriptor);

    if (result != PEBBLE_OK) {
        return result;
    }
    if (kernel->files[descriptor->file_index].open_count == 0u) {
        return PEBBLE_ERR_CORRUPT;
    }
    close_descriptor(kernel, descriptor);
    return PEBBLE_OK;
}

int32_t pebble_fs_read(pebble_kernel_t *kernel, int32_t pid, int32_t fd,
                       void *destination, size_t length)
{
    pebble_fd_t *descriptor;
    pebble_file_t *file;
    size_t available;
    size_t amount;
    int result;

    if (length != 0u && destination == NULL) {
        return PEBBLE_ERR_INVALID;
    }
    result = get_descriptor(kernel, pid, fd, NULL, &descriptor);
    if (result != PEBBLE_OK) {
        return result;
    }
    if ((descriptor->flags & PEBBLE_OPEN_READ) == 0u) {
        return PEBBLE_ERR_PERMISSION;
    }
    file = &kernel->files[descriptor->file_index];
    if (descriptor->cursor > file->size) {
        return PEBBLE_ERR_CORRUPT;
    }
    available = (size_t)file->size - descriptor->cursor;
    amount = length < available ? length : available;
    if (amount != 0u) {
        memmove(destination, file->data + descriptor->cursor, amount);
        descriptor->cursor = (uint16_t)(descriptor->cursor + amount);
    }
    return (int32_t)amount;
}

int32_t pebble_fs_write(pebble_kernel_t *kernel, int32_t pid, int32_t fd,
                        const void *source, size_t length)
{
    pebble_fd_t *descriptor;
    pebble_file_t *file;
    size_t end;
    int result;

    if (length != 0u && source == NULL) {
        return PEBBLE_ERR_INVALID;
    }
    result = get_descriptor(kernel, pid, fd, NULL, &descriptor);
    if (result != PEBBLE_OK) {
        return result;
    }
    if ((descriptor->flags & PEBBLE_OPEN_WRITE) == 0u) {
        return PEBBLE_ERR_PERMISSION;
    }
    file = &kernel->files[descriptor->file_index];
    if (descriptor->cursor > file->size) {
        return PEBBLE_ERR_CORRUPT;
    }
    if (length > PEBBLE_MAX_FILE_BYTES - descriptor->cursor) {
        return PEBBLE_ERR_NO_SPACE;
    }
    end = descriptor->cursor + length;
    if (length != 0u) {
        memmove(file->data + descriptor->cursor, source, length);
        descriptor->cursor = (uint16_t)end;
        if (end > file->size) {
            file->size = (uint16_t)end;
        }
    }
    return (int32_t)length;
}

int pebble_fs_seek(pebble_kernel_t *kernel, int32_t pid, int32_t fd,
                   size_t position)
{
    pebble_fd_t *descriptor;
    pebble_file_t *file;
    int result = get_descriptor(kernel, pid, fd, NULL, &descriptor);

    if (result != PEBBLE_OK) {
        return result;
    }
    file = &kernel->files[descriptor->file_index];
    if (position > file->size) {
        return PEBBLE_ERR_INVALID;
    }
    descriptor->cursor = (uint16_t)position;
    return PEBBLE_OK;
}

int pebble_fs_size(const pebble_kernel_t *kernel, int32_t pid, int32_t fd,
                   size_t *size_out)
{
    const pebble_fd_t *descriptor;
    int result;

    if (size_out == NULL) {
        return PEBBLE_ERR_INVALID;
    }
    result = get_descriptor_const(kernel, pid, fd, &descriptor);
    if (result != PEBBLE_OK) {
        return result;
    }
    *size_out = kernel->files[descriptor->file_index].size;
    return PEBBLE_OK;
}

int pebble_fs_unlink(pebble_kernel_t *kernel, const char *name)
{
    size_t name_length;
    size_t file_index;
    int result;

    if (kernel == NULL || !valid_name(name, &name_length)) {
        return PEBBLE_ERR_INVALID;
    }
    result = find_file(kernel, name, name_length, &file_index);
    if (result != PEBBLE_OK) {
        return result;
    }
    if (kernel->files[file_index].open_count != 0u) {
        return PEBBLE_ERR_BUSY;
    }
    memset(&kernel->files[file_index], 0, sizeof(kernel->files[file_index]));
    return PEBBLE_OK;
}

static int bytes_are_zero(const void *object, size_t size)
{
    const uint8_t *bytes = object;
    size_t index;

    for (index = 0u; index < size; ++index) {
        if (bytes[index] != 0u) {
            return 0;
        }
    }
    return 1;
}

static void set_reason(char *why, size_t capacity, const char *message)
{
    size_t index = 0u;

    if (why == NULL || capacity == 0u) {
        return;
    }
    while (index + 1u < capacity && message[index] != '\0') {
        why[index] = message[index];
        ++index;
    }
    why[index] = '\0';
}

#define CHECK_INVARIANT(condition, message)                                      \
    do {                                                                         \
        if (!(condition)) {                                                       \
            set_reason(why, why_capacity, (message));                             \
            return PEBBLE_ERR_CORRUPT;                                            \
        }                                                                        \
    } while (0)

int pebble_check(const pebble_kernel_t *kernel, char *why, size_t why_capacity)
{
    uint16_t derived_refs[PEBBLE_PHYSICAL_FRAMES] = {0u};
    uint16_t derived_opens[PEBBLE_MAX_FILES] = {0u};
    size_t process_index;
    size_t other;
    size_t frame;
    size_t file;
    size_t running_count = 0u;
    int running_slot = -1;

    set_reason(why, why_capacity, "");
    CHECK_INVARIANT(kernel != NULL, "null kernel");
    CHECK_INVARIANT(kernel->current_slot >= -1 &&
                        kernel->current_slot < (int16_t)PEBBLE_MAX_PROCESSES,
                    "bad current slot");
    CHECK_INVARIANT(kernel->schedule_cursor < PEBBLE_MAX_PROCESSES,
                    "bad schedule cursor");
    CHECK_INVARIANT(kernel->next_pid >= 1u &&
                        kernel->next_pid <= (uint32_t)INT32_MAX + 1u,
                    "bad next pid");

    for (process_index = 0u; process_index < PEBBLE_MAX_PROCESSES;
         ++process_index) {
        const pebble_process_t *process = &kernel->processes[process_index];
        size_t page;
        size_t fd;

        if (process->state == PEBBLE_PROC_UNUSED) {
            CHECK_INVARIANT(bytes_are_zero(process, sizeof(*process)),
                            "dirty unused process");
            continue;
        }
        CHECK_INVARIANT(process->state >= PEBBLE_PROC_READY &&
                            process->state <= PEBBLE_PROC_ZOMBIE,
                        "bad process state");
        CHECK_INVARIANT(process->pid > 0 &&
                            (uint32_t)process->pid < kernel->next_pid,
                        "bad process pid");
        for (other = process_index + 1u; other < PEBBLE_MAX_PROCESSES; ++other) {
            CHECK_INVARIANT(kernel->processes[other].state == PEBBLE_PROC_UNUSED ||
                                kernel->processes[other].pid != process->pid,
                            "duplicate pid");
        }
        if (process->state == PEBBLE_PROC_RUNNING) {
            ++running_count;
            running_slot = (int)process_index;
        }
        for (page = 0u; page < PEBBLE_VIRTUAL_PAGES; ++page) {
            const pebble_pte_t *entry = &process->pages[page];
            if ((entry->flags & PEBBLE_PAGE_PRESENT) == 0u) {
                CHECK_INVARIANT(bytes_are_zero(entry, sizeof(*entry)),
                                "dirty absent page");
                continue;
            }
            CHECK_INVARIANT(process->state != PEBBLE_PROC_ZOMBIE,
                            "zombie owns page");
            CHECK_INVARIANT(entry->reserved == 0u, "page reserved bits");
            CHECK_INVARIANT((entry->flags & (uint8_t)~PEBBLE_PAGE_ALL_FLAGS) ==
                                0u,
                            "unknown page flags");
            CHECK_INVARIANT((entry->flags &
                             (PEBBLE_PAGE_READ | PEBBLE_PAGE_WRITE |
                              PEBBLE_PAGE_COW)) != 0u,
                            "page has no access");
            CHECK_INVARIANT((entry->flags &
                             (PEBBLE_PAGE_WRITE | PEBBLE_PAGE_COW)) !=
                                (PEBBLE_PAGE_WRITE | PEBBLE_PAGE_COW),
                            "writable cow page");
            CHECK_INVARIANT(entry->frame < PEBBLE_PHYSICAL_FRAMES,
                            "bad frame index");
            ++derived_refs[entry->frame];
        }
        for (fd = 0u; fd < PEBBLE_MAX_FDS; ++fd) {
            const pebble_fd_t *descriptor = &process->fds[fd];
            if (descriptor->used == 0u) {
                CHECK_INVARIANT(bytes_are_zero(descriptor, sizeof(*descriptor)),
                                "dirty unused descriptor");
                continue;
            }
            CHECK_INVARIANT(process->state != PEBBLE_PROC_ZOMBIE,
                            "zombie owns descriptor");
            CHECK_INVARIANT(descriptor->used == 1u && descriptor->reserved == 0u,
                            "bad descriptor marker");
            CHECK_INVARIANT(descriptor->flags != 0u &&
                                (descriptor->flags &
                                 (uint8_t)~(PEBBLE_OPEN_READ |
                                            PEBBLE_OPEN_WRITE)) == 0u,
                            "bad descriptor flags");
            CHECK_INVARIANT(descriptor->file_index < PEBBLE_MAX_FILES,
                            "bad descriptor file");
            CHECK_INVARIANT(
                kernel->files[descriptor->file_index].used == 1u,
                "descriptor to unused file");
            CHECK_INVARIANT(
                descriptor->cursor <= kernel->files[descriptor->file_index].size,
                "descriptor past eof");
            ++derived_opens[descriptor->file_index];
        }
    }
    CHECK_INVARIANT(running_count <= 1u, "multiple running processes");
    CHECK_INVARIANT((running_count == 0u && kernel->current_slot == -1) ||
                        (running_count == 1u &&
                         kernel->current_slot == running_slot),
                    "running slot mismatch");

    for (frame = 0u; frame < PEBBLE_PHYSICAL_FRAMES; ++frame) {
        CHECK_INVARIANT(kernel->frames[frame].reserved == 0u,
                        "frame reserved bits");
        CHECK_INVARIANT(kernel->frames[frame].refs == derived_refs[frame],
                        "frame refcount mismatch");
        if (derived_refs[frame] == 0u) {
            CHECK_INVARIANT(
                bytes_are_zero(&kernel->frames[frame],
                               sizeof(kernel->frames[frame])),
                "dirty free frame");
        }
    }

    for (file = 0u; file < PEBBLE_MAX_FILES; ++file) {
        const pebble_file_t *record = &kernel->files[file];
        size_t name_length;
        if (record->used == 0u) {
            CHECK_INVARIANT(bytes_are_zero(record, sizeof(*record)),
                            "dirty unused file");
            continue;
        }
        CHECK_INVARIANT(record->used == 1u && record->reserved0 == 0u &&
                            record->reserved1 == 0u,
                        "bad file marker");
        CHECK_INVARIANT(valid_name(record->name, &name_length),
                        "bad file name");
        CHECK_INVARIANT(record->size <= PEBBLE_MAX_FILE_BYTES,
                        "file too large");
        CHECK_INVARIANT(record->open_count == derived_opens[file],
                        "file open count mismatch");
        for (other = file + 1u; other < PEBBLE_MAX_FILES; ++other) {
            const pebble_file_t *candidate = &kernel->files[other];
            if (candidate->used != 0u) {
                size_t other_length;
                CHECK_INVARIANT(valid_name(candidate->name, &other_length),
                                "bad file name");
                CHECK_INVARIANT(
                    name_length != other_length ||
                        memcmp(record->name, candidate->name, name_length) != 0,
                    "duplicate file name");
            }
        }
    }
    return PEBBLE_OK;
}
