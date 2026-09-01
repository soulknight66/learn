#include "micaos.h"

static bool valid_name(const char *name)
{
    size_t length;

    if (name == NULL) {
        return false;
    }
    for (length = 0u; length <= MICA_NAME_MAX; length++) {
        if (name[length] == '\0') {
            break;
        }
        if (name[length] == '/') {
            return false;
        }
    }
    if (length == 0u || length > MICA_NAME_MAX) {
        return false;
    }
    if (length == 1u && name[0] == '.') {
        return false;
    }
    if (length == 2u && name[0] == '.' && name[1] == '.') {
        return false;
    }
    return true;
}

static bool names_equal(const char *left, const char *right)
{
    size_t i;

    for (i = 0u; i <= MICA_NAME_MAX; i++) {
        if (left[i] != right[i]) {
            return false;
        }
        if (left[i] == '\0') {
            return true;
        }
    }
    return false;
}

static bool find_file(const mica_ramfs_t *fs,
                      const char *name,
                      size_t *out_index)
{
    size_t i;

    for (i = 0u; i < MICA_MAX_FILES; i++) {
        if (fs->files[i].used && names_equal(fs->files[i].name, name)) {
            *out_index = i;
            return true;
        }
    }
    return false;
}

static void clear_file(mica_ramfs_file_t *file)
{
    size_t i;

    file->used = false;
    for (i = 0u; i <= MICA_NAME_MAX; i++) {
        file->name[i] = '\0';
    }
    for (i = 0u; i < MICA_FILE_CAPACITY; i++) {
        file->data[i] = 0u;
    }
    file->size = 0u;
}

void mica_ramfs_init(mica_ramfs_t *fs)
{
    size_t i;

    if (fs == NULL) {
        return;
    }
    for (i = 0u; i < MICA_MAX_FILES; i++) {
        clear_file(&fs->files[i]);
    }
}

mica_status_t mica_ramfs_create(mica_ramfs_t *fs, const char *name)
{
    size_t existing;
    size_t slot;
    size_t i;

    if (fs == NULL || !valid_name(name)) {
        return MICA_ERR_ARG;
    }
    if (find_file(fs, name, &existing)) {
        return MICA_ERR_EXISTS;
    }
    for (slot = 0u; slot < MICA_MAX_FILES; slot++) {
        if (!fs->files[slot].used) {
            break;
        }
    }
    if (slot == MICA_MAX_FILES) {
        return MICA_ERR_FULL;
    }

    clear_file(&fs->files[slot]);
    for (i = 0u; name[i] != '\0'; i++) {
        fs->files[slot].name[i] = name[i];
    }
    fs->files[slot].name[i] = '\0';
    fs->files[slot].used = true;
    return MICA_OK;
}

mica_status_t mica_ramfs_write(mica_ramfs_t *fs,
                               const char *name,
                               size_t offset,
                               const uint8_t *data,
                               size_t length)
{
    size_t index;
    size_t i;
    size_t end;
    uint8_t staged[MICA_FILE_CAPACITY];
    mica_ramfs_file_t *file;

    if (fs == NULL || !valid_name(name) || (length != 0u && data == NULL)) {
        return MICA_ERR_ARG;
    }
    if (offset > MICA_FILE_CAPACITY ||
        length > MICA_FILE_CAPACITY - offset) {
        return MICA_ERR_RANGE;
    }
    if (!find_file(fs, name, &index)) {
        return MICA_ERR_NOT_FOUND;
    }
    file = &fs->files[index];
    if (file->size > MICA_FILE_CAPACITY) {
        return MICA_ERR_STATE;
    }
    if (length == 0u) {
        return MICA_OK;
    }

    for (i = 0u; i < length; i++) {
        staged[i] = data[i];
    }
    if (offset > file->size) {
        for (i = file->size; i < offset; i++) {
            file->data[i] = 0u;
        }
    }
    for (i = 0u; i < length; i++) {
        file->data[offset + i] = staged[i];
    }
    end = offset + length;
    if (end > file->size) {
        file->size = end;
    }
    return MICA_OK;
}

mica_status_t mica_ramfs_read(const mica_ramfs_t *fs,
                              const char *name,
                              size_t offset,
                              uint8_t *out,
                              size_t capacity,
                              size_t *out_read)
{
    size_t index;
    size_t available;
    size_t amount;
    size_t i;
    const mica_ramfs_file_t *file;

    if (fs == NULL || !valid_name(name) || out_read == NULL ||
        (capacity != 0u && out == NULL)) {
        return MICA_ERR_ARG;
    }
    if (!find_file(fs, name, &index)) {
        return MICA_ERR_NOT_FOUND;
    }
    file = &fs->files[index];
    if (file->size > MICA_FILE_CAPACITY) {
        return MICA_ERR_STATE;
    }
    if (offset > file->size) {
        return MICA_ERR_RANGE;
    }
    available = file->size - offset;
    amount = capacity < available ? capacity : available;
    for (i = 0u; i < amount; i++) {
        out[i] = file->data[offset + i];
    }
    *out_read = amount;
    return MICA_OK;
}

mica_status_t mica_ramfs_unlink(mica_ramfs_t *fs, const char *name)
{
    size_t index;

    if (fs == NULL || !valid_name(name)) {
        return MICA_ERR_ARG;
    }
    if (!find_file(fs, name, &index)) {
        return MICA_ERR_NOT_FOUND;
    }
    clear_file(&fs->files[index]);
    return MICA_OK;
}

mica_status_t mica_ramfs_stat(const mica_ramfs_t *fs,
                              const char *name,
                              mica_ramfs_stat_t *out_stat)
{
    size_t index;
    size_t size;

    if (fs == NULL || !valid_name(name) || out_stat == NULL) {
        return MICA_ERR_ARG;
    }
    if (!find_file(fs, name, &index)) {
        return MICA_ERR_NOT_FOUND;
    }
    size = fs->files[index].size;
    if (size > MICA_FILE_CAPACITY) {
        return MICA_ERR_STATE;
    }
    out_stat->size = size;
    return MICA_OK;
}
