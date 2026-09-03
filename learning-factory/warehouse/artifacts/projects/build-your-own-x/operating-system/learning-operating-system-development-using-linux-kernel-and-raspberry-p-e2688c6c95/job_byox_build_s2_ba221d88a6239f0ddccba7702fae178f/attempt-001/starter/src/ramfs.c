#include "minios.h"

void fs_init(ramfs_t *fs)
{
    size_t i;
    size_t j;

    if (fs == NULL) {
        return;
    }
    for (i = 0; i < MINIOS_FS_MAX_FILES; ++i) {
        fs->files[i].used = 0;
        fs->files[i].size = 0;
        for (j = 0; j < MINIOS_FS_NAME_STORAGE; ++j) {
            fs->files[i].name[j] = '\0';
        }
        for (j = 0; j < MINIOS_FS_FILE_CAPACITY; ++j) {
            fs->files[i].data[j] = 0;
        }
    }
}

os_status_t fs_create(ramfs_t *fs, const char *name)
{
    /* TODO: validate the flat path, reject duplicates, and use the first slot. */
    (void)fs;
    (void)name;
    return OS_ERR_FULL;
}

os_status_t fs_stat(const ramfs_t *fs, const char *name, size_t *out_size)
{
    /* TODO: find a valid name and return its logical byte length. */
    (void)fs;
    (void)name;
    if (out_size != NULL) {
        *out_size = 0;
    }
    return OS_ERR_NOT_FOUND;
}

os_status_t fs_write(ramfs_t *fs, const char *name, size_t offset,
                     const uint8_t *data, size_t count, size_t *out_written)
{
    /* TODO: preflight the complete request, zero any gap, then copy bytes. */
    (void)fs;
    (void)name;
    (void)offset;
    (void)data;
    (void)count;
    if (out_written != NULL) {
        *out_written = 0;
    }
    return OS_ERR_NOT_FOUND;
}

os_status_t fs_read(const ramfs_t *fs, const char *name, size_t offset,
                    uint8_t *data, size_t count, size_t *out_read)
{
    /* TODO: copy at most the bytes that remain before end of file. */
    (void)fs;
    (void)name;
    (void)offset;
    (void)data;
    (void)count;
    if (out_read != NULL) {
        *out_read = 0;
    }
    return OS_ERR_NOT_FOUND;
}

os_status_t fs_unlink(ramfs_t *fs, const char *name)
{
    /* TODO: clear the complete occupied slot for this name. */
    (void)fs;
    (void)name;
    return OS_ERR_NOT_FOUND;
}
