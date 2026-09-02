#include "kernel/ramfs.h"
#include "kernel/scheduler.h"
#include "kernel/vm.h"

#include <inttypes.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static unsigned failures;

#define CHECK(condition)                                                       \
    do {                                                                       \
        if (!(condition)) {                                                    \
            fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__,          \
                    #condition);                                               \
            ++failures;                                                        \
        }                                                                      \
    } while (false)

static void inert_task(void *argument) {
    (void)argument;
}

static bool bytes_are_zero(const void *object, size_t size) {
    const unsigned char *bytes = (const unsigned char *)object;
    size_t index;

    for (index = 0u; index < size; ++index) {
        if (bytes[index] != 0u) {
            return false;
        }
    }
    return true;
}

static void test_scheduler(void) {
    lf_scheduler_t scheduler;
    const lf_task_t *task;
    uint32_t pids[5];

    lf_scheduler_init(&scheduler);
    CHECK(lf_scheduler_invariant(&scheduler));
    CHECK(scheduler.current_slot == LF_NO_SLOT);

    pids[0] = lf_scheduler_spawn(&scheduler, inert_task, (void *)(uintptr_t)1u);
    pids[1] = lf_scheduler_spawn(&scheduler, inert_task, (void *)(uintptr_t)2u);
    pids[2] = lf_scheduler_spawn(&scheduler, inert_task, (void *)(uintptr_t)3u);
    pids[3] = lf_scheduler_spawn(&scheduler, inert_task, (void *)(uintptr_t)4u);
    pids[4] = lf_scheduler_spawn(&scheduler, inert_task, (void *)(uintptr_t)5u);
    CHECK(pids[0] == 1u && pids[1] == 2u && pids[2] == 3u && pids[3] == 4u);
    CHECK(pids[4] == 0u);
    CHECK(lf_scheduler_spawn(&scheduler, (lf_task_entry_t)0, (void *)0) == 0u);

    CHECK(lf_scheduler_rotate(&scheduler) == pids[0]);
    CHECK(lf_scheduler_rotate(&scheduler) == pids[1]);
    CHECK(lf_scheduler_block_current(&scheduler) == pids[2]);
    task = lf_scheduler_task(&scheduler, pids[1]);
    CHECK(task != (const lf_task_t *)0);
    if (task != (const lf_task_t *)0) {
        CHECK(task->state == LF_TASK_BLOCKED);
    }
    CHECK(lf_scheduler_unblock(&scheduler, pids[1]));
    CHECK(!lf_scheduler_unblock(&scheduler, pids[1]));
    CHECK(lf_scheduler_rotate(&scheduler) == pids[3]);
    CHECK(lf_scheduler_exit_current(&scheduler) == pids[0]);
    task = lf_scheduler_task(&scheduler, pids[3]);
    CHECK(task != (const lf_task_t *)0);
    if (task != (const lf_task_t *)0) {
        CHECK(task->state == LF_TASK_ZOMBIE);
    }
    CHECK(!lf_scheduler_reap(&scheduler, pids[0]));
    CHECK(lf_scheduler_reap(&scheduler, pids[3]));
    CHECK(lf_scheduler_spawn(&scheduler, inert_task, (void *)0) == 5u);
    CHECK(lf_scheduler_invariant(&scheduler));
}

static void test_frames_and_mappings(void) {
    lf_frame_pool_t pool;
    lf_vm_space_t space;
    unsigned char before[sizeof(space)];
    uint32_t first;
    uint32_t second;
    uint32_t translated = 0u;

    CHECK(!lf_frame_pool_init(&pool, UINT32_C(0x00100001), 4u));
    CHECK(!lf_frame_pool_init(&pool, UINT32_C(0x00100000), 0u));
    CHECK(lf_frame_pool_init(&pool, UINT32_C(0x00100000), 4u));
    first = lf_frame_alloc(&pool);
    second = lf_frame_alloc(&pool);
    CHECK(first == UINT32_C(0x00100000));
    CHECK(second == UINT32_C(0x00101000));
    CHECK(lf_frame_retain(&pool, first));
    CHECK(lf_frame_refcount(&pool, first) == 2u);
    CHECK(lf_frame_release(&pool, first));
    CHECK(lf_frame_release(&pool, first));
    CHECK(!lf_frame_release(&pool, first));
    CHECK(lf_frame_alloc(&pool) == first);
    CHECK(!lf_frame_retain(&pool, UINT32_C(0x00200000)));

    memset(&space, 0xa5, sizeof(space));
    lf_vm_space_init(&space);
    CHECK(bytes_are_zero(&space, sizeof(space)));
    CHECK(!lf_vm_map(&space, UINT32_C(0x40000001), first, LF_VM_READ));
    CHECK(!lf_vm_map(&space, UINT32_C(0x40000000), first, 0u));
    CHECK(lf_vm_map(&space, UINT32_C(0x40000000), first,
                    LF_VM_READ | LF_VM_WRITE));
    memcpy(before, &space, sizeof(before));
    CHECK(!lf_vm_map(&space, UINT32_C(0x40000000), second, LF_VM_READ));
    CHECK(memcmp(before, &space, sizeof(before)) == 0);
    CHECK(lf_vm_translate(&space, UINT32_C(0x40000321), LF_VM_READ,
                          &translated));
    CHECK(translated == first + UINT32_C(0x321));
    CHECK(!lf_vm_translate(&space, UINT32_C(0x40000321), LF_VM_EXEC,
                           &translated));
    CHECK(!lf_vm_translate(&space, UINT32_C(0x50000000), LF_VM_READ,
                           &translated));
    CHECK(lf_vm_unmap(&space, UINT32_C(0x40000000)));
    CHECK(!lf_vm_unmap(&space, UINT32_C(0x40000000)));
}

