#include "kernel/ramfs.h"

#include <stddef.h>

/* Stage 4: replace these safe failure stubs with a bounded, failure-atomic
 * implementation. */
void lf_ramfs_init(lf_ramfs_t *filesystem) {
    uint8_t *byte;
    size_t index;

    if (filesystem == (lf_ramfs_t *)0) {
        return;
    }
    byte = (uint8_t *)filesystem;
    for (index = 0u; index < sizeof(*filesystem); ++index) {
        byte[index] = 0u;
    }
}

int32_t lf_ramfs_create(lf_ramfs_t *filesystem, const char *name) {
    (void)filesystem;
    (void)name;
    return LF_ERR_INVALID;
}

int32_t lf_ramfs_write(lf_ramfs_t *filesystem, const char *name,
                       uint32_t offset, const void *source, uint32_t length) {
    (void)filesystem;
    (void)name;
    (void)offset;
    (void)source;
    (void)length;
    return LF_ERR_INVALID;
}

int32_t lf_ramfs_read(const lf_ramfs_t *filesystem, const char *name,
                      uint32_t offset, void *destination, uint32_t length) {
    (void)filesystem;
    (void)name;
    (void)offset;
    (void)destination;
    (void)length;
    return LF_ERR_INVALID;
}

int32_t lf_ramfs_size(const lf_ramfs_t *filesystem, const char *name,
                      uint32_t *size) {
    (void)filesystem;
    (void)name;
    (void)size;
    return LF_ERR_INVALID;
}

int32_t lf_ramfs_unlink(lf_ramfs_t *filesystem, const char *name) {
    (void)filesystem;
    (void)name;
    return LF_ERR_INVALID;
}
