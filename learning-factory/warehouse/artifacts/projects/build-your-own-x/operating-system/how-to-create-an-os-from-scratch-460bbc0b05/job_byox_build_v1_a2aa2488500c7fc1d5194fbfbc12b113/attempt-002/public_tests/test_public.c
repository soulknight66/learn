#include "micaos.h"

#include <stdbool.h>
#include <stdio.h>
#include <string.h>

#define CHECK(expression)                                                     \
    do {                                                                      \
        if (!(expression)) {                                                  \
            (void)printf("    line %d: %s\n", __LINE__, #expression);        \
            return false;                                                     \
        }                                                                     \
    } while (false)

typedef bool (*test_function_t)(void);

typedef struct public_test {
    const char *name;
    test_function_t function;
} public_test_t;

static size_t running_count(const mica_scheduler_t *scheduler)
{
    size_t index;
    size_t count = 0u;

    for (index = 0u; index < MICA_MAX_PROCESSES; ++index) {
        if (scheduler->processes[index].state == MICA_PROCESS_RUNNING) {
            ++count;
        }
    }
    return count;
}

static bool ramfs_equal(const mica_ramfs_t *left, const mica_ramfs_t *right)
{
    size_t file;
    size_t byte;

    for (file = 0u; file < MICA_MAX_FILES; ++file) {
        if (left->files[file].used != right->files[file].used ||
            left->files[file].size != right->files[file].size) {
            return false;
        }
        for (byte = 0u; byte <= MICA_NAME_MAX; ++byte) {
            if (left->files[file].name[byte] != right->files[file].name[byte]) {
                return false;
            }
        }
        for (byte = 0u; byte < MICA_FILE_CAPACITY; ++byte) {
            if (left->files[file].data[byte] != right->files[file].data[byte]) {
                return false;
            }
        }
    }
    return true;
}

static bool test_initializers_and_constants(void)
{
    mica_scheduler_t scheduler;
    mica_vm_t vm;
    mica_address_space_t space;
    mica_ramfs_t fs;
    size_t outer;
    size_t inner;

    CHECK(MICA_MAX_PROCESSES == 8u);
    CHECK(MICA_VIRTUAL_PAGES == 16u);
    CHECK(MICA_PHYSICAL_FRAMES == 8u);
    CHECK(MICA_PAGE_SIZE == 64u);
    CHECK(MICA_MAX_FILES == 8u);
    CHECK(MICA_NAME_MAX == 15u);
    CHECK(MICA_FILE_CAPACITY == 128u);
    CHECK(MICA_OK == 0);
    CHECK(MICA_ERR_PERM == -7);

    (void)memset(&scheduler, 0xa5, sizeof(scheduler));
    mica_scheduler_init(&scheduler);
    CHECK(scheduler.next_pid == 1u);
    CHECK(scheduler.cursor == MICA_MAX_PROCESSES - 1u);
    for (outer = 0u; outer < MICA_MAX_PROCESSES; ++outer) {
        CHECK(scheduler.processes[outer].pid == 0u);
        CHECK(scheduler.processes[outer].state == MICA_PROCESS_UNUSED);
        CHECK(scheduler.processes[outer].exit_code == 0);
    }

    (void)memset(&vm, 0xa5, sizeof(vm));
    mica_vm_init(&vm);
    for (outer = 0u; outer < MICA_PHYSICAL_FRAMES; ++outer) {
        CHECK(!vm.frame_used[outer]);
        for (inner = 0u; inner < MICA_PAGE_SIZE; ++inner) {
            CHECK(vm.frames[outer][inner] == 0u);
        }
    }

    (void)memset(&space, 0xa5, sizeof(space));
    mica_vm_space_init(&space);
    for (outer = 0u; outer < MICA_VIRTUAL_PAGES; ++outer) {
        CHECK(!space.pages[outer].mapped);
        CHECK(!space.pages[outer].writable);
        CHECK(space.pages[outer].frame == 0u);
    }

    (void)memset(&fs, 0xa5, sizeof(fs));
    mica_ramfs_init(&fs);
    for (outer = 0u; outer < MICA_MAX_FILES; ++outer) {
        CHECK(!fs.files[outer].used);
        CHECK(fs.files[outer].name[0] == '\0');
        CHECK(fs.files[outer].size == 0u);
    }
    return true;
}

static bool test_scheduler_validation(void)
{
    mica_scheduler_t scheduler;
    mica_process_info_t info = {91u, MICA_PROCESS_EXITED, 17};
    mica_pid_t pid = 73u;
    size_t index;

    mica_scheduler_init(&scheduler);
    CHECK(mica_scheduler_spawn(NULL, &pid) == MICA_ERR_ARG);
    CHECK(mica_scheduler_spawn(&scheduler, NULL) == MICA_ERR_ARG);
    CHECK(mica_scheduler_schedule(&scheduler, &pid) == MICA_ERR_NOT_FOUND);
    CHECK(pid == 73u);
    CHECK(mica_scheduler_inspect(&scheduler, 0u, &info) == MICA_ERR_ARG);
    CHECK(mica_scheduler_get(&scheduler, 9u, &info) == MICA_ERR_NOT_FOUND);
    CHECK(info.pid == 91u);
    CHECK(mica_scheduler_block(&scheduler, 9u) == MICA_ERR_NOT_FOUND);
    CHECK(mica_scheduler_wake(&scheduler, 0u) == MICA_ERR_ARG);
    CHECK(mica_scheduler_exit(NULL, 1u, 0) == MICA_ERR_ARG);
    CHECK(mica_scheduler_reap(&scheduler, 1u, NULL) == MICA_ERR_ARG);

    for (index = 0u; index < MICA_MAX_PROCESSES; ++index) {
        scheduler.processes[index].pid = (mica_pid_t)(index + 1u);
        scheduler.processes[index].state = MICA_PROCESS_READY;
    }
    CHECK(mica_scheduler_spawn(&scheduler, &pid) == MICA_ERR_FULL);
    CHECK(pid == 73u);
    return true;
}

static bool test_vm_validation(void)
{
    mica_vm_t vm;
    mica_address_space_t space;
    uint8_t value = 0x5au;

    mica_vm_init(&vm);
    mica_vm_space_init(&space);
    CHECK(mica_vm_map(NULL, &space, 0u, true) == MICA_ERR_ARG);
    CHECK(mica_vm_map(&vm, &space, MICA_VIRTUAL_PAGES, true) ==
          MICA_ERR_RANGE);
    CHECK(mica_vm_unmap(&vm, &space, 0u) == MICA_ERR_NOT_FOUND);
    CHECK(mica_vm_read_u8(&vm, &space, 0u, &value) == MICA_ERR_NOT_FOUND);
    CHECK(value == 0x5au);
    CHECK(mica_vm_read_u8(&vm, &space,
                          MICA_VIRTUAL_PAGES * MICA_PAGE_SIZE,
                          &value) == MICA_ERR_RANGE);
    CHECK(mica_vm_write_u8(&vm, &space, 0u, 1u) == MICA_ERR_NOT_FOUND);

    space.pages[0].mapped = true;
    space.pages[0].writable = false;
    space.pages[0].frame = 0u;
    vm.frame_used[0] = true;
    vm.frames[0][0] = 0x33u;
    CHECK(mica_vm_write_u8(&vm, &space, 0u, 0x44u) == MICA_ERR_PERM);
    CHECK(vm.frames[0][0] == 0x33u);
    return true;
}

static bool test_ramfs_validation(void)
{
    mica_ramfs_t fs;
    mica_ramfs_t before;
    mica_ramfs_stat_t stat = {55u};
    uint8_t byte = 0x5au;
    uint8_t output = 0u;
    size_t amount = 41u;

    mica_ramfs_init(&fs);
    CHECK(mica_ramfs_create(NULL, "x") == MICA_ERR_ARG);
    CHECK(mica_ramfs_create(&fs, NULL) == MICA_ERR_ARG);
    CHECK(mica_ramfs_create(&fs, "") == MICA_ERR_ARG);
    CHECK(mica_ramfs_create(&fs, ".") == MICA_ERR_ARG);
    CHECK(mica_ramfs_create(&fs, "..") == MICA_ERR_ARG);
    CHECK(mica_ramfs_create(&fs, "a/b") == MICA_ERR_ARG);
    CHECK(mica_ramfs_create(&fs, "abcdefghijklmnop") == MICA_ERR_ARG);
    CHECK(mica_ramfs_write(&fs, "missing", 0u, &byte, 1u) ==
          MICA_ERR_NOT_FOUND);
    CHECK(mica_ramfs_read(&fs, "missing", 0u, &output, 1u, &amount) ==
          MICA_ERR_NOT_FOUND);
    CHECK(amount == 41u);
    CHECK(mica_ramfs_stat(&fs, "missing", &stat) == MICA_ERR_NOT_FOUND);
    CHECK(stat.size == 55u);
    CHECK(mica_ramfs_unlink(&fs, "missing") == MICA_ERR_NOT_FOUND);

    fs.files[0].used = true;
    fs.files[0].name[0] = 'x';
    fs.files[0].name[1] = '\0';
    fs.files[0].data[0] = 0x77u;
    fs.files[0].size = 1u;
    before = fs;
    CHECK(mica_ramfs_write(&fs, "x", MICA_FILE_CAPACITY, &byte, 1u) ==
          MICA_ERR_RANGE);
    CHECK(ramfs_equal(&fs, &before));
    return true;
}

static bool test_scheduler_lifecycle(void)
{
    mica_scheduler_t scheduler;
    mica_process_info_t info;
    mica_pid_t first;
    mica_pid_t second;
    mica_pid_t third;
    mica_pid_t selected;
    int exit_code = -1;

    mica_scheduler_init(&scheduler);
    CHECK(mica_scheduler_spawn(&scheduler, &first) == MICA_OK);
    CHECK(mica_scheduler_spawn(&scheduler, &second) == MICA_OK);
    CHECK(mica_scheduler_spawn(&scheduler, &third) == MICA_OK);
    CHECK(first == 1u && second == 2u && third == 3u);

    CHECK(mica_scheduler_block(&scheduler, third) == MICA_OK);
    CHECK(mica_scheduler_schedule(&scheduler, &selected) == MICA_OK);
    CHECK(selected == first);
    CHECK(running_count(&scheduler) == 1u);
    CHECK(mica_scheduler_schedule(&scheduler, &selected) == MICA_OK);
    CHECK(selected == second);
    CHECK(running_count(&scheduler) == 1u);

    CHECK(mica_scheduler_wake(&scheduler, third) == MICA_OK);
    CHECK(mica_scheduler_schedule(&scheduler, &selected) == MICA_OK);
    CHECK(selected == third);
    CHECK(mica_scheduler_exit(&scheduler, third, 7) == MICA_OK);
    CHECK(running_count(&scheduler) == 0u);
    CHECK(mica_scheduler_inspect(&scheduler, third, &info) == MICA_OK);
    CHECK(info.state == MICA_PROCESS_EXITED && info.exit_code == 7);
    CHECK(mica_scheduler_reap(&scheduler, third, &exit_code) == MICA_OK);
    CHECK(exit_code == 7);
    CHECK(mica_scheduler_get(&scheduler, third, &info) == MICA_ERR_NOT_FOUND);
    return true;
}

static bool test_vm_lifecycle(void)
{
    mica_vm_t vm;
    mica_address_space_t space;
    uint8_t value = 0xffu;
    size_t address = 2u * MICA_PAGE_SIZE + 13u;

    mica_vm_init(&vm);
    mica_vm_space_init(&space);
    vm.frames[0][13] = 0xa5u;
    CHECK(mica_vm_map(&vm, &space, 2u, true) == MICA_OK);
    CHECK(space.pages[2].frame == 0u);
    CHECK(mica_vm_read_u8(&vm, &space, address, &value) == MICA_OK);
    CHECK(value == 0u);
    CHECK(mica_vm_write_u8(&vm, &space, address, 0x42u) == MICA_OK);
    CHECK(mica_vm_read_u8(&vm, &space, address, &value) == MICA_OK);
    CHECK(value == 0x42u);

    CHECK(mica_vm_map(&vm, &space, 5u, false) == MICA_OK);
    CHECK(mica_vm_write_u8(&vm, &space, 5u * MICA_PAGE_SIZE, 1u) ==
          MICA_ERR_PERM);
    CHECK(mica_vm_unmap(&vm, &space, 2u) == MICA_OK);
    CHECK(mica_vm_read_u8(&vm, &space, address, &value) ==
          MICA_ERR_NOT_FOUND);
    return true;
}

static bool test_ramfs_lifecycle(void)
{
    mica_ramfs_t fs;
    mica_ramfs_t before;
    mica_ramfs_stat_t stat;
    const uint8_t payload[2] = {'O', 'S'};
    uint8_t output[8];
    size_t amount = 0u;

    mica_ramfs_init(&fs);
    CHECK(mica_ramfs_create(&fs, "note") == MICA_OK);
    CHECK(mica_ramfs_create(&fs, "note") == MICA_ERR_EXISTS);
    CHECK(mica_ramfs_write(&fs, "note", 2u, payload, sizeof(payload)) ==
          MICA_OK);
    (void)memset(output, 0xee, sizeof(output));
    CHECK(mica_ramfs_read(&fs, "note", 0u, output, sizeof(output), &amount) ==
          MICA_OK);
    CHECK(amount == 4u);
    CHECK(output[0] == 0u && output[1] == 0u);
    CHECK(output[2] == 'O' && output[3] == 'S');
    CHECK(output[4] == 0xeeu);
    CHECK(mica_ramfs_stat(&fs, "note", &stat) == MICA_OK);
    CHECK(stat.size == 4u);

    CHECK(mica_ramfs_write(&fs, "note", MICA_FILE_CAPACITY, NULL, 0u) ==
          MICA_OK);
    CHECK(mica_ramfs_stat(&fs, "note", &stat) == MICA_OK);
    CHECK(stat.size == 4u);
    before = fs;
    CHECK(mica_ramfs_write(&fs, "note", MICA_FILE_CAPACITY - 1u,
                           payload, sizeof(payload)) == MICA_ERR_RANGE);
    CHECK(ramfs_equal(&fs, &before));
    CHECK(mica_ramfs_unlink(&fs, "note") == MICA_OK);
    CHECK(mica_ramfs_stat(&fs, "note", &stat) == MICA_ERR_NOT_FOUND);
    return true;
}

int main(void)
{
    static const public_test_t tests[] = {
        {"initializers and constants", test_initializers_and_constants},
        {"scheduler validation", test_scheduler_validation},
        {"VM validation", test_vm_validation},
        {"RAMFS validation", test_ramfs_validation},
        {"scheduler lifecycle", test_scheduler_lifecycle},
        {"VM lifecycle", test_vm_lifecycle},
        {"RAMFS lifecycle", test_ramfs_lifecycle}
    };
    size_t index;
    size_t passed = 0u;
    size_t failed = 0u;

    for (index = 0u; index < sizeof(tests) / sizeof(tests[0]); ++index) {
        if (tests[index].function()) {
            (void)printf("[PASS] %s\n", tests[index].name);
            ++passed;
        } else {
            (void)printf("[FAIL] %s\n", tests[index].name);
            ++failed;
        }
    }
    (void)printf("\n%zu passed, %zu failed\n", passed, failed);
    return failed == 0u ? 0 : 1;
}
