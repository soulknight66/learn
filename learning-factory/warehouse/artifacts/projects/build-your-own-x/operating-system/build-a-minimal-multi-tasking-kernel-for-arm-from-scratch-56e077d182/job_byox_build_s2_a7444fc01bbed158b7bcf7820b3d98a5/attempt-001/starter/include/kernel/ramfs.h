#ifndef LF_KERNEL_RAMFS_H
#define LF_KERNEL_RAMFS_H

#include <stdint.h>

#define LF_RAMFS_MAX_FILES 8u
#define LF_RAMFS_NAME_MAX 15u
#define LF_RAMFS_FILE_MAX 256u

enum {
    LF_OK = 0,
    LF_ERR_INVALID = -1,
    LF_ERR_NOT_FOUND = -2,
    LF_ERR_EXISTS = -3,
    LF_ERR_NO_SPACE = -4,
    LF_ERR_RANGE = -5
};

typedef struct {
    char name[LF_RAMFS_NAME_MAX + 1u];
    uint8_t data[LF_RAMFS_FILE_MAX];
    uint32_t size;
    uint8_t used;
} lf_ramfs_file_t;

typedef struct {
    lf_ramfs_file_t files[LF_RAMFS_MAX_FILES];
} lf_ramfs_t;

void lf_ramfs_init(lf_ramfs_t *filesystem);
int32_t lf_ramfs_create(lf_ramfs_t *filesystem, const char *name);
int32_t lf_ramfs_write(lf_ramfs_t *filesystem, const char *name,
                       uint32_t offset, const void *source, uint32_t length);
int32_t lf_ramfs_read(const lf_ramfs_t *filesystem, const char *name,
                      uint32_t offset, void *destination, uint32_t length);
int32_t lf_ramfs_size(const lf_ramfs_t *filesystem, const char *name,
                      uint32_t *size);
int32_t lf_ramfs_unlink(lf_ramfs_t *filesystem, const char *name);

#endif
