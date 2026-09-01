#include "micaos.h"

static mica_status_t validate_name(const char *name)
{
    size_t index;

    if (name == NULL) {
        return MICA_ERR_ARG;
    }
    for (index = 0u; index <= MICA_NAME_MAX; ++index) {
        if (name[index] == '\0') {
            if (index == 0u ||
                (index == 1u && name[0] == '.') ||
                (index == 2u && name[0] == '.' && name[1] == '.')) {
                return MICA_ERR_ARG;
            }
            return MICA_OK;
        }
        if (name[index] == '/') {
            return MICA_ERR_ARG;
        }
    }
    return MICA_ERR_ARG;
}

static bool names_equal(const char *left, const char *right)
{
    size_t index;

    for (index = 0u; index <= MICA_NAME_MAX; ++index) {
        if (left[index] != right[index]) {
            return false;
        }
        if (left[index] == '\0') {
            return true;
        }
    }
    return false;
}

static bool find_file(const mica_ramfs_t *fs,
                      const char *name,
                      size_t *out_index)
{
    size_t index;

    for (index = 0u; index < MICA_MAX_FILES; ++index) {
        if (fs->files[index].used && names_equal(fs->files[index].name, name)) {
            *out_index = index;
            return true;
        }
    }
    return false;
}

void mica_ramfs_init(mica_ramfs_t *fs)
{
    size_t file;
    size_t index;

    if (fs == NULL) {
        return;
    }
    for (file = 0u; file < MICA_MAX_FILES; ++file) {
        fs->files[file].used = false;
        fs->files[file].size = 0u;
        for (index = 0u; index <= MICA_NAME_MAX; ++index) {
            fs->files[file].name[index] = '\0';
        }
        for (index = 0u; index < MICA_FILE_CAPACITY; ++index) {
            fs->files[file].data[index] = 0u;
        }
    }
}

mica_status_t mica_ramfs_create(mica_ramfs_t *fs, const char *name)
{
    size_t index;

    if (fs == NULL) {
        return MICA_ERR_ARG;
    }
    if (validate_name(name) != MICA_OK) {
        return MICA_ERR_ARG;
    }
    if (find_file(fs, name, &index)) {
        return MICA_ERR_EXISTS;
    }
    for (index = 0u; index < MICA_MAX_FILES; ++index) {
        if (!fs->files[index].used) {
            /* TODO: initialize a new empty file in this slot. */
            return MICA_ERR_STATE;
        }
    }
    return MICA_ERR_FULL;
}

mica_status_t mica_ramfs_write(mica_ramfs_t *fs,
                               const char *name,
                               size_t offset,
                               const uint8_t *data,
                               size_t length)
{
    size_t index;

    if (fs == NULL || (data == NULL && length != 0u)) {
        return MICA_ERR_ARG;
    }
    if (validate_name(name) != MICA_OK) {
        return MICA_ERR_ARG;
    }
    if (offset > MICA_FILE_CAPACITY ||
        length > MICA_FILE_CAPACITY - offset) {
        return MICA_ERR_RANGE;
    }
    if (!find_file(fs, name, &index)) {
        return MICA_ERR_NOT_FOUND;
    }
    /* TODO: apply the entire bounded write, including any sparse gap. */
    return MICA_ERR_STATE;
}

mica_status_t mica_ramfs_read(const mica_ramfs_t *fs,
                              const char *name,
                              size_t offset,
                              uint8_t *out,
                              size_t capacity,
                              size_t *out_read)
{
    size_t index;

    if (fs == NULL || out_read == NULL || (out == NULL && capacity != 0u)) {
        return MICA_ERR_ARG;
    }
    if (validate_name(name) != MICA_OK) {
        return MICA_ERR_ARG;
    }
    if (!find_file(fs, name, &index)) {
        return MICA_ERR_NOT_FOUND;
    }
    if (offset > fs->files[index].size) {
        return MICA_ERR_RANGE;
    }
    if (capacity == 0u || offset == fs->files[index].size) {
        *out_read = 0u;
        return MICA_OK;
    }
    /* TODO: copy the available prefix into the caller's buffer. */
    return MICA_ERR_STATE;
}

mica_status_t mica_ramfs_unlink(mica_ramfs_t *fs, const char *name)
{
    size_t index;

    if (fs == NULL) {
        return MICA_ERR_ARG;
    }
    if (validate_name(name) != MICA_OK) {
        return MICA_ERR_ARG;
    }
    if (!find_file(fs, name, &index)) {
        return MICA_ERR_NOT_FOUND;
    }
    /* TODO: release this file slot. */
    return MICA_ERR_STATE;
}

mica_status_t mica_ramfs_stat(const mica_ramfs_t *fs,
                              const char *name,
                              mica_ramfs_stat_t *out_stat)
{
    size_t index;

    if (fs == NULL || out_stat == NULL) {
        return MICA_ERR_ARG;
    }
    if (validate_name(name) != MICA_OK) {
        return MICA_ERR_ARG;
    }
    if (!find_file(fs, name, &index)) {
        return MICA_ERR_NOT_FOUND;
    }
    /* TODO: report metadata for this file. */
    return MICA_ERR_STATE;
}
