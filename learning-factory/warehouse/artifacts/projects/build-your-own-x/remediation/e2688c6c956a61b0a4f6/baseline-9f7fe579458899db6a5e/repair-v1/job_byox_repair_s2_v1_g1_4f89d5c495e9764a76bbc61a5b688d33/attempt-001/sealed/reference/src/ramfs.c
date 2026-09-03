#include "minios.h"

static void clear_bytes(void *object, size_t size)
{
    unsigned char *bytes = (unsigned char *)object;
    size_t i;

    for (i = 0u; i < size; ++i) {
        bytes[i] = 0u;
    }
}

static void clear_file(fs_file_t *file)
{
    clear_bytes(file, sizeof(*file));
}

static int name_valid(const char *name)
{
    size_t i;

    if (name == NULL || name[0] != '/' || name[1] == '\0') {
        return 0;
    }
    for (i = 1u; i <= MINIOS_FS_NAME_CHARS; ++i) {
        unsigned char character = (unsigned char)name[i];
        int alpha = (character >= (unsigned char)'a' &&
                     character <= (unsigned char)'z') ||
                    (character >= (unsigned char)'A' &&
                     character <= (unsigned char)'Z');
        int digit = character >= (unsigned char)'0' &&
                    character <= (unsigned char)'9';

        if (character == (unsigned char)'\0') {
            return 1;
        }
        if (!alpha && !digit && character != (unsigned char)'.' &&
            character != (unsigned char)'_' && character != (unsigned char)'-') {
            return 0;
        }
    }
    return name[MINIOS_FS_NAME_CHARS + 1u] == '\0';
}

static int names_equal(const char *left, const char *right)
{
    size_t i;

    for (i = 0; i < MINIOS_FS_NAME_STORAGE; ++i) {
        if (left[i] != right[i]) {
            return 0;
        }
        if (left[i] == '\0') {
            return 1;
        }
    }
    return 1;
}

static fs_file_t *find_file(ramfs_t *fs, const char *name)
{
    size_t i;

    for (i = 0; i < MINIOS_FS_MAX_FILES; ++i) {
        if (fs->files[i].used != 0u &&
            names_equal(fs->files[i].name, name)) {
            return &fs->files[i];
        }
    }
    return NULL;
}

static const fs_file_t *find_file_const(const ramfs_t *fs, const char *name)
{
    size_t i;

    for (i = 0; i < MINIOS_FS_MAX_FILES; ++i) {
        if (fs->files[i].used != 0u &&
            names_equal(fs->files[i].name, name)) {
            return &fs->files[i];
        }
    }
    return NULL;
}

void fs_init(ramfs_t *fs)
{
    if (fs == NULL) {
        return;
    }
    clear_bytes(fs, sizeof(*fs));
}

os_status_t fs_create(ramfs_t *fs, const char *name)
{
    fs_file_t *free_file = NULL;
    size_t i;

    if (fs == NULL || !name_valid(name)) {
        return OS_ERR_INVALID;
    }
    for (i = 0; i < MINIOS_FS_MAX_FILES; ++i) {
        if (fs->files[i].used != 0u) {
            if (names_equal(fs->files[i].name, name)) {
                return OS_ERR_EXISTS;
            }
        } else if (free_file == NULL) {
            free_file = &fs->files[i];
        }
    }
    if (free_file == NULL) {
        return OS_ERR_FULL;
    }

    clear_file(free_file);
    for (i = 0; i < MINIOS_FS_NAME_STORAGE; ++i) {
        free_file->name[i] = name[i];
        if (name[i] == '\0') {
            break;
        }
    }
    free_file->used = 1u;
    return OS_OK;
}

os_status_t fs_stat(const ramfs_t *fs, const char *name, size_t *out_size)
{
    const fs_file_t *file;

    if (out_size != NULL) {
        *out_size = 0u;
    }
    if (fs == NULL || out_size == NULL || !name_valid(name)) {
        return OS_ERR_INVALID;
    }
    file = find_file_const(fs, name);
    if (file == NULL) {
        return OS_ERR_NOT_FOUND;
    }
    *out_size = file->size;
    return OS_OK;
}

os_status_t fs_write(ramfs_t *fs, const char *name, size_t offset,
                     const uint8_t *data, size_t count, size_t *out_written)
{
    fs_file_t *file;
    size_t i;
    size_t end;

    if (out_written != NULL) {
        *out_written = 0u;
    }
    if (fs == NULL || out_written == NULL ||
        (data == NULL && count != 0u) || !name_valid(name)) {
        return OS_ERR_INVALID;
    }
    file = find_file(fs, name);
    if (file == NULL) {
        return OS_ERR_NOT_FOUND;
    }
    if (offset > MINIOS_FS_FILE_CAPACITY ||
        count > MINIOS_FS_FILE_CAPACITY - offset) {
        return OS_ERR_NO_SPACE;
    }
    if (count == 0u) {
        return OS_OK;
    }

    for (i = file->size; i < offset; ++i) {
        file->data[i] = 0u;
    }
    for (i = 0; i < count; ++i) {
        file->data[offset + i] = data[i];
    }
    end = offset + count;
    if (end > file->size) {
        file->size = end;
    }
    *out_written = count;
    return OS_OK;
}

os_status_t fs_read(const ramfs_t *fs, const char *name, size_t offset,
                    uint8_t *data, size_t count, size_t *out_read)
{
    const fs_file_t *file;
    size_t available;
    size_t amount;
    size_t i;

    if (out_read != NULL) {
        *out_read = 0u;
    }
    if (fs == NULL || out_read == NULL ||
        (data == NULL && count != 0u) || !name_valid(name)) {
        return OS_ERR_INVALID;
    }
    file = find_file_const(fs, name);
    if (file == NULL) {
        return OS_ERR_NOT_FOUND;
    }
    if (count == 0u || offset >= file->size) {
        return OS_OK;
    }
    available = file->size - offset;
    amount = count < available ? count : available;
    for (i = 0; i < amount; ++i) {
        data[i] = file->data[offset + i];
    }
    *out_read = amount;
    return OS_OK;
}

os_status_t fs_unlink(ramfs_t *fs, const char *name)
{
    fs_file_t *file;

    if (fs == NULL || !name_valid(name)) {
        return OS_ERR_INVALID;
    }
    file = find_file(fs, name);
    if (file == NULL) {
        return OS_ERR_NOT_FOUND;
    }
    clear_file(file);
    return OS_OK;
}
