#include "kernel/ramfs.h"
#include "kernel/scheduler.h"
#include "kernel/vm.h"

#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static unsigned checks;
static unsigned failures;

#define EXPECT(condition)                                                      \
    do {                                                                       \
        ++checks;                                                              \
        if (!(condition)) {                                                    \
            fprintf(stderr, "reference failure at line %d: %s\n", __LINE__,   \
                    #condition);                                               \
            ++failures;                                                        \
        }                                                                      \
    } while (false)

static void no_op(void *argument) {
    (void)argument;
}

static void scheduler_edges(void) {
    lf_scheduler_t scheduler;
    lf_scheduler_t snapshot;
    uint32_t first;
    uint32_t second;

    lf_scheduler_init(&scheduler);
    snapshot = scheduler;
    EXPECT(lf_scheduler_rotate(&scheduler) == 0u);
    EXPECT(memcmp(&scheduler, &snapshot, sizeof(scheduler)) == 0);
    EXPECT(lf_scheduler_block_current(&scheduler) == 0u);
    EXPECT(lf_scheduler_exit_current(&scheduler) == 0u);
    EXPECT(!lf_scheduler_unblock(&scheduler, 0u));
    EXPECT(!lf_scheduler_reap(&scheduler, 77u));

    first = lf_scheduler_spawn(&scheduler, no_op, (void *)0);
    EXPECT(first == 1u);
    EXPECT(lf_scheduler_rotate(&scheduler) == first);
    EXPECT(lf_scheduler_rotate(&scheduler) == first);
    EXPECT(lf_scheduler_block_current(&scheduler) == 0u);
    EXPECT(scheduler.current_slot == LF_NO_SLOT);
    EXPECT(lf_scheduler_task(&scheduler, first)->state == LF_TASK_BLOCKED);
    EXPECT(lf_scheduler_unblock(&scheduler, first));
    EXPECT(lf_scheduler_rotate(&scheduler) == first);
    EXPECT(lf_scheduler_exit_current(&scheduler) == 0u);
    EXPECT(lf_scheduler_reap(&scheduler, first));
    second = lf_scheduler_spawn(&scheduler, no_op, (void *)0);
    EXPECT(second == 2u);

    lf_scheduler_init(&scheduler);
    scheduler.next_pid = UINT32_MAX;
    EXPECT(lf_scheduler_spawn(&scheduler, no_op, (void *)0) == UINT32_MAX);
    EXPECT(scheduler.next_pid == 0u);
    EXPECT(lf_scheduler_spawn(&scheduler, no_op, (void *)0) == 0u);
    EXPECT(lf_scheduler_invariant(&scheduler));

    lf_scheduler_init(&scheduler);
    first = lf_scheduler_spawn(&scheduler, no_op, (void *)0);
    second = lf_scheduler_spawn(&scheduler, no_op, (void *)0);
    EXPECT(first != 0u && second != 0u);
    scheduler.tasks[1].pid = first;
    EXPECT(!lf_scheduler_invariant(&scheduler));
    snapshot = scheduler;
    EXPECT(lf_scheduler_rotate(&scheduler) == 0u);
    EXPECT(memcmp(&scheduler, &snapshot, sizeof(scheduler)) == 0);

    lf_scheduler_init(&scheduler);
    scheduler.tasks[0].argument = (void *)(uintptr_t)1u;
    EXPECT(!lf_scheduler_invariant(&scheduler));
    lf_scheduler_init(&scheduler);
    first = lf_scheduler_spawn(&scheduler, no_op, (void *)0);
    scheduler.next_pid = first;
    EXPECT(!lf_scheduler_invariant(&scheduler));
}

static void frame_edges(void) {
    lf_frame_pool_t pool;
    uint32_t frames[LF_MAX_FRAMES];
    uint32_t index;

    EXPECT(!lf_frame_pool_init((lf_frame_pool_t *)0, 0u, 1u));
    EXPECT(!lf_frame_pool_init(&pool, UINT32_C(0xfffff000), 2u));
    EXPECT(lf_frame_pool_init(&pool, UINT32_C(0xfffff000), 1u));
    EXPECT(lf_frame_alloc(&pool) == UINT32_C(0xfffff000));
    EXPECT(lf_frame_alloc(&pool) == LF_INVALID_PADDR);
    pool.references[0] = UINT16_MAX;
    EXPECT(!lf_frame_retain(&pool, UINT32_C(0xfffff000)));
    pool.references[0] = 1u;
    EXPECT(!lf_frame_release(&pool, UINT32_C(0xfffff001)));
    EXPECT(lf_frame_release(&pool, UINT32_C(0xfffff000)));

    EXPECT(lf_frame_pool_init(&pool, UINT32_C(0x00800000), LF_MAX_FRAMES));
    for (index = 0u; index < LF_MAX_FRAMES; ++index) {
        frames[index] = lf_frame_alloc(&pool);
        EXPECT(frames[index] == UINT32_C(0x00800000) + index * LF_PAGE_SIZE);
    }
    EXPECT(lf_frame_alloc(&pool) == LF_INVALID_PADDR);
    EXPECT(lf_frame_release(&pool, frames[7]));
    EXPECT(lf_frame_alloc(&pool) == frames[7]);
}

static void mapping_edges(void) {
    lf_vm_space_t space;
    lf_vm_space_t snapshot;
    uint32_t translated = 0u;
    uint32_t slot;

    lf_vm_space_init(&space);
    EXPECT(!lf_vm_map((lf_vm_space_t *)0, 0u, 0u, LF_VM_READ));
    EXPECT(!lf_vm_map(&space, 0u, 0u, UINT8_C(0x80)));
    for (slot = 0u; slot < LF_MAX_MAPPINGS; ++slot) {
        EXPECT(lf_vm_map(&space, slot * LF_PAGE_SIZE,
                         UINT32_C(0x01000000) + slot * LF_PAGE_SIZE,
                         LF_VM_READ));
    }
    snapshot = space;
    EXPECT(!lf_vm_map(&space, UINT32_C(0x20000000), UINT32_C(0x02000000),
                      LF_VM_READ));
    EXPECT(memcmp(&space, &snapshot, sizeof(space)) == 0);
    EXPECT(!lf_vm_translate(&space, 0u, 0u, &translated));
    EXPECT(!lf_vm_translate(&space, 0u, LF_VM_READ, (uint32_t *)0));
    EXPECT(!lf_vm_translate(&space, 0u, LF_VM_WRITE, &translated));
    EXPECT(lf_vm_translate(&space, LF_PAGE_SIZE + 17u, LF_VM_READ,
                           &translated));
    EXPECT(translated == UINT32_C(0x01001011));

    lf_vm_space_init(&space);
    EXPECT(lf_vm_map(&space, UINT32_C(0x70000000), UINT32_C(0xfffff000),
                     LF_VM_READ));
    EXPECT(lf_vm_translate(&space, UINT32_C(0x70000fff), LF_VM_READ,
                           &translated));
    EXPECT(translated == UINT32_MAX);
}

static void ramfs_edges(void) {
    static const char *const names[LF_RAMFS_MAX_FILES] = {
        "a", "b", "c", "d", "e", "f", "g", "h"
    };
    lf_ramfs_t filesystem;
    lf_ramfs_t snapshot;
    uint8_t source[LF_RAMFS_FILE_MAX];
    uint8_t output[LF_RAMFS_FILE_MAX];
    uint32_t index;
    uint32_t size;

    for (index = 0u; index < LF_RAMFS_FILE_MAX; ++index) {
        source[index] = (uint8_t)(index ^ UINT32_C(0x5a));
        output[index] = 0u;
    }
    lf_ramfs_init(&filesystem);
    EXPECT(lf_ramfs_create((lf_ramfs_t *)0, "a") == LF_ERR_INVALID);
    EXPECT(lf_ramfs_create(&filesystem, (const char *)0) == LF_ERR_INVALID);
    snapshot = filesystem;
    EXPECT(lf_ramfs_read(&filesystem, "1234567890123456", 0u, output, 1u) ==
           LF_ERR_RANGE);
    EXPECT(lf_ramfs_write(&filesystem, "1234567890123456", 0u, source, 1u) ==
           LF_ERR_RANGE);
    EXPECT(lf_ramfs_size(&filesystem, "1234567890123456", &size) ==
           LF_ERR_RANGE);
    EXPECT(lf_ramfs_unlink(&filesystem, "1234567890123456") == LF_ERR_RANGE);
    EXPECT(memcmp(&filesystem, &snapshot, sizeof(filesystem)) == 0);
    for (index = 0u; index < LF_RAMFS_MAX_FILES; ++index) {
        EXPECT(lf_ramfs_create(&filesystem, names[index]) == LF_OK);
    }
    snapshot = filesystem;
    EXPECT(lf_ramfs_create(&filesystem, "overflow") == LF_ERR_NO_SPACE);
    EXPECT(memcmp(&filesystem, &snapshot, sizeof(filesystem)) == 0);

    EXPECT(lf_ramfs_write(&filesystem, "a", 0u, source,
                          LF_RAMFS_FILE_MAX) == (int32_t)LF_RAMFS_FILE_MAX);
    EXPECT(lf_ramfs_size(&filesystem, "a", &size) == LF_OK);
    EXPECT(size == LF_RAMFS_FILE_MAX);
    EXPECT(lf_ramfs_read(&filesystem, "a", 0u, output,
                         LF_RAMFS_FILE_MAX) == (int32_t)LF_RAMFS_FILE_MAX);
    EXPECT(memcmp(source, output, sizeof(source)) == 0);

    snapshot = filesystem;
    EXPECT(lf_ramfs_write(&filesystem, "a", 0u, (const void *)0, 1u) ==
           LF_ERR_INVALID);
    EXPECT(lf_ramfs_write(&filesystem, "a", UINT32_MAX, source, 2u) ==
           LF_ERR_RANGE);
    EXPECT(lf_ramfs_write(&filesystem, "a", LF_RAMFS_FILE_MAX, source, 0u) == 0);
    EXPECT(memcmp(&filesystem, &snapshot, sizeof(filesystem)) == 0);
    EXPECT(lf_ramfs_read(&filesystem, "a", UINT32_MAX, output, 2u) ==
           LF_ERR_RANGE);

    EXPECT(lf_ramfs_unlink(&filesystem, "a") == LF_OK);
    for (index = 0u; index < LF_RAMFS_FILE_MAX; ++index) {
        EXPECT(filesystem.files[0].data[index] == 0u);
    }
    for (index = 0u; index <= LF_RAMFS_NAME_MAX; ++index) {
        EXPECT(filesystem.files[0].name[index] == '\0');
    }
    EXPECT(lf_ramfs_create(&filesystem, "replacement") == LF_OK);
}

int main(void) {
    scheduler_edges();
    frame_edges();
    mapping_edges();
    ramfs_edges();

    if (failures != 0u) {
        fprintf(stderr, "reference_tests: %u/%u failed\n", failures, checks);
        return 1;
    }
    printf("reference_tests: PASS (%u checks)\n", checks);
    return 0;
}
