#include "tinykernel.h"

static int valid_name(const char *name, size_t *length_out)
{
    size_t length;

    if (name == NULL) {
        return 0;
    }
    for (length = 0; length < TK_NAME_CAPACITY; ++length) {
        if (name[length] == '\0') {
            if (length == 0u) {
                return 0;
            }
            if (length_out != NULL) {
                *length_out = length;
            }
            return 1;
        }
    }
    return 0;
}

static int names_equal(const char *left, const char *right)
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

static int find_file(const tk_fs_t *fs, const char *name)
{
    size_t index;

    if (fs == NULL || !valid_name(name, NULL)) {
        return -1;
    }
    for (index = 0; index < TK_MAX_FILES; ++index) {
        if (fs->files[index].used != 0u && names_equal(fs->files[index].name, name)) {
            return (int)index;
        }
    }
    return -1;
}

void tk_fs_init(tk_fs_t *fs)
{
    size_t file_index;

    if (fs == NULL) {
        return;
    }
    for (file_index = 0; file_index < TK_MAX_FILES; ++file_index) {
        size_t byte_index;
        for (byte_index = 0; byte_index < TK_NAME_CAPACITY; ++byte_index) {
            fs->files[file_index].name[byte_index] = '\0';
        }
        for (byte_index = 0; byte_index < TK_FILE_CAPACITY; ++byte_index) {
            fs->files[file_index].data[byte_index] = 0u;
        }
        fs->files[file_index].size = 0u;
        fs->files[file_index].used = 0u;
    }
}

int tk_fs_create(tk_fs_t *fs, const char *name)
{
    size_t name_length;
    size_t free_index = TK_MAX_FILES;
    size_t index;

    if (fs == NULL || !valid_name(name, &name_length)) {
        return -1;
    }
    for (index = 0; index < TK_MAX_FILES; ++index) {
        if (fs->files[index].used != 0u) {
            if (names_equal(fs->files[index].name, name)) {
                return -1;
            }
        } else if (free_index == TK_MAX_FILES) {
            free_index = index;
        }
    }
    if (free_index == TK_MAX_FILES) {
        return -1;
    }
    for (index = 0; index <= name_length; ++index) {
        fs->files[free_index].name[index] = name[index];
    }
    fs->files[free_index].size = 0u;
    fs->files[free_index].used = 1u;
    return 0;
}

int tk_fs_write(tk_fs_t *fs, const char *name, const uint8_t *data, size_t length)
{
    int file_index = find_file(fs, name);
    size_t index;

    if (file_index < 0 || length > TK_FILE_CAPACITY ||
        (length != 0u && data == NULL)) {
        return -1;
    }
    for (index = 0; index < length; ++index) {
        fs->files[file_index].data[index] = data[index];
    }
    for (index = length; index < TK_FILE_CAPACITY; ++index) {
        fs->files[file_index].data[index] = 0u;
    }
    fs->files[file_index].size = (uint16_t)length;
    return 0;
}

int tk_fs_read(const tk_fs_t *fs, const char *name, uint8_t *out, size_t capacity)
{
    int file_index = find_file(fs, name);
    size_t index;
    size_t length;

    if (file_index < 0) {
        return -1;
    }
    length = fs->files[file_index].size;
    if (capacity < length || (length != 0u && out == NULL)) {
        return -1;
    }
    for (index = 0; index < length; ++index) {
        out[index] = fs->files[file_index].data[index];
    }
    return (int)length;
}

int tk_fs_size(const tk_fs_t *fs, const char *name)
{
    int file_index = find_file(fs, name);

    if (file_index < 0) {
        return -1;
    }
    return (int)fs->files[file_index].size;
}

int tk_fs_unlink(tk_fs_t *fs, const char *name)
{
    int file_index = find_file(fs, name);
    size_t index;

    if (file_index < 0) {
        return -1;
    }
    for (index = 0; index < TK_NAME_CAPACITY; ++index) {
        fs->files[file_index].name[index] = '\0';
    }
    for (index = 0; index < TK_FILE_CAPACITY; ++index) {
        fs->files[file_index].data[index] = 0u;
    }
    fs->files[file_index].size = 0u;
    fs->files[file_index].used = 0u;
    return 0;
}

size_t tk_fs_file_count(const tk_fs_t *fs)
{
    size_t index;
    size_t count = 0u;

    if (fs == NULL) {
        return 0u;
    }
    for (index = 0; index < TK_MAX_FILES; ++index) {
        if (fs->files[index].used != 0u) {
            ++count;
        }
    }
    return count;
}
