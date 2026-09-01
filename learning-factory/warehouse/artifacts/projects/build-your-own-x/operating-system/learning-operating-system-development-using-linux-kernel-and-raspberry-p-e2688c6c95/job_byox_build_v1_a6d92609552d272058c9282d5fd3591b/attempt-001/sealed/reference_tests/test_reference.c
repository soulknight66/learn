#include "pebble.h"

#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static int failures;

#define EXPECT(condition)                                                        \
    do {                                                                         \
        if (!(condition)) {                                                       \
            (void)fprintf(stderr, "  %s:%d: %s\n", __func__, __LINE__,           \
                          #condition);                                            \
            ++failures;                                                          \
        }                                                                        \
    } while (0)

#define REQUIRE(condition)                                                       \
    do {                                                                         \
        if (!(condition)) {                                                       \
            (void)fprintf(stderr, "  %s:%d: required %s\n", __func__, __LINE__,  \
                          #condition);                                            \
            ++failures;                                                          \
            return;                                                              \
        }                                                                        \
    } while (0)

static void assert_valid(const pebble_kernel_t *kernel)
{
    char reason[96];
    int result = pebble_check(kernel, reason, sizeof(reason));
    if (result != PEBBLE_OK) {
        (void)fprintf(stderr, "  invariant failure: %s\n", reason);
        ++failures;
    }
}

static int same_kernel(const pebble_kernel_t *left,
                       const pebble_kernel_t *right)
{
    return memcmp(left, right, sizeof(*left)) == 0;
}

static size_t process_slot(const pebble_kernel_t *kernel, int32_t pid)
{
    size_t slot;
    for (slot = 0u; slot < PEBBLE_MAX_PROCESSES; ++slot) {
        if (kernel->processes[slot].state != PEBBLE_PROC_UNUSED &&
            kernel->processes[slot].pid == pid) {
            return slot;
        }
    }
    return PEBBLE_MAX_PROCESSES;
}

static void test_initialization_and_diagnostics(void)
{
    pebble_kernel_t kernel;
    char reason[8] = "filled";
    size_t index;

    pebble_init(NULL);
    memset(&kernel, 0xa5, sizeof(kernel));
    pebble_init(&kernel);
    EXPECT(kernel.current_slot == -1);
    EXPECT(kernel.schedule_cursor == 0u);
    EXPECT(kernel.next_pid == 1u);
    EXPECT(kernel.ticks == 0u);
    for (index = 0u; index < PEBBLE_MAX_PROCESSES; ++index) {
        EXPECT(kernel.processes[index].state == PEBBLE_PROC_UNUSED);
    }
    EXPECT(pebble_check(&kernel, reason, sizeof(reason)) == PEBBLE_OK);
    EXPECT(reason[0] == '\0');
    EXPECT(pebble_check(NULL, reason, sizeof(reason)) == PEBBLE_ERR_CORRUPT);
    EXPECT(reason[sizeof(reason) - 1u] == '\0');
    EXPECT(pebble_check(NULL, NULL, 0u) == PEBBLE_ERR_CORRUPT);
}

static void test_process_lifecycle_and_scheduler(void)
{
    pebble_kernel_t kernel;
    int32_t one;
    int32_t two;
    int32_t three;
    int32_t status = 0;

    pebble_init(&kernel);
    EXPECT(pebble_schedule(&kernel) == PEBBLE_ERR_NOT_FOUND);
    EXPECT(kernel.ticks == 1u);
    one = pebble_process_create(&kernel);
    two = pebble_process_create(&kernel);
    three = pebble_process_create(&kernel);
    REQUIRE(one == 1 && two == 2 && three == 3);
    EXPECT(pebble_schedule(&kernel) == one);
    EXPECT(pebble_schedule(&kernel) == two);
    EXPECT(pebble_process_block(&kernel, two) == PEBBLE_OK);
    EXPECT(kernel.current_slot == -1);
    EXPECT(pebble_process_block(&kernel, two) == PEBBLE_ERR_STATE);
    EXPECT(pebble_schedule(&kernel) == three);
    EXPECT(pebble_process_exit(&kernel, three, -17) == PEBBLE_OK);
    EXPECT(kernel.current_slot == -1);
    EXPECT(pebble_process_state(&kernel, three) == PEBBLE_PROC_ZOMBIE);
    EXPECT(pebble_schedule(&kernel) == one);
    EXPECT(pebble_process_wake(&kernel, two) == PEBBLE_OK);
    EXPECT(pebble_schedule(&kernel) == two);
    EXPECT(pebble_process_reap(&kernel, three, &status) == PEBBLE_OK);
    EXPECT(status == -17);
    EXPECT(pebble_process_state(&kernel, three) == PEBBLE_ERR_NOT_FOUND);
    EXPECT(pebble_process_create(&kernel) == 4);
    EXPECT(kernel.processes[2].pid == 4);
    EXPECT(pebble_process_wake(&kernel, one) == PEBBLE_ERR_STATE);
    assert_valid(&kernel);
}

static void test_process_capacity_and_pid_overflow(void)
{
    pebble_kernel_t kernel;
    pebble_kernel_t before;
    int32_t pid = 0;
    size_t index;

    pebble_init(&kernel);
    for (index = 0u; index < PEBBLE_MAX_PROCESSES; ++index) {
        pid = pebble_process_create(&kernel);
        EXPECT(pid == (int32_t)index + 1);
    }
    before = kernel;
    EXPECT(pebble_process_create(&kernel) == PEBBLE_ERR_NO_SPACE);
    EXPECT(same_kernel(&kernel, &before));
    EXPECT(pebble_process_exit(&kernel, pid, 0) == PEBBLE_OK);
    EXPECT(pebble_process_reap(&kernel, pid, NULL) == PEBBLE_OK);
    kernel.next_pid = (uint32_t)INT32_MAX + 1u;
    before = kernel;
    EXPECT(pebble_process_create(&kernel) == PEBBLE_ERR_OVERFLOW);
    EXPECT(same_kernel(&kernel, &before));
}

static void test_virtual_memory_boundaries(void)
{
    pebble_kernel_t kernel;
    pebble_kernel_t before;
    uint8_t zeros[8] = {1u, 1u, 1u, 1u, 1u, 1u, 1u, 1u};
    const uint8_t payload[6] = {3u, 1u, 4u, 1u, 5u, 9u};
    uint8_t output[6] = {0u};
    uint8_t preserved = 0u;
    int32_t pid;

    pebble_init(&kernel);
    pid = pebble_process_create(&kernel);
    REQUIRE(pid > 0);
    EXPECT(pebble_vm_map(&kernel, pid, 0u, PEBBLE_PAGE_READ) == PEBBLE_OK);
    EXPECT(pebble_vm_read(&kernel, pid, 0u, zeros, sizeof(zeros)) ==
           (int32_t)sizeof(zeros));
    EXPECT(memcmp(zeros, (uint8_t[8]){0u}, sizeof(zeros)) == 0);
    EXPECT(pebble_vm_write(&kernel, pid, 0u, payload, 1u) ==
           PEBBLE_ERR_PERMISSION);
    EXPECT(pebble_vm_map(&kernel, pid, 0u, PEBBLE_PAGE_READ) ==
           PEBBLE_ERR_STATE);
    EXPECT(pebble_vm_map(&kernel, pid, 1u,
                         PEBBLE_PAGE_READ | PEBBLE_PAGE_WRITE) == PEBBLE_OK);
    EXPECT(pebble_vm_map(&kernel, pid, 2u,
                         PEBBLE_PAGE_READ | PEBBLE_PAGE_WRITE) == PEBBLE_OK);
    EXPECT(pebble_vm_write(&kernel, pid, 2u * PEBBLE_PAGE_SIZE - 2u,
                           payload, sizeof(payload)) == (int32_t)sizeof(payload));
    EXPECT(pebble_vm_read(&kernel, pid, 2u * PEBBLE_PAGE_SIZE - 2u,
                          output, sizeof(output)) == (int32_t)sizeof(output));
    EXPECT(memcmp(payload, output, sizeof(payload)) == 0);

    before = kernel;
    EXPECT(pebble_vm_write(&kernel, pid, PEBBLE_PAGE_SIZE - 1u, payload, 2u) ==
           PEBBLE_ERR_PERMISSION);
    EXPECT(same_kernel(&kernel, &before));
    EXPECT(pebble_vm_read(&kernel, pid,
                          PEBBLE_PAGE_SIZE * PEBBLE_VIRTUAL_PAGES,
                          NULL, 0u) == 0);
    EXPECT(pebble_vm_read(&kernel, pid,
                          PEBBLE_PAGE_SIZE * PEBBLE_VIRTUAL_PAGES + 1u,
                          NULL, 0u) == PEBBLE_ERR_INVALID);
    EXPECT(pebble_vm_read(&kernel, pid,
                          PEBBLE_PAGE_SIZE * PEBBLE_VIRTUAL_PAGES - 1u,
                          &preserved, 2u) == PEBBLE_ERR_INVALID);
    EXPECT(pebble_vm_unmap(&kernel, pid, 1u) == PEBBLE_OK);
    EXPECT(kernel.frames[1].refs == 0u);
    EXPECT(pebble_vm_unmap(&kernel, pid, 1u) == PEBBLE_ERR_NOT_FOUND);
    assert_valid(&kernel);
}

static void test_copy_on_write_isolation(void)
{
    pebble_kernel_t kernel;
    const uint8_t initial = 41u;
    const uint8_t child_value = 73u;
    const uint8_t parent_value = 19u;
    uint8_t output = 0u;
    int32_t parent;
    int32_t child;
    size_t parent_slot;
    size_t child_slot;
    uint16_t original_frame;

    pebble_init(&kernel);
    parent = pebble_process_create(&kernel);
    REQUIRE(parent > 0);
    EXPECT(pebble_vm_map(&kernel, parent, 0u,
                         PEBBLE_PAGE_READ | PEBBLE_PAGE_WRITE) == PEBBLE_OK);
    EXPECT(pebble_vm_map(&kernel, parent, 1u, PEBBLE_PAGE_READ) == PEBBLE_OK);
    EXPECT(pebble_vm_write(&kernel, parent, 0u, &initial, 1u) == 1);
    child = pebble_process_fork(&kernel, parent);
    REQUIRE(child > 0);
    parent_slot = process_slot(&kernel, parent);
    child_slot = process_slot(&kernel, child);
    REQUIRE(parent_slot < PEBBLE_MAX_PROCESSES);
    REQUIRE(child_slot < PEBBLE_MAX_PROCESSES);
    original_frame = kernel.processes[parent_slot].pages[0].frame;
    EXPECT(kernel.frames[original_frame].refs == 2u);
    EXPECT((kernel.processes[parent_slot].pages[0].flags & PEBBLE_PAGE_COW) != 0u);
    EXPECT((kernel.processes[child_slot].pages[0].flags & PEBBLE_PAGE_COW) != 0u);
    EXPECT(kernel.processes[parent_slot].pages[1].frame ==
           kernel.processes[child_slot].pages[1].frame);
    EXPECT((kernel.processes[parent_slot].pages[1].flags & PEBBLE_PAGE_COW) == 0u);

    EXPECT(pebble_vm_write(&kernel, child, 0u, &child_value, 1u) == 1);
    EXPECT(kernel.frames[original_frame].refs == 1u);
    EXPECT(kernel.processes[child_slot].pages[0].frame != original_frame);
    EXPECT(pebble_vm_read(&kernel, parent, 0u, &output, 1u) == 1);
    EXPECT(output == initial);
    EXPECT(pebble_vm_read(&kernel, child, 0u, &output, 1u) == 1);
    EXPECT(output == child_value);

    EXPECT(pebble_vm_write(&kernel, parent, 0u, &parent_value, 1u) == 1);
    EXPECT(kernel.processes[parent_slot].pages[0].frame == original_frame);
    EXPECT((kernel.processes[parent_slot].pages[0].flags &
            PEBBLE_PAGE_WRITE) != 0u);
    EXPECT((kernel.processes[parent_slot].pages[0].flags & PEBBLE_PAGE_COW) == 0u);
    assert_valid(&kernel);
}

static void test_cow_capacity_is_transactional(void)
{
    pebble_kernel_t kernel;
    pebble_kernel_t before;
    uint8_t bytes[2] = {8u, 9u};
    int32_t parent;
    int32_t child;
    int32_t filler_one;
    int32_t filler_two;
    size_t page;

    pebble_init(&kernel);
    parent = pebble_process_create(&kernel);
    REQUIRE(parent > 0);
    EXPECT(pebble_vm_map(&kernel, parent, 0u,
                         PEBBLE_PAGE_READ | PEBBLE_PAGE_WRITE) == PEBBLE_OK);
    EXPECT(pebble_vm_map(&kernel, parent, 1u,
                         PEBBLE_PAGE_READ | PEBBLE_PAGE_WRITE) == PEBBLE_OK);
    child = pebble_process_fork(&kernel, parent);
    REQUIRE(child > 0);
    filler_one = pebble_process_create(&kernel);
    filler_two = pebble_process_create(&kernel);
    REQUIRE(filler_one > 0 && filler_two > 0);
    for (page = 0u; page < PEBBLE_VIRTUAL_PAGES; ++page) {
        EXPECT(pebble_vm_map(&kernel, filler_one, (uint16_t)page,
                             PEBBLE_PAGE_READ) == PEBBLE_OK);
    }
    for (page = 0u; page < PEBBLE_VIRTUAL_PAGES - 3u; ++page) {
        EXPECT(pebble_vm_map(&kernel, filler_two, (uint16_t)page,
                             PEBBLE_PAGE_READ) == PEBBLE_OK);
    }
    before = kernel;
    EXPECT(pebble_vm_write(&kernel, child, PEBBLE_PAGE_SIZE - 1u,
                           bytes, sizeof(bytes)) == PEBBLE_ERR_NO_SPACE);
    EXPECT(same_kernel(&kernel, &before));
    assert_valid(&kernel);
}

static void test_physical_frame_exhaustion(void)
{
    pebble_kernel_t kernel;
    pebble_kernel_t before;
    uint8_t byte = 0xffu;
    int32_t first;
    int32_t second;
    int32_t third;
    size_t page;

    pebble_init(&kernel);
    first = pebble_process_create(&kernel);
    second = pebble_process_create(&kernel);
    third = pebble_process_create(&kernel);
    REQUIRE(first > 0 && second > 0 && third > 0);
    for (page = 0u; page < PEBBLE_VIRTUAL_PAGES; ++page) {
        EXPECT(pebble_vm_map(&kernel, first, (uint16_t)page,
                             PEBBLE_PAGE_READ) == PEBBLE_OK);
        EXPECT(pebble_vm_map(&kernel, second, (uint16_t)page,
                             PEBBLE_PAGE_READ) == PEBBLE_OK);
    }
    before = kernel;
    EXPECT(pebble_vm_map(&kernel, third, 0u, PEBBLE_PAGE_READ) ==
           PEBBLE_ERR_NO_SPACE);
    EXPECT(same_kernel(&kernel, &before));
    EXPECT(pebble_vm_unmap(&kernel, first, 7u) == PEBBLE_OK);
    EXPECT(pebble_vm_map(&kernel, third, 0u,
                         PEBBLE_PAGE_READ | PEBBLE_PAGE_WRITE) == PEBBLE_OK);
    EXPECT(kernel.processes[2].pages[0].frame == 14u);
    EXPECT(pebble_vm_read(&kernel, third, 0u, &byte, 1u) == 1);
    EXPECT(byte == 0u);
    assert_valid(&kernel);
}

static void test_filesystem_semantics(void)
{
    pebble_kernel_t kernel;
    const char payload[] = "kernel-notes";
    char output[sizeof(payload)] = {0};
    size_t size = 0u;
    int32_t pid;
    int32_t fd;
    int32_t second;

    pebble_init(&kernel);
    pid = pebble_process_create(&kernel);
    REQUIRE(pid > 0);
    EXPECT(pebble_fs_open(&kernel, pid, "", PEBBLE_OPEN_READ) ==
           PEBBLE_ERR_INVALID);
    EXPECT(pebble_fs_open(&kernel, pid, "a/b", PEBBLE_OPEN_READ) ==
           PEBBLE_ERR_INVALID);
    EXPECT(pebble_fs_open(&kernel, pid, "notes", PEBBLE_OPEN_CREATE |
                                                       PEBBLE_OPEN_READ) ==
           PEBBLE_ERR_INVALID);
    fd = pebble_fs_open(&kernel, pid, "notes",
                        PEBBLE_OPEN_CREATE | PEBBLE_OPEN_READ |
                            PEBBLE_OPEN_WRITE);
    REQUIRE(fd == 0);
    EXPECT(pebble_fs_write(&kernel, pid, fd, payload, sizeof(payload)) ==
           (int32_t)sizeof(payload));
    EXPECT(pebble_fs_size(&kernel, pid, fd, &size) == PEBBLE_OK);
    EXPECT(size == sizeof(payload));
    EXPECT(pebble_fs_seek(&kernel, pid, fd, 0u) == PEBBLE_OK);
    second = pebble_fs_open(&kernel, pid, "notes", PEBBLE_OPEN_READ);
    REQUIRE(second == 1);
    EXPECT(pebble_fs_read(&kernel, pid, second, output, 3u) == 3);
    EXPECT(pebble_fs_read(&kernel, pid, fd, output, sizeof(output)) ==
           (int32_t)sizeof(output));
    EXPECT(memcmp(output, payload, sizeof(payload)) == 0);
    EXPECT(pebble_fs_unlink(&kernel, "notes") == PEBBLE_ERR_BUSY);
    EXPECT(pebble_fs_close(&kernel, pid, second) == PEBBLE_OK);
    EXPECT(pebble_fs_close(&kernel, pid, fd) == PEBBLE_OK);
    EXPECT(pebble_fs_unlink(&kernel, "notes") == PEBBLE_OK);
    EXPECT(pebble_fs_open(&kernel, pid, "notes", PEBBLE_OPEN_READ) ==
           PEBBLE_ERR_NOT_FOUND);
    assert_valid(&kernel);
}

static void test_descriptor_fork_and_truncate_rollback(void)
{
    pebble_kernel_t kernel;
    pebble_kernel_t before;
    const char payload[] = "retain me";
    char child_byte = '\0';
    int32_t parent;
    int32_t child;
    int32_t fd;
    size_t fd_index;
    size_t parent_slot;
    size_t child_slot;

    pebble_init(&kernel);
    parent = pebble_process_create(&kernel);
    REQUIRE(parent > 0);
    fd = pebble_fs_open(&kernel, parent, "state",
                        PEBBLE_OPEN_CREATE | PEBBLE_OPEN_READ |
                            PEBBLE_OPEN_WRITE);
    REQUIRE(fd == 0);
    EXPECT(pebble_fs_write(&kernel, parent, fd, payload, sizeof(payload)) ==
           (int32_t)sizeof(payload));
    EXPECT(pebble_fs_seek(&kernel, parent, fd, 2u) == PEBBLE_OK);
    child = pebble_process_fork(&kernel, parent);
    REQUIRE(child > 0);
    parent_slot = process_slot(&kernel, parent);
    child_slot = process_slot(&kernel, child);
    REQUIRE(parent_slot < PEBBLE_MAX_PROCESSES);
    REQUIRE(child_slot < PEBBLE_MAX_PROCESSES);
    EXPECT(kernel.files[0].open_count == 2u);
    EXPECT(pebble_fs_read(&kernel, child, fd, &child_byte, 1u) == 1);
    EXPECT(child_byte == payload[2]);
    EXPECT(kernel.processes[parent_slot].fds[fd].cursor == 2u);
    EXPECT(kernel.processes[child_slot].fds[fd].cursor == 3u);

    for (fd_index = 1u; fd_index < PEBBLE_MAX_FDS; ++fd_index) {
        EXPECT(pebble_fs_open(&kernel, parent, "state",
                              PEBBLE_OPEN_READ | PEBBLE_OPEN_WRITE) ==
               (int32_t)fd_index);
    }
    before = kernel;
    EXPECT(pebble_fs_open(&kernel, parent, "state",
                          PEBBLE_OPEN_WRITE | PEBBLE_OPEN_TRUNCATE) ==
           PEBBLE_ERR_NO_SPACE);
    EXPECT(same_kernel(&kernel, &before));
    assert_valid(&kernel);
}

static void test_truncate_resets_open_cursors(void)
{
    pebble_kernel_t kernel;
    const char payload[] = "abcdef";
    char scratch[3];
    int32_t first_pid;
    int32_t second_pid;
    int32_t first_fd;
    int32_t second_fd;
    int32_t truncating_fd;

    pebble_init(&kernel);
    first_pid = pebble_process_create(&kernel);
    second_pid = pebble_process_create(&kernel);
    REQUIRE(first_pid > 0 && second_pid > 0);
    first_fd = pebble_fs_open(&kernel, first_pid, "shared",
                              PEBBLE_OPEN_CREATE | PEBBLE_OPEN_READ |
                                  PEBBLE_OPEN_WRITE);
    REQUIRE(first_fd == 0);
    EXPECT(pebble_fs_write(&kernel, first_pid, first_fd, payload,
                           sizeof(payload)) == (int32_t)sizeof(payload));
    second_fd = pebble_fs_open(&kernel, second_pid, "shared", PEBBLE_OPEN_READ);
    REQUIRE(second_fd == 0);
    EXPECT(pebble_fs_read(&kernel, second_pid, second_fd, scratch,
                          sizeof(scratch)) == (int32_t)sizeof(scratch));
    truncating_fd = pebble_fs_open(&kernel, first_pid, "shared",
                                   PEBBLE_OPEN_WRITE |
                                       PEBBLE_OPEN_TRUNCATE);
    REQUIRE(truncating_fd == 1);
    EXPECT(kernel.files[0].size == 0u);
    EXPECT(kernel.processes[0].fds[first_fd].cursor == 0u);
    EXPECT(kernel.processes[1].fds[second_fd].cursor == 0u);
    EXPECT(kernel.processes[0].fds[truncating_fd].cursor == 0u);
    EXPECT(pebble_fs_read(&kernel, second_pid, second_fd, scratch,
                          sizeof(scratch)) == 0);
    assert_valid(&kernel);
}

static void test_file_capacity_and_process_cleanup(void)
{
    pebble_kernel_t kernel;
    pebble_kernel_t before;
    uint8_t byte = 7u;
    int32_t parent;
    int32_t child;
    int32_t fd;
    size_t parent_slot;
    uint16_t frame;

    pebble_init(&kernel);
    parent = pebble_process_create(&kernel);
    REQUIRE(parent > 0);
    EXPECT(pebble_vm_map(&kernel, parent, 0u,
                         PEBBLE_PAGE_READ | PEBBLE_PAGE_WRITE) == PEBBLE_OK);
    frame = kernel.processes[0].pages[0].frame;
    fd = pebble_fs_open(&kernel, parent, "blob",
                        PEBBLE_OPEN_CREATE | PEBBLE_OPEN_WRITE);
    REQUIRE(fd >= 0);
    EXPECT(pebble_fs_write(&kernel, parent, fd, &byte, 1u) == 1);
    child = pebble_process_fork(&kernel, parent);
    REQUIRE(child > 0);
    EXPECT(kernel.frames[frame].refs == 2u);
    EXPECT(kernel.files[0].open_count == 2u);
    EXPECT(pebble_process_exit(&kernel, parent, 23) == PEBBLE_OK);
    parent_slot = process_slot(&kernel, parent);
    REQUIRE(parent_slot < PEBBLE_MAX_PROCESSES);
    EXPECT(kernel.processes[parent_slot].state == PEBBLE_PROC_ZOMBIE);
    EXPECT(kernel.frames[frame].refs == 1u);
    EXPECT(kernel.files[0].open_count == 1u);
    EXPECT(pebble_fs_unlink(&kernel, "blob") == PEBBLE_ERR_BUSY);
    EXPECT(pebble_process_exit(&kernel, child, 0) == PEBBLE_OK);
    EXPECT(kernel.frames[frame].refs == 0u);
    EXPECT(kernel.files[0].open_count == 0u);
    EXPECT(pebble_fs_unlink(&kernel, "blob") == PEBBLE_OK);

    before = kernel;
    EXPECT(pebble_process_exit(&kernel, parent, 99) == PEBBLE_ERR_STATE);
    EXPECT(same_kernel(&kernel, &before));
    assert_valid(&kernel);
}

static void test_write_capacity_is_atomic(void)
{
    pebble_kernel_t kernel;
    pebble_kernel_t before;
    uint8_t data[PEBBLE_MAX_FILE_BYTES];
    int32_t pid;
    int32_t fd;

    memset(data, 0x5a, sizeof(data));
    pebble_init(&kernel);
    pid = pebble_process_create(&kernel);
    REQUIRE(pid > 0);
    fd = pebble_fs_open(&kernel, pid, "full",
                        PEBBLE_OPEN_CREATE | PEBBLE_OPEN_WRITE);
    REQUIRE(fd >= 0);
    EXPECT(pebble_fs_write(&kernel, pid, fd, data, sizeof(data)) ==
           (int32_t)sizeof(data));
    before = kernel;
    EXPECT(pebble_fs_write(&kernel, pid, fd, data, 1u) ==
           PEBBLE_ERR_NO_SPACE);
    EXPECT(same_kernel(&kernel, &before));
    EXPECT(pebble_fs_seek(&kernel, pid, fd, PEBBLE_MAX_FILE_BYTES + 1u) ==
           PEBBLE_ERR_INVALID);
    EXPECT(pebble_fs_write(&kernel, pid, fd, NULL, 0u) == 0);
    assert_valid(&kernel);
}

static void test_file_table_exhaustion(void)
{
    static const char *const names[PEBBLE_MAX_FILES] = {
        "f0", "f1", "f2", "f3", "f4", "f5", "f6", "f7"
    };
    pebble_kernel_t kernel;
    pebble_kernel_t before;
    int32_t pid;
    size_t index;

    pebble_init(&kernel);
    pid = pebble_process_create(&kernel);
    REQUIRE(pid > 0);
    for (index = 0u; index < PEBBLE_MAX_FILES; ++index) {
        int32_t fd = pebble_fs_open(&kernel, pid, names[index],
                                    PEBBLE_OPEN_CREATE | PEBBLE_OPEN_WRITE);
        REQUIRE(fd == 0);
        EXPECT(pebble_fs_close(&kernel, pid, fd) == PEBBLE_OK);
    }
    before = kernel;
    EXPECT(pebble_fs_open(&kernel, pid, "overflow",
                          PEBBLE_OPEN_CREATE | PEBBLE_OPEN_WRITE) ==
           PEBBLE_ERR_NO_SPACE);
    EXPECT(same_kernel(&kernel, &before));
    EXPECT(pebble_fs_unlink(&kernel, "f3") == PEBBLE_OK);
    EXPECT(pebble_fs_open(&kernel, pid, "replacement",
                          PEBBLE_OPEN_CREATE | PEBBLE_OPEN_WRITE) == 0);
    EXPECT(strcmp(kernel.files[3].name, "replacement") == 0);
    assert_valid(&kernel);
}

static void test_invariant_checker_detects_corruption(void)
{
    pebble_kernel_t kernel;
    pebble_kernel_t corrupt;
    char reason[64];
    int32_t pid;

    pebble_init(&kernel);
    corrupt = kernel;
    corrupt.files[3].data[0] = 1u;
    EXPECT(pebble_check(&corrupt, reason, sizeof(reason)) ==
           PEBBLE_ERR_CORRUPT);
    EXPECT(strcmp(reason, "dirty unused file") == 0);

    pid = pebble_process_create(&kernel);
    REQUIRE(pid > 0);
    EXPECT(pebble_vm_map(&kernel, pid, 0u, PEBBLE_PAGE_READ) == PEBBLE_OK);
    corrupt = kernel;
    ++corrupt.frames[0].refs;
    EXPECT(pebble_check(&corrupt, reason, sizeof(reason)) ==
           PEBBLE_ERR_CORRUPT);
    EXPECT(strcmp(reason, "frame refcount mismatch") == 0);

    corrupt = kernel;
    corrupt.current_slot = 0;
    EXPECT(pebble_check(&corrupt, reason, sizeof(reason)) ==
           PEBBLE_ERR_CORRUPT);
    EXPECT(strcmp(reason, "running slot mismatch") == 0);

    EXPECT(pebble_process_create(&kernel) == 2);
    corrupt = kernel;
    corrupt.processes[1].pid = corrupt.processes[0].pid;
    EXPECT(pebble_check(&corrupt, reason, sizeof(reason)) ==
           PEBBLE_ERR_CORRUPT);
    EXPECT(strcmp(reason, "duplicate pid") == 0);
}

static void run_test(const char *name, void (*test_fn)(void))
{
    int before = failures;
    test_fn();
    (void)printf("%s %s\n", failures == before ? "PASS" : "FAIL", name);
}

int main(void)
{
    run_test("initialization and diagnostics",
             test_initialization_and_diagnostics);
    run_test("process lifecycle and scheduler",
             test_process_lifecycle_and_scheduler);
    run_test("process capacity and pid overflow",
             test_process_capacity_and_pid_overflow);
    run_test("virtual memory boundaries", test_virtual_memory_boundaries);
    run_test("copy-on-write isolation", test_copy_on_write_isolation);
    run_test("copy-on-write capacity rollback",
             test_cow_capacity_is_transactional);
    run_test("physical frame exhaustion", test_physical_frame_exhaustion);
    run_test("filesystem semantics", test_filesystem_semantics);
    run_test("descriptor fork and truncate rollback",
             test_descriptor_fork_and_truncate_rollback);
    run_test("truncate resets open cursors",
             test_truncate_resets_open_cursors);
    run_test("file capacity and process cleanup",
             test_file_capacity_and_process_cleanup);
    run_test("write capacity rollback", test_write_capacity_is_atomic);
    run_test("file table exhaustion", test_file_table_exhaustion);
    run_test("invariant corruption detection",
             test_invariant_checker_detects_corruption);

    if (failures != 0) {
        (void)fprintf(stderr, "%d reference assertion(s) failed\n", failures);
        return 1;
    }
    (void)printf("all reference tests passed\n");
    return 0;
}
