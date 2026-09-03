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

static int test_initialization_and_transactional_errors(void)
{
    struct cairn_kernel kernel;
    struct cairn_kernel before;
    char unterminated[CAIRN_NAME_CAP];
    int output = 31337;
    int i;

    memset(&kernel, 0xA5, sizeof(kernel));
    cairn_init(&kernel);
    CHECK(kernel.next_pid == 1 && kernel.current_slot == -1);
    for (i = 0; i < CAIRN_MAX_FRAMES; ++i) {
        CHECK(kernel.frame_owner[i] == -1);
    }
    CHECK(cairn_validate(&kernel) == CAIRN_OK);

    before = kernel;
    CHECK(cairn_spawn(&kernel, CAIRN_USER_TOP, &output) == CAIRN_ERR_INVALID);
    CHECK(output == 31337 && memcmp(&kernel, &before, sizeof(kernel)) == 0);
    CHECK(cairn_spawn(&kernel, 0U, NULL) == CAIRN_ERR_INVALID);
    CHECK(memcmp(&kernel, &before, sizeof(kernel)) == 0);
    CHECK(cairn_create(&kernel, "") == CAIRN_ERR_INVALID);
    CHECK(cairn_create(&kernel, "a/b") == CAIRN_ERR_INVALID);
    memset(unterminated, 'x', sizeof(unterminated));
    CHECK(cairn_create(&kernel, unterminated) == CAIRN_ERR_INVALID);
    CHECK(memcmp(&kernel, &before, sizeof(kernel)) == 0);
    CHECK(cairn_open(&kernel, 1, "missing", &output) == CAIRN_ERR_NOT_FOUND);
    CHECK(output == 31337 && memcmp(&kernel, &before, sizeof(kernel)) == 0);
    return 1;
}

static int test_process_capacity_and_reuse(void)
{
    struct cairn_kernel kernel;
    int pids[CAIRN_MAX_PROCESSES];
    int output = -77;
    int running;
    int replacement;
    int i;

    cairn_init(&kernel);
    for (i = 0; i < CAIRN_MAX_PROCESSES; ++i) {
        CHECK(cairn_spawn(&kernel, (cairn_u32)i, &pids[i]) == CAIRN_OK);
        CHECK(pids[i] == i + 1);
    }
    CHECK(cairn_spawn(&kernel, 0U, &output) == CAIRN_ERR_NO_SPACE);
    CHECK(output == -77);
    CHECK(cairn_schedule(&kernel, &running) == CAIRN_OK && running == pids[0]);
    CHECK(cairn_exit_current(&kernel, 9) == CAIRN_OK);
    CHECK(cairn_spawn(&kernel, 0x55U, &replacement) == CAIRN_OK);
    CHECK(replacement == CAIRN_MAX_PROCESSES + 1);
    CHECK(kernel.processes[0].entry == 0x55U);
    CHECK(kernel.processes[0].exit_code == 0);
    CHECK(cairn_schedule(&kernel, &running) == CAIRN_OK && running == pids[1]);
    CHECK(cairn_validate(&kernel) == CAIRN_OK);
    return 1;
}

static int test_scheduler_no_runnable_is_transactional(void)
{
    struct cairn_kernel kernel;
    struct cairn_kernel before;
    int pid;
    int running;
    int output = 444;

    cairn_init(&kernel);
    CHECK(cairn_spawn(&kernel, 0U, &pid) == CAIRN_OK);
    CHECK(cairn_schedule(&kernel, &running) == CAIRN_OK && running == pid);
    CHECK(cairn_block_current(&kernel) == CAIRN_OK);
    before = kernel;
    CHECK(cairn_schedule(&kernel, &output) == CAIRN_ERR_NO_RUNNABLE);
    CHECK(output == 444 && memcmp(&kernel, &before, sizeof(kernel)) == 0);
    CHECK(cairn_wake(&kernel, pid) == CAIRN_OK);
    CHECK(cairn_wake(&kernel, pid) == CAIRN_ERR_BAD_STATE);
    CHECK(cairn_schedule(&kernel, &running) == CAIRN_OK && running == pid);
    CHECK(cairn_schedule(&kernel, &running) == CAIRN_OK && running == pid);
    CHECK(cairn_validate(&kernel) == CAIRN_OK);
    return 1;
}

