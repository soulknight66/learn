#include "kernel/ramfs.h"

#include <stdbool.h>
#include <stddef.h>

static void clear_file(lf_ramfs_file_t *file) {
    uint8_t *byte = (uint8_t *)file;
    size_t index;

    for (index = 0u; index < sizeof(*file); ++index) {
        byte[index] = 0u;
    }
}

static int32_t valid_name_length(const char *name) {
    uint32_t length;

    if (name == (const char *)0) {
        return LF_ERR_INVALID;
    }
    for (length = 0u; length <= LF_RAMFS_NAME_MAX; ++length) {
        if (name[length] == '\0') {
            return length == 0u ? LF_ERR_INVALID : (int32_t)length;
        }
    }
    return LF_ERR_RANGE;
}

static bool names_equal(const char *left, const char *right) {
    uint32_t index = 0u;

    while (left[index] == right[index]) {
        if (left[index] == '\0') {
            return true;
        }
        ++index;
    }
    return false;
}

static int32_t find_file(const lf_ramfs_t *filesystem, const char *name) {
    uint32_t slot;
    int32_t name_length;

    if (filesystem == (const lf_ramfs_t *)0) {
        return LF_ERR_INVALID;
    }
    name_length = valid_name_length(name);
    if (name_length < 0) {
        return name_length;
    }
    for (slot = 0u; slot < LF_RAMFS_MAX_FILES; ++slot) {
        if (filesystem->files[slot].used != 0u &&
            names_equal(filesystem->files[slot].name, name)) {
            return (int32_t)slot;
        }
    }
    return LF_ERR_NOT_FOUND;
}

void lf_ramfs_init(lf_ramfs_t *filesystem) {
    uint32_t slot;

    if (filesystem == (lf_ramfs_t *)0) {
        return;
    }
    for (slot = 0u; slot < LF_RAMFS_MAX_FILES; ++slot) {
        clear_file(&filesystem->files[slot]);
    }
}

int32_t lf_ramfs_create(lf_ramfs_t *filesystem, const char *name) {
    uint32_t slot;
    uint32_t free_slot = LF_RAMFS_MAX_FILES;
    int32_t name_length;

    if (filesystem == (lf_ramfs_t *)0) {
        return LF_ERR_INVALID;
    }
    name_length = valid_name_length(name);
    if (name_length < 0) {
        return name_length;
    }
    for (slot = 0u; slot < LF_RAMFS_MAX_FILES; ++slot) {
        if (filesystem->files[slot].used != 0u) {
            if (names_equal(filesystem->files[slot].name, name)) {
                return LF_ERR_EXISTS;
            }
        } else if (free_slot == LF_RAMFS_MAX_FILES) {
            free_slot = slot;
        }
    }
    if (free_slot == LF_RAMFS_MAX_FILES) {
        return LF_ERR_NO_SPACE;
    }

    clear_file(&filesystem->files[free_slot]);
    for (slot = 0u; slot < (uint32_t)name_length; ++slot) {
        filesystem->files[free_slot].name[slot] = name[slot];
    }
    filesystem->files[free_slot].name[(uint32_t)name_length] = '\0';
    filesystem->files[free_slot].used = 1u;
    return LF_OK;
}

int32_t lf_ramfs_write(lf_ramfs_t *filesystem, const char *name,
                       uint32_t offset, const void *source, uint32_t length) {
    int32_t found;
    uint32_t end;
    uint32_t index;
    const uint8_t *bytes = (const uint8_t *)source;
    lf_ramfs_file_t *file;

    if (filesystem == (lf_ramfs_t *)0 || (source == (const void *)0 && length != 0u)) {
        return LF_ERR_INVALID;
    }
    found = find_file(filesystem, name);
    if (found < 0) {
        return found;
    }
    if (offset > UINT32_MAX - length) {
        return LF_ERR_RANGE;
    }
    end = offset + length;
    if (end > LF_RAMFS_FILE_MAX) {
        return LF_ERR_NO_SPACE;
    }
    if (length == 0u) {
        return 0;
    }

    file = &filesystem->files[(uint32_t)found];
    for (index = file->size; index < offset; ++index) {
        file->data[index] = 0u;
    }
    for (index = 0u; index < length; ++index) {
        file->data[offset + index] = bytes[index];
    }
    if (end > file->size) {
        file->size = end;
    }
    return (int32_t)length;
}

int32_t lf_ramfs_read(const lf_ramfs_t *filesystem, const char *name,
                      uint32_t offset, void *destination, uint32_t length) {
    int32_t found;
    uint32_t available;
    uint32_t copied;
    uint8_t *bytes = (uint8_t *)destination;
    const lf_ramfs_file_t *file;

    if (filesystem == (const lf_ramfs_t *)0 ||
        (destination == (void *)0 && length != 0u)) {
        return LF_ERR_INVALID;
    }
    found = find_file(filesystem, name);
    if (found < 0) {
        return found;
    }
    if (offset > UINT32_MAX - length) {
        return LF_ERR_RANGE;
    }
    file = &filesystem->files[(uint32_t)found];
    if (length == 0u || offset >= file->size) {
        return 0;
    }
    available = file->size - offset;
    copied = length < available ? length : available;
    for (available = 0u; available < copied; ++available) {
        bytes[available] = file->data[offset + available];
    }
    return (int32_t)copied;
}

int32_t lf_ramfs_size(const lf_ramfs_t *filesystem, const char *name,
                      uint32_t *size) {
    int32_t found;

    if (filesystem == (const lf_ramfs_t *)0 || size == (uint32_t *)0) {
        return LF_ERR_INVALID;
    }
    found = find_file(filesystem, name);
    if (found < 0) {
        return found;
    }
    *size = filesystem->files[(uint32_t)found].size;
    return LF_OK;
}

int32_t lf_ramfs_unlink(lf_ramfs_t *filesystem, const char *name) {
    int32_t found;

    if (filesystem == (lf_ramfs_t *)0) {
        return LF_ERR_INVALID;
    }
    found = find_file(filesystem, name);
    if (found < 0) {
        return found;
    }
    clear_file(&filesystem->files[(uint32_t)found]);
    return LF_OK;
}
