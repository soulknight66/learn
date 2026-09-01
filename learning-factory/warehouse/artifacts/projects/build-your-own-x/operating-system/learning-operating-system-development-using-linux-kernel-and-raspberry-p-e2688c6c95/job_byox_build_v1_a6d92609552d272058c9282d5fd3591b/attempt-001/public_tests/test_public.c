#include "pebble.h"

#include <stdint.h>
#include <stdio.h>
#include <string.h>

static int failures;

#define EXPECT(condition)                                                        \
    do {                                                                         \
        if (!(condition)) {                                                       \
            (void)fprintf(stderr, "  line %d: %s\n", __LINE__, #condition);      \
            ++failures;                                                          \
        }                                                                        \
    } while (0)

static void run_test(const char *name, void (*test_fn)(void))
{
    int before = failures;
    test_fn();
    (void)printf("%s %s\n", failures == before ? "PASS" : "FAIL", name);
}

static void test_initialization(void)
{
    pebble_kernel_t kernel;
    char reason[64];

    memset(&kernel, 0xa5, sizeof(kernel));
    pebble_init(&kernel);
    EXPECT(kernel.current_slot == -1);
    EXPECT(kernel.schedule_cursor == 0u);
    EXPECT(kernel.next_pid == 1u);
    EXPECT(kernel.ticks == 0u);
    EXPECT(kernel.processes[0].state == PEBBLE_PROC_UNUSED);
    EXPECT(kernel.frames[0].refs == 0u);
    EXPECT(pebble_check(&kernel, reason, sizeof(reason)) == PEBBLE_OK);
    EXPECT(reason[0] == '\0');
}

static void test_process_round_robin(void)
{
    pebble_kernel_t kernel;
    int32_t first;
    int32_t second;

    pebble_init(&kernel);
    first = pebble_process_create(&kernel);
    second = pebble_process_create(&kernel);
    EXPECT(first == 1);
    EXPECT(second == 2);
    if (first > 0 && second > 0) {
        EXPECT(pebble_schedule(&kernel) == first);
        EXPECT(pebble_schedule(&kernel) == second);
        EXPECT(pebble_process_block(&kernel, second) == PEBBLE_OK);
        EXPECT(pebble_schedule(&kernel) == first);
        EXPECT(pebble_process_wake(&kernel, second) == PEBBLE_OK);
        EXPECT(pebble_schedule(&kernel) == second);
        EXPECT(kernel.ticks == 4u);
    }
}

static void test_memory_and_fork(void)
{
    pebble_kernel_t kernel;
    const uint8_t input[] = {10u, 20u, 30u, 40u, 50u, 60u};
    const uint8_t replacement = 99u;
    uint8_t output[sizeof(input)] = {0u};
    uint8_t parent_byte = 0u;
    uint8_t child_byte = 0u;
    int32_t parent;
    int32_t child;
    uint32_t start = PEBBLE_PAGE_SIZE - 2u;

    pebble_init(&kernel);
    parent = pebble_process_create(&kernel);
    if (parent <= 0) {
        EXPECT(parent > 0);
        return;
    }
    EXPECT(pebble_vm_map(&kernel, parent, 0u,
                         PEBBLE_PAGE_READ | PEBBLE_PAGE_WRITE) == PEBBLE_OK);
    EXPECT(pebble_vm_map(&kernel, parent, 1u,
                         PEBBLE_PAGE_READ | PEBBLE_PAGE_WRITE) == PEBBLE_OK);
    EXPECT(pebble_vm_write(&kernel, parent, start, input, sizeof(input)) ==
           (int32_t)sizeof(input));
    EXPECT(pebble_vm_read(&kernel, parent, start, output, sizeof(output)) ==
           (int32_t)sizeof(output));
    EXPECT(memcmp(input, output, sizeof(input)) == 0);

    child = pebble_process_fork(&kernel, parent);
    EXPECT(child == 2);
    if (child > 0) {
        EXPECT(pebble_vm_write(&kernel, child, start, &replacement, 1u) == 1);
        EXPECT(pebble_vm_read(&kernel, parent, start, &parent_byte, 1u) == 1);
        EXPECT(pebble_vm_read(&kernel, child, start, &child_byte, 1u) == 1);
        EXPECT(parent_byte == input[0]);
        EXPECT(child_byte == replacement);
    }
}

static void test_filesystem_round_trip(void)
{
    pebble_kernel_t kernel;
    const char payload[] = "pebble";
    char output[sizeof(payload)] = {0};
    int32_t pid;
    int32_t fd;

    pebble_init(&kernel);
    pid = pebble_process_create(&kernel);
    if (pid <= 0) {
        EXPECT(pid > 0);
        return;
    }
    fd = pebble_fs_open(&kernel, pid, "notes",
                        PEBBLE_OPEN_READ | PEBBLE_OPEN_WRITE |
                            PEBBLE_OPEN_CREATE);
    EXPECT(fd == 0);
    if (fd >= 0) {
        EXPECT(pebble_fs_write(&kernel, pid, fd, payload, sizeof(payload)) ==
               (int32_t)sizeof(payload));
        EXPECT(pebble_fs_seek(&kernel, pid, fd, 0u) == PEBBLE_OK);
        EXPECT(pebble_fs_read(&kernel, pid, fd, output, sizeof(output)) ==
               (int32_t)sizeof(output));
        EXPECT(memcmp(payload, output, sizeof(payload)) == 0);
        EXPECT(pebble_fs_close(&kernel, pid, fd) == PEBBLE_OK);
        EXPECT(pebble_fs_unlink(&kernel, "notes") == PEBBLE_OK);
    }
}

int main(void)
{
    run_test("initialization", test_initialization);
    run_test("process round robin", test_process_round_robin);
    run_test("memory and fork", test_memory_and_fork);
    run_test("filesystem round trip", test_filesystem_round_trip);

    if (failures != 0) {
        (void)fprintf(stderr, "%d public assertion(s) failed\n", failures);
        return 1;
    }
    (void)printf("all public tests passed\n");
    return 0;
}