static int test_mapping_boundaries_and_precedence(void)
{
    struct cairn_kernel kernel;
    struct cairn_kernel before;
    cairn_u32 physical = 0xCAFEBABEU;
    int first;
    int second;
    int i;

    cairn_init(&kernel);
    CHECK(cairn_spawn(&kernel, 0U, &first) == CAIRN_OK);
    CHECK(cairn_spawn(&kernel, 0U, &second) == CAIRN_OK);
    for (i = 0; i < CAIRN_MAX_MAPPINGS; ++i) {
        CHECK(cairn_map(&kernel, first, (cairn_u32)i * CAIRN_PAGE_SIZE,
                        (cairn_u32)i, i & 1) == CAIRN_OK);
    }
    before = kernel;
    CHECK(cairn_map(&kernel, first, 0U, 20U, 1) == CAIRN_ERR_EXISTS);
    CHECK(memcmp(&kernel, &before, sizeof(kernel)) == 0);
    CHECK(cairn_map(&kernel, first, 9U * CAIRN_PAGE_SIZE, 0U, 1) == CAIRN_ERR_BUSY);
    CHECK(cairn_map(&kernel, first, 9U * CAIRN_PAGE_SIZE, 20U, 1) ==
          CAIRN_ERR_NO_SPACE);
    CHECK(cairn_map(&kernel, second, 0U, 0U, 1) == CAIRN_ERR_BUSY);
    CHECK(cairn_translate(&kernel, first, 1U, 1, &physical) == CAIRN_ERR_PERMISSION);
    CHECK(physical == 0xCAFEBABEU);
    CHECK(cairn_translate(&kernel, first, CAIRN_USER_TOP, 0, &physical) ==
          CAIRN_ERR_INVALID);
    CHECK(physical == 0xCAFEBABEU);
    CHECK(cairn_unmap(&kernel, first, 0U) == CAIRN_OK);
    CHECK(cairn_map(&kernel, second, 0U, 0U, 1) == CAIRN_OK);
    CHECK(cairn_translate(&kernel, second, CAIRN_PAGE_SIZE - 1U, 1, &physical) ==
          CAIRN_OK);
    CHECK(physical == CAIRN_PAGE_SIZE - 1U);
    CHECK(cairn_validate(&kernel) == CAIRN_OK);
    return 1;
}

static int test_inode_capacity_and_names(void)
{
    struct cairn_kernel kernel;
    char name[CAIRN_NAME_CAP];
    int i;

    cairn_init(&kernel);
    for (i = 0; i < CAIRN_MAX_FILES; ++i) {
        CHECK(snprintf(name, sizeof(name), "file-%02d", i) > 0);
        CHECK(cairn_create(&kernel, name) == CAIRN_OK);
    }
    CHECK(cairn_create(&kernel, "file-00") == CAIRN_ERR_EXISTS);
    CHECK(cairn_create(&kernel, "overflow") == CAIRN_ERR_NO_SPACE);
    CHECK(cairn_unlink(&kernel, "file-07") == CAIRN_OK);
    CHECK(cairn_create(&kernel, "replacement") == CAIRN_OK);
    CHECK(cairn_unlink(&kernel, "does-not-exist") == CAIRN_ERR_NOT_FOUND);
    CHECK(cairn_validate(&kernel) == CAIRN_OK);
    return 1;
}

static int test_descriptor_independence_and_capacity(void)
{
    struct cairn_kernel kernel;
    const char text[3] = {'a', 'b', 'c'};
    char received[3] = {0, 0, 0};
    char one = '\0';
    cairn_size transferred;
    int descriptors[CAIRN_MAX_FDS];
    int output = 999;
    int pid;
    int i;

    cairn_init(&kernel);
    CHECK(cairn_spawn(&kernel, 0U, &pid) == CAIRN_OK);
    CHECK(cairn_create(&kernel, "shared") == CAIRN_OK);
    for (i = 0; i < CAIRN_MAX_FDS; ++i) {
        CHECK(cairn_open(&kernel, pid, "shared", &descriptors[i]) == CAIRN_OK);
        CHECK(descriptors[i] == i);
    }
    CHECK(cairn_open(&kernel, pid, "shared", &output) == CAIRN_ERR_NO_SPACE);
    CHECK(output == 999);
    CHECK(cairn_write(&kernel, pid, descriptors[0], text, 3U, &transferred) == CAIRN_OK);
    CHECK(transferred == 3U);
    CHECK(cairn_read(&kernel, pid, descriptors[1], received, 2U, &transferred) == CAIRN_OK);
    CHECK(transferred == 2U && received[0] == 'a' && received[1] == 'b');
    CHECK(cairn_read(&kernel, pid, descriptors[2], received, 3U, &transferred) == CAIRN_OK);
    CHECK(transferred == 3U && memcmp(received, text, 3U) == 0);
    CHECK(cairn_seek(&kernel, pid, descriptors[0], 0U) == CAIRN_OK);
    CHECK(cairn_write(&kernel, pid, descriptors[0], "Z", 1U, &transferred) == CAIRN_OK);
    CHECK(cairn_read(&kernel, pid, descriptors[3], &one, 1U, &transferred) == CAIRN_OK);
    CHECK(one == 'Z');
    CHECK(cairn_unlink(&kernel, "shared") == CAIRN_ERR_BUSY);
    for (i = 0; i < CAIRN_MAX_FDS; ++i) {
        CHECK(cairn_close(&kernel, pid, descriptors[i]) == CAIRN_OK);
    }
    CHECK(cairn_unlink(&kernel, "shared") == CAIRN_OK);
    CHECK(cairn_validate(&kernel) == CAIRN_OK);
    return 1;
}