static void test_ramfs(void) {
    static const char *const extra_names[] = {
        "f1", "f2", "f3", "f4", "f5", "f6", "f7"
    };
    const uint8_t payload[] = {'h', 'i'};
    const uint8_t expected[] = {0u, 0u, 'h', 'i'};
    uint8_t output[8] = {0xffu, 0xffu, 0xffu, 0xffu,
                         0xffu, 0xffu, 0xffu, 0xffu};
    lf_ramfs_t filesystem;
    unsigned char before[sizeof(filesystem)];
    uint32_t size = UINT32_MAX;
    uint32_t index;

    memset(&filesystem, 0xa5, sizeof(filesystem));
    lf_ramfs_init(&filesystem);
    CHECK(bytes_are_zero(&filesystem, sizeof(filesystem)));
    CHECK(lf_ramfs_create(&filesystem, "motd") == LF_OK);
    CHECK(lf_ramfs_create(&filesystem, "motd") == LF_ERR_EXISTS);
    CHECK(lf_ramfs_create(&filesystem, "") == LF_ERR_INVALID);
    CHECK(lf_ramfs_create(&filesystem, "sixteen-byte-name") == LF_ERR_RANGE);
    CHECK(lf_ramfs_write(&filesystem, "motd", 2u, payload,
                         (uint32_t)sizeof(payload)) == 2);
    CHECK(lf_ramfs_size(&filesystem, "motd", &size) == LF_OK && size == 4u);
    CHECK(lf_ramfs_read(&filesystem, "motd", 0u, output,
                        (uint32_t)sizeof(output)) == 4);
    CHECK(memcmp(output, expected, sizeof(expected)) == 0);
    CHECK(lf_ramfs_read(&filesystem, "motd", 0u, (void *)0, 0u) == 0);

    memcpy(before, &filesystem, sizeof(before));
    CHECK(lf_ramfs_write(&filesystem, "motd", UINT32_MAX, payload, 2u) ==
          LF_ERR_RANGE);
    CHECK(memcmp(before, &filesystem, sizeof(before)) == 0);
    CHECK(lf_ramfs_write(&filesystem, "motd", LF_RAMFS_FILE_MAX, payload, 1u) ==
          LF_ERR_NO_SPACE);
    CHECK(memcmp(before, &filesystem, sizeof(before)) == 0);

    for (index = 0u; index <
         (uint32_t)(sizeof(extra_names) / sizeof(extra_names[0])); ++index) {
        CHECK(lf_ramfs_create(&filesystem, extra_names[index]) == LF_OK);
    }
    CHECK(lf_ramfs_create(&filesystem, "full") == LF_ERR_NO_SPACE);
    CHECK(lf_ramfs_unlink(&filesystem, "motd") == LF_OK);
    CHECK(filesystem.files[0].used == 0u && filesystem.files[0].size == 0u);
    for (index = 0u; index < LF_RAMFS_FILE_MAX; ++index) {
        CHECK(filesystem.files[0].data[index] == 0u);
    }
    CHECK(lf_ramfs_read(&filesystem, "motd", 0u, output, 1u) ==
          LF_ERR_NOT_FOUND);
}

int main(void) {
    test_scheduler();
    test_frames_and_mappings();
    test_ramfs();

    if (failures != 0u) {
        fprintf(stderr, "public_tests: %u check(s) failed\n", failures);
        return 1;
    }
    puts("public_tests: PASS");
    return 0;
}
