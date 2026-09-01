#include "invariant_checks.h"

#define AUDIT_VM_FLAGS (TK_VM_READ | TK_VM_WRITE | TK_VM_EXEC | TK_VM_USER)

static int audit_name(const char name[TK_NAME_CAPACITY])
{
    size_t index;

    for (index = 0; index < TK_NAME_CAPACITY; ++index) {
        if (name[index] == '\0') {
            return index != 0u;
        }
    }
    return 0;
}

static int audit_names_equal(const char left[TK_NAME_CAPACITY],
                             const char right[TK_NAME_CAPACITY])
{
    size_t index;

    for (index = 0; index < TK_NAME_CAPACITY; ++index) {
        if (left[index] != right[index]) {
            return 0;
        }
        if (left[index] == '\0') {
            return 1;
        }
    }
    return 0;
}

int tk_audit_frames(const tk_frame_allocator_t *frames)
{
    size_t index;
    size_t free_count = 0u;

    if (frames == NULL || frames->frame_count > TK_MAX_FRAMES) {
        return -1;
    }
    for (index = 0; index < frames->frame_count; ++index) {
        if (frames->used[index] > 1u) {
            return -1;
        }
        if (frames->used[index] == 0u) {
            ++free_count;
        }
    }
    for (; index < TK_MAX_FRAMES; ++index) {
        if (frames->used[index] != 0u) {
            return -1;
        }
    }
    return free_count == frames->free_count ? 0 : -1;
}

int tk_audit_scheduler(const tk_scheduler_t *scheduler)
{
    size_t left;
    size_t running_count = 0u;
    int running_slot = -1;

    if (scheduler == NULL || scheduler->cursor >= TK_MAX_PROCESSES ||
        scheduler->current_slot < -1 ||
        scheduler->current_slot >= (int)TK_MAX_PROCESSES || scheduler->next_pid == 0u) {
        return -1;
    }
    for (left = 0; left < TK_MAX_PROCESSES; ++left) {
        const tk_process_t *process = &scheduler->processes[left];
        size_t right;

        if (process->state < TK_UNUSED || process->state > TK_EXITED) {
            return -1;
        }
        if (process->state == TK_UNUSED) {
            if (process->pid != 0u) {
                return -1;
            }
            continue;
        }
        if (process->pid == 0u || process->pid >= scheduler->next_pid) {
            return -1;
        }
        if (process->state == TK_RUNNING) {
            ++running_count;
            running_slot = (int)left;
        }
        for (right = left + 1u; right < TK_MAX_PROCESSES; ++right) {
            if (scheduler->processes[right].state != TK_UNUSED &&
                scheduler->processes[right].pid == process->pid) {
                return -1;
            }
        }
    }
    if (running_count > 1u) {
        return -1;
    }
    if ((running_count == 0u && scheduler->current_slot != -1) ||
        (running_count == 1u && scheduler->current_slot != running_slot)) {
        return -1;
    }
    return 0;
}

int tk_audit_vm(const tk_address_space_t *space)
{
    size_t left;

    if (space == NULL || space->frames == NULL || tk_audit_frames(space->frames) != 0) {
        return -1;
    }
    for (left = 0; left < TK_MAX_MAPPINGS; ++left) {
        const tk_mapping_t *mapping = &space->mappings[left];
        size_t right;

        if (mapping->present > 1u) {
            return -1;
        }
        if (mapping->present == 0u) {
            continue;
        }
        if ((mapping->flags & TK_VM_READ) == 0u ||
            (mapping->flags & (uint8_t)~AUDIT_VM_FLAGS) != 0u ||
            mapping->frame >= space->frames->frame_count ||
            space->frames->used[mapping->frame] == 0u) {
            return -1;
        }
        for (right = left + 1u; right < TK_MAX_MAPPINGS; ++right) {
            if (space->mappings[right].present != 0u &&
                (space->mappings[right].virtual_page == mapping->virtual_page ||
                 space->mappings[right].frame == mapping->frame)) {
                return -1;
            }
        }
    }
    return 0;
}

int tk_audit_fs(const tk_fs_t *fs)
{
    size_t left;

    if (fs == NULL) {
        return -1;
    }
    for (left = 0; left < TK_MAX_FILES; ++left) {
        const tk_file_t *file = &fs->files[left];
        size_t right;

        if (file->used > 1u || file->size > TK_FILE_CAPACITY) {
            return -1;
        }
        if (file->used == 0u) {
            if (file->size != 0u || file->name[0] != '\0') {
                return -1;
            }
            continue;
        }
        if (!audit_name(file->name)) {
            return -1;
        }
        for (right = left + 1u; right < TK_MAX_FILES; ++right) {
            if (fs->files[right].used != 0u &&
                audit_names_equal(file->name, fs->files[right].name)) {
                return -1;
            }
        }
    }
    return 0;
}