static int test_file_capacity_is_atomic(void)
{
    struct cairn_kernel kernel;
    struct cairn_kernel before;
    unsigned char input[CAIRN_FILE_CAP];
    unsigned char output[CAIRN_FILE_CAP];
    cairn_size transferred = 0U;
    int pid;
    int fd;
    int i;

    for (i = 0; i < CAIRN_FILE_CAP; ++i) {
        input[i] = (unsigned char)(i ^ 0x5A);
    }
    cairn_init(&kernel);
    CHECK(cairn_spawn(&kernel, 0U, &pid) == CAIRN_OK);
    CHECK(cairn_create(&kernel, "full") == CAIRN_OK);
    CHECK(cairn_open(&kernel, pid, "full", &fd) == CAIRN_OK);
    CHECK(cairn_write(&kernel, pid, fd, input, CAIRN_FILE_CAP, &transferred) == CAIRN_OK);
    CHECK(transferred == CAIRN_FILE_CAP);
    before = kernel;
    transferred = 123U;
    CHECK(cairn_write(&kernel, pid, fd, "x", 1U, &transferred) == CAIRN_ERR_NO_SPACE);
    CHECK(transferred == 123U && memcmp(&kernel, &before, sizeof(kernel)) == 0);
    CHECK(cairn_seek(&kernel, pid, fd, 0U) == CAIRN_OK);
    memset(output, 0, sizeof(output));
    CHECK(cairn_read(&kernel, pid, fd, output, sizeof(output), &transferred) == CAIRN_OK);
    CHECK(transferred == sizeof(output) && memcmp(input, output, sizeof(input)) == 0);
    CHECK(cairn_read(&kernel, pid, fd, NULL, 0U, &transferred) == CAIRN_OK);
    CHECK(transferred == 0U);
    before = kernel;
    transferred = 88U;
    CHECK(cairn_read(&kernel, pid, fd, NULL, 1U, &transferred) == CAIRN_ERR_INVALID);
    CHECK(transferred == 88U && memcmp(&kernel, &before, sizeof(kernel)) == 0);
    CHECK(cairn_seek(&kernel, pid, fd, CAIRN_FILE_CAP + 1U) == CAIRN_ERR_INVALID);
    CHECK(cairn_validate(&kernel) == CAIRN_OK);
    return 1;
}

static int test_exit_cleanup_crosses_subsystems(void)
{
    struct cairn_kernel kernel;
    int first;
    int second;
    int replacement;
    int running;
    int fd;
    enum cairn_process_state state;

    cairn_init(&kernel);
    CHECK(cairn_spawn(&kernel, 0U, &first) == CAIRN_OK);
    CHECK(cairn_spawn(&kernel, 0U, &second) == CAIRN_OK);
    CHECK(cairn_map(&kernel, first, 0U, 12U, 1) == CAIRN_OK);
    CHECK(cairn_create(&kernel, "lifetime") == CAIRN_OK);
    CHECK(cairn_open(&kernel, first, "lifetime", &fd) == CAIRN_OK);
    CHECK(cairn_schedule(&kernel, &running) == CAIRN_OK && running == first);
    CHECK(cairn_exit_current(&kernel, -41) == CAIRN_OK);
    CHECK(kernel.frame_owner[12] == -1);
    CHECK(cairn_unlink(&kernel, "lifetime") == CAIRN_OK);
    CHECK(cairn_process_state(&kernel, first, &state) == CAIRN_OK);
    CHECK(state == CAIRN_PROCESS_EXITED && kernel.processes[0].exit_code == -41);
    CHECK(cairn_spawn(&kernel, 0U, &replacement) == CAIRN_OK);
    CHECK(replacement == 3);
    CHECK(cairn_process_state(&kernel, first, &state) == CAIRN_ERR_NOT_FOUND);
    CHECK(cairn_process_state(&kernel, second, &state) == CAIRN_OK);
    CHECK(cairn_validate(&kernel) == CAIRN_OK);
    return 1;
}

