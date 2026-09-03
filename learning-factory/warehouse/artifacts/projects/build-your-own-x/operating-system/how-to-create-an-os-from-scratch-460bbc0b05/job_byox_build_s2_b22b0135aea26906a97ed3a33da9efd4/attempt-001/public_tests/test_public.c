#include <stdio.h>
#include <string.h>

#include "cairn.h"

static int failures;

#define CHECK(expression) do { \
    if (!(expression)) { \
        printf("  FAIL %s:%d: %s\n", __FILE__, __LINE__, #expression); \
        return 0; \
    } \
} while (0)

static int test_process_round_robin(void)
{
    struct cairn_kernel kernel;
    int first = -1;
    int second = -1;
    int running = -1;
    enum cairn_process_state state = CAIRN_PROCESS_EMPTY;

    cairn_init(&kernel);
    CHECK(cairn_spawn(&kernel, 0x1000U, &first) == CAIRN_OK);
    CHECK(cairn_spawn(&kernel, 0x2000U, &second) == CAIRN_OK);
    CHECK(first == 1 && second == 2);
    CHECK(cairn_schedule(&kernel, &running) == CAIRN_OK && running == first);
    CHECK(cairn_schedule(&kernel, &running) == CAIRN_OK && running == second);
    CHECK(cairn_block_current(&kernel) == CAIRN_OK);
    CHECK(cairn_process_state(&kernel, second, &state) == CAIRN_OK);
    CHECK(state == CAIRN_PROCESS_BLOCKED);
    CHECK(cairn_schedule(&kernel, &running) == CAIRN_OK && running == first);
    CHECK(cairn_wake(&kernel, second) == CAIRN_OK);
    CHECK(cairn_validate(&kernel) == CAIRN_OK);
    return 1;
}

static int test_mapping_translation(void)
{
    struct cairn_kernel kernel;
    cairn_u32 physical = 0xDEADBEEFU;
    int pid = -1;

    cairn_init(&kernel);
    CHECK(cairn_spawn(&kernel, 0U, &pid) == CAIRN_OK);
    CHECK(cairn_map(&kernel, pid, 0x4000U, 7U, 0) == CAIRN_OK);
    CHECK(cairn_translate(&kernel, pid, 0x4123U, 0, &physical) == CAIRN_OK);
    CHECK(physical == 0x7123U);
    CHECK(cairn_translate(&kernel, pid, 0x4123U, 1, &physical) ==
          CAIRN_ERR_PERMISSION);
    CHECK(physical == 0x7123U);
    CHECK(cairn_map(&kernel, pid, 0x4001U, 8U, 1) == CAIRN_ERR_INVALID);
    CHECK(cairn_unmap(&kernel, pid, 0x4000U) == CAIRN_OK);
    CHECK(kernel.frame_owner[7] == -1);
    CHECK(cairn_validate(&kernel) == CAIRN_OK);
    return 1;
}

static int test_file_descriptors(void)
{
    struct cairn_kernel kernel;
    const char message[] = "cairn";
    char received[sizeof(message)] = {0};
    cairn_size count = 99U;
    int pid = -1;
    int fd = -1;

    cairn_init(&kernel);
    CHECK(cairn_spawn(&kernel, 0U, &pid) == CAIRN_OK);
    CHECK(cairn_create(&kernel, "notes") == CAIRN_OK);
    CHECK(cairn_open(&kernel, pid, "notes", &fd) == CAIRN_OK && fd == 0);
    CHECK(cairn_write(&kernel, pid, fd, message, sizeof(message), &count) == CAIRN_OK);
    CHECK(count == sizeof(message));
    CHECK(cairn_seek(&kernel, pid, fd, 0U) == CAIRN_OK);
    CHECK(cairn_read(&kernel, pid, fd, received, sizeof(received), &count) == CAIRN_OK);
    CHECK(count == sizeof(received));
    CHECK(memcmp(received, message, sizeof(message)) == 0);
    CHECK(cairn_unlink(&kernel, "notes") == CAIRN_ERR_BUSY);
    CHECK(cairn_close(&kernel, pid, fd) == CAIRN_OK);
    CHECK(cairn_unlink(&kernel, "notes") == CAIRN_OK);
    CHECK(cairn_validate(&kernel) == CAIRN_OK);
    return 1;
}

static int test_exit_releases_resources(void)
{
    struct cairn_kernel kernel;
    int pid = -1;
    int running = -1;
    int fd = -1;
    enum cairn_process_state state = CAIRN_PROCESS_EMPTY;

    cairn_init(&kernel);
    CHECK(cairn_spawn(&kernel, 0U, &pid) == CAIRN_OK);
    CHECK(cairn_map(&kernel, pid, 0U, 2U, 1) == CAIRN_OK);
    CHECK(cairn_create(&kernel, "held") == CAIRN_OK);
    CHECK(cairn_open(&kernel, pid, "held", &fd) == CAIRN_OK);
    CHECK(cairn_schedule(&kernel, &running) == CAIRN_OK && running == pid);
    CHECK(cairn_exit_current(&kernel, 17) == CAIRN_OK);
    CHECK(kernel.frame_owner[2] == -1);
    CHECK(cairn_unlink(&kernel, "held") == CAIRN_OK);
    CHECK(cairn_process_state(&kernel, pid, &state) == CAIRN_OK);
    CHECK(state == CAIRN_PROCESS_EXITED);
    CHECK(cairn_validate(&kernel) == CAIRN_OK);
    return 1;
}

static void run_test(const char *name, int (*test)(void))
{
    if (test()) {
        printf("  PASS %s\n", name);
    } else {
        ++failures;
    }
}

int main(void)
{
    run_test("process round robin", test_process_round_robin);
    run_test("mapping translation", test_mapping_translation);
    run_test("file descriptors", test_file_descriptors);
    run_test("exit cleanup", test_exit_releases_resources);
    if (failures != 0) {
        printf("public tests: %d failed\n", failures);
        return 1;
    }
    puts("public tests: 4 passed");
    return 0;
}
