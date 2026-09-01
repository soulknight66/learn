#include "tinykernel.h"

void tk_fs_init(tk_fs_t *fs)
{
    if (fs != NULL) {
        size_t file_index;
        for (file_index = 0; file_index < TK_MAX_FILES; ++file_index) {
            size_t byte_index;
            fs->files[file_index].name[0] = '\0';
            for (byte_index = 0; byte_index < TK_FILE_CAPACITY; ++byte_index) {
                fs->files[file_index].data[byte_index] = 0u;
            }
            fs->files[file_index].size = 0u;
            fs->files[file_index].used = 0u;
        }
    }
}

int tk_fs_create(tk_fs_t *fs, const char *name)
{
    (void)fs;
    (void)name;
    /* TODO(stage 4): validate and copy the name into a free slot. */
    return -1;
}

int tk_fs_write(tk_fs_t *fs, const char *name, const uint8_t *data, size_t length)
{
    (void)fs;
    (void)name;
    (void)data;
    (void)length;
    return -1;
}

int tk_fs_read(const tk_fs_t *fs, const char *name, uint8_t *out, size_t capacity)
{
    (void)fs;
    (void)name;
    (void)out;
    (void)capacity;
    return -1;
}

int tk_fs_size(const tk_fs_t *fs, const char *name)
{
    (void)fs;
    (void)name;
    return -1;
}

int tk_fs_unlink(tk_fs_t *fs, const char *name)
{
    (void)fs;
    (void)name;
    return -1;
}

size_t tk_fs_file_count(const tk_fs_t *fs)
{
    (void)fs;
    return 0u;
}