static int test_validator_rejects_corruption_safely(void)
{
    struct cairn_kernel base;
    struct cairn_kernel bad;
    int first;
    int second;
    int fd;

    cairn_init(&base);
    CHECK(cairn_spawn(&base, 0U, &first) == CAIRN_OK);
    CHECK(cairn_spawn(&base, 0U, &second) == CAIRN_OK);
    CHECK(cairn_map(&base, first, 0U, 5U, 1) == CAIRN_OK);
    CHECK(cairn_create(&base, "one") == CAIRN_OK);
    CHECK(cairn_create(&base, "two") == CAIRN_OK);
    CHECK(cairn_open(&base, first, "one", &fd) == CAIRN_OK);
    CHECK(cairn_validate(&base) == CAIRN_OK);

    memset(&bad, 0xFF, sizeof(bad));
    CHECK(cairn_validate(&bad) == CAIRN_ERR_CORRUPT);
    CHECK(cairn_validate(NULL) == CAIRN_ERR_CORRUPT);

    bad = base;
    bad.processes[1].pid = first;
    CHECK(cairn_validate(&bad) == CAIRN_ERR_CORRUPT);
    bad = base;
    bad.frame_owner[5] = second;
    CHECK(cairn_validate(&bad) == CAIRN_ERR_CORRUPT);
    bad = base;
    bad.processes[0].mappings[1] = bad.processes[0].mappings[0];
    CHECK(cairn_validate(&bad) == CAIRN_ERR_CORRUPT);
    bad = base;
    bad.processes[0].descriptors[fd].inode_slot = CAIRN_MAX_FILES;
    CHECK(cairn_validate(&bad) == CAIRN_ERR_CORRUPT);
    bad = base;
    memcpy(bad.inodes[1].name, bad.inodes[0].name, CAIRN_NAME_CAP);
    CHECK(cairn_validate(&bad) == CAIRN_ERR_CORRUPT);
    bad = base;
    memset(bad.inodes[0].name, 'q', CAIRN_NAME_CAP);
    CHECK(cairn_validate(&bad) == CAIRN_ERR_CORRUPT);
    bad = base;
    bad.current_slot = CAIRN_MAX_PROCESSES - 1;
    CHECK(cairn_validate(&bad) == CAIRN_ERR_CORRUPT);
    bad = base;
    bad.current_slot = 0;
    bad.processes[0].state = CAIRN_PROCESS_RUNNING;
    bad.processes[1].state = CAIRN_PROCESS_RUNNING;
    CHECK(cairn_validate(&bad) == CAIRN_ERR_CORRUPT);
    bad = base;
    bad.processes[0].state = CAIRN_PROCESS_EXITED;
    CHECK(cairn_validate(&bad) == CAIRN_ERR_CORRUPT);
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
    run_test("initialization and transactional errors",
             test_initialization_and_transactional_errors);
    run_test("process capacity and reuse", test_process_capacity_and_reuse);
    run_test("scheduler no-runnable transaction",
             test_scheduler_no_runnable_is_transactional);
    run_test("mapping boundaries and precedence", test_mapping_boundaries_and_precedence);
    run_test("inode capacity and names", test_inode_capacity_and_names);
    run_test("descriptor independence and capacity",
             test_descriptor_independence_and_capacity);
    run_test("file capacity atomicity", test_file_capacity_is_atomic);
    run_test("cross-subsystem exit cleanup", test_exit_cleanup_crosses_subsystems);
    run_test("validator corruption rejection", test_validator_rejects_corruption_safely);
    if (failures != 0) {
        printf("reference tests: %d failed\n", failures);
        return 1;
    }
    puts("reference tests: 9 passed");
    return 0;
}
