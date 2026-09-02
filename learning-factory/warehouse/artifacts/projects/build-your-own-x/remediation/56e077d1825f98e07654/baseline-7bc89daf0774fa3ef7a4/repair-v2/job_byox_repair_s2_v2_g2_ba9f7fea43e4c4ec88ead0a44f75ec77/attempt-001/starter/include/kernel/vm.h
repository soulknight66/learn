#ifndef LF_KERNEL_VM_H
#define LF_KERNEL_VM_H

#include <stdbool.h>
#include <stdint.h>

#define LF_PAGE_SIZE 4096u
#define LF_MAX_FRAMES 32u
#define LF_MAX_MAPPINGS 16u
#define LF_INVALID_PADDR UINT32_MAX

#define LF_VM_READ (1u << 0)
#define LF_VM_WRITE (1u << 1)
#define LF_VM_EXEC (1u << 2)
#define LF_VM_ALL (LF_VM_READ | LF_VM_WRITE | LF_VM_EXEC)

typedef struct {
    uint32_t base;
    uint32_t count;
    uint16_t references[LF_MAX_FRAMES];
    bool initialized;
} lf_frame_pool_t;

typedef struct {
    uint32_t virtual_base;
    uint32_t physical_base;
    uint8_t flags;
    bool used;
} lf_vm_mapping_t;

typedef struct {
    lf_vm_mapping_t mappings[LF_MAX_MAPPINGS];
} lf_vm_space_t;

bool lf_frame_pool_init(lf_frame_pool_t *pool, uint32_t base,
                        uint32_t count);
uint32_t lf_frame_alloc(lf_frame_pool_t *pool);
bool lf_frame_retain(lf_frame_pool_t *pool, uint32_t physical_address);
bool lf_frame_release(lf_frame_pool_t *pool, uint32_t physical_address);
uint16_t lf_frame_refcount(const lf_frame_pool_t *pool,
                           uint32_t physical_address);

void lf_vm_space_init(lf_vm_space_t *space);
bool lf_vm_map(lf_vm_space_t *space, uint32_t virtual_base,
               uint32_t physical_base, uint8_t flags);
bool lf_vm_unmap(lf_vm_space_t *space, uint32_t virtual_base);
bool lf_vm_translate(const lf_vm_space_t *space, uint32_t virtual_address,
                     uint8_t requested_access, uint32_t *physical_address);

#endif
