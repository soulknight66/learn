#include "micaos.h"

#include <stdio.h>
#include <string.h>

static int failures;

static void check_condition(bool condition,
                            const char *expression,
                            int line)
{
    if (!condition) {
        (void)fprintf(stderr, "line %d: check failed: %s\n", line, expression);
        failures++;
    }
}

static void check_status(mica_status_t expected,
                         mica_status_t actual,
                         const char *expression,
                         int line)
{
    if (actual != expected) {
        (void)fprintf(stderr,
                      "line %d: %s returned %d, expected %d\n",
                      line,
                      expression,
                      (int)actual,
                      (int)expected);
        failures++;
    }
}

#define CHECK(expression) \
    check_condition((expression), #expression, __LINE__)
#define CHECK_STATUS(expected, expression) \
    check_status((expected), (expression), #expression, __LINE__)

static size_t running_processes(const mica_scheduler_t *scheduler)
{
    size_t i;
    size_t count = 0u;

    for (i = 0u; i < MICA_MAX_PROCESSES; i++) {
        if (scheduler->processes[i].state == MICA_PROCESS_RUNNING) {
            count++;
        }
    }
    return count;
}

static bool scheduler_equal(const mica_scheduler_t *left,
                            const mica_scheduler_t *right)
{
    size_t i;

    if (left->next_pid != right->next_pid || left->cursor != right->cursor) {
        return false;
    }
    for (i = 0u; i < MICA_MAX_PROCESSES; i++) {
        if (left->processes[i].pid != right->processes[i].pid ||
            left->processes[i].state != right->processes[i].state ||
            left->processes[i].exit_code != right->processes[i].exit_code) {
            return false;
        }
    }
    return true;
}

static bool vm_equal(const mica_vm_t *left, const mica_vm_t *right)
{
    size_t frame;
    size_t byte;

    for (frame = 0u; frame < MICA_PHYSICAL_FRAMES; frame++) {
        if (left->frame_used[frame] != right->frame_used[frame]) {
            return false;
        }
        for (byte = 0u; byte < MICA_PAGE_SIZE; byte++) {
            if (left->frames[frame][byte] != right->frames[frame][byte]) {
                return false;
            }
        }
    }
    return true;
}

static bool space_equal(const mica_address_space_t *left,
                        const mica_address_space_t *right)
{
    size_t page;

    for (page = 0u; page < MICA_VIRTUAL_PAGES; page++) {
        if (left->pages[page].mapped != right->pages[page].mapped ||
            left->pages[page].writable != right->pages[page].writable ||
            left->pages[page].frame != right->pages[page].frame) {
            return false;
        }
    }
    return true;
}

static bool ramfs_equal(const mica_ramfs_t *left, const mica_ramfs_t *right)
{
    size_t file;
    size_t byte;

    for (file = 0u; file < MICA_MAX_FILES; file++) {
        if (left->files[file].used != right->files[file].used ||
            left->files[file].size != right->files[file].size) {
            return false;
        }
        for (byte = 0u; byte <= MICA_NAME_MAX; byte++) {
            if (left->files[file].name[byte] != right->files[file].name[byte]) {
                return false;
            }
        }
        for (byte = 0u; byte < MICA_FILE_CAPACITY; byte++) {
            if (left->files[file].data[byte] != right->files[file].data[byte]) {
                return false;
            }
        }
    }
    return true;
}

static void test_constants_and_statuses(void)
{
    CHECK(MICA_MAX_PROCESSES == 8u);
    CHECK(MICA_VIRTUAL_PAGES == 16u);
    CHECK(MICA_PHYSICAL_FRAMES == 8u);
    CHECK(MICA_PAGE_SIZE == 64u);
    CHECK(MICA_MAX_FILES == 8u);
    CHECK(MICA_NAME_MAX == 15u);
    CHECK(MICA_FILE_CAPACITY == 128u);
    CHECK(MICA_OK == 0);
    CHECK(MICA_ERR_ARG == -1);
    CHECK(MICA_ERR_FULL == -2);
    CHECK(MICA_ERR_NOT_FOUND == -3);
    CHECK(MICA_ERR_STATE == -4);
    CHECK(MICA_ERR_EXISTS == -5);
    CHECK(MICA_ERR_RANGE == -6);
    CHECK(MICA_ERR_PERM == -7);
}

static void test_scheduler_round_robin_and_lifecycle(void)
{
    mica_scheduler_t scheduler;
    mica_pid_t a;
    mica_pid_t b;
    mica_pid_t c;
    mica_pid_t selected;
    mica_process_info_t info;
    int exit_code;
    size_t i;

    (void)memset(&scheduler, 0xa5, sizeof(scheduler));
    mica_scheduler_init(&scheduler);
    CHECK(scheduler.next_pid == 1u);
    CHECK(scheduler.cursor == MICA_MAX_PROCESSES - 1u);
    CHECK(running_processes(&scheduler) == 0u);
    for (i = 0u; i < MICA_MAX_PROCESSES; i++) {
        CHECK(scheduler.processes[i].pid == 0u);
        CHECK(scheduler.processes[i].state == MICA_PROCESS_UNUSED);
        CHECK(scheduler.processes[i].exit_code == 0);
    }

    selected = 777u;
    CHECK_STATUS(MICA_ERR_NOT_FOUND,
                 mica_scheduler_schedule(&scheduler, &selected));
    CHECK(selected == 777u);

    CHECK_STATUS(MICA_OK, mica_scheduler_spawn(&scheduler, &a));
    CHECK_STATUS(MICA_OK, mica_scheduler_spawn(&scheduler, &b));
    CHECK_STATUS(MICA_OK, mica_scheduler_spawn(&scheduler, &c));
    CHECK(a == 1u);
    CHECK(b == 2u);
    CHECK(c == 3u);

    CHECK_STATUS(MICA_OK, mica_scheduler_schedule(&scheduler, &selected));
    CHECK(selected == a);
    CHECK(running_processes(&scheduler) == 1u);
    CHECK_STATUS(MICA_OK, mica_scheduler_schedule(&scheduler, &selected));
    CHECK(selected == b);
    CHECK(running_processes(&scheduler) == 1u);
    CHECK_STATUS(MICA_OK, mica_scheduler_schedule(&scheduler, &selected));
    CHECK(selected == c);
    CHECK_STATUS(MICA_OK, mica_scheduler_schedule(&scheduler, &selected));
    CHECK(selected == a);

    /* A READY process can be blocked without disturbing the running one. */
    CHECK_STATUS(MICA_OK, mica_scheduler_block(&scheduler, b));
    CHECK(running_processes(&scheduler) == 1u);
    CHECK_STATUS(MICA_OK, mica_scheduler_schedule(&scheduler, &selected));
    CHECK(selected == c);
    CHECK_STATUS(MICA_OK, mica_scheduler_schedule(&scheduler, &selected));
    CHECK(selected == a);
    CHECK_STATUS(MICA_OK, mica_scheduler_wake(&scheduler, b));
    CHECK_STATUS(MICA_OK, mica_scheduler_schedule(&scheduler, &selected));
    CHECK(selected == b);

    /* Blocking RUNNING leaves the CPU idle until schedule is called. */
    CHECK_STATUS(MICA_OK, mica_scheduler_block(&scheduler, b));
    CHECK(running_processes(&scheduler) == 0u);
    CHECK_STATUS(MICA_ERR_STATE, mica_scheduler_block(&scheduler, b));
    CHECK_STATUS(MICA_OK, mica_scheduler_schedule(&scheduler, &selected));
    CHECK(selected == c);

    /* Exit is valid for BLOCKED, READY, and RUNNING processes. */
    CHECK_STATUS(MICA_OK, mica_scheduler_exit(&scheduler, b, 23));
    CHECK_STATUS(MICA_OK, mica_scheduler_get(&scheduler, b, &info));
    CHECK(info.pid == b);
    CHECK(info.state == MICA_PROCESS_EXITED);
    CHECK(info.exit_code == 23);
    CHECK_STATUS(MICA_OK, mica_scheduler_exit(&scheduler, a, 11));
    CHECK_STATUS(MICA_OK, mica_scheduler_exit(&scheduler, c, 37));
    CHECK(running_processes(&scheduler) == 0u);
    CHECK_STATUS(MICA_ERR_STATE, mica_scheduler_exit(&scheduler, c, 38));
    CHECK_STATUS(MICA_ERR_STATE, mica_scheduler_wake(&scheduler, c));

    exit_code = -1;
    CHECK_STATUS(MICA_OK, mica_scheduler_reap(&scheduler, b, &exit_code));
    CHECK(exit_code == 23);
    CHECK_STATUS(MICA_ERR_NOT_FOUND,
                 mica_scheduler_inspect(&scheduler, b, &info));
    CHECK_STATUS(MICA_ERR_NOT_FOUND,
                 mica_scheduler_reap(&scheduler, b, &exit_code));
    CHECK_STATUS(MICA_OK, mica_scheduler_spawn(&scheduler, &selected));
    CHECK(selected == 4u);
    CHECK(selected != b);
}

static void test_scheduler_capacity_arguments_and_integrity(void)
{
    mica_scheduler_t scheduler;
    mica_scheduler_t before;
    mica_pid_t pids[MICA_MAX_PROCESSES];
    mica_pid_t output;
    mica_process_info_t info;
    mica_process_info_t original_info;
    int exit_code;
    size_t i;

    mica_scheduler_init(NULL);
    mica_scheduler_init(&scheduler);
    output = 91u;
    CHECK_STATUS(MICA_ERR_ARG, mica_scheduler_spawn(NULL, &output));
    CHECK_STATUS(MICA_ERR_ARG, mica_scheduler_spawn(&scheduler, NULL));
    CHECK_STATUS(MICA_ERR_ARG, mica_scheduler_schedule(NULL, &output));
    CHECK_STATUS(MICA_ERR_ARG, mica_scheduler_schedule(&scheduler, NULL));
    CHECK_STATUS(MICA_ERR_ARG, mica_scheduler_block(NULL, 1u));
    CHECK_STATUS(MICA_ERR_ARG, mica_scheduler_block(&scheduler, 0u));
    CHECK_STATUS(MICA_ERR_ARG, mica_scheduler_wake(&scheduler, 0u));
    CHECK_STATUS(MICA_ERR_ARG, mica_scheduler_exit(&scheduler, 0u, 0));
    CHECK_STATUS(MICA_ERR_ARG, mica_scheduler_reap(&scheduler, 0u, &exit_code));
    CHECK_STATUS(MICA_ERR_ARG, mica_scheduler_reap(&scheduler, 1u, NULL));
    CHECK_STATUS(MICA_ERR_ARG, mica_scheduler_get(&scheduler, 0u, &info));
    CHECK_STATUS(MICA_ERR_ARG, mica_scheduler_get(&scheduler, 1u, NULL));
    CHECK_STATUS(MICA_ERR_NOT_FOUND, mica_scheduler_block(&scheduler, 99u));
    CHECK_STATUS(MICA_ERR_NOT_FOUND, mica_scheduler_wake(&scheduler, 99u));
    CHECK_STATUS(MICA_ERR_NOT_FOUND, mica_scheduler_exit(&scheduler, 99u, 0));

    for (i = 0u; i < MICA_MAX_PROCESSES; i++) {
        CHECK_STATUS(MICA_OK, mica_scheduler_spawn(&scheduler, &pids[i]));
        CHECK(pids[i] == (mica_pid_t)(i + 1u));
    }
    before = scheduler;
    output = 999u;
    CHECK_STATUS(MICA_ERR_FULL, mica_scheduler_spawn(&scheduler, &output));
    CHECK(output == 999u);
    CHECK(scheduler_equal(&scheduler, &before));

    /* EXITED records still consume capacity until reaped. */
    CHECK_STATUS(MICA_OK, mica_scheduler_exit(&scheduler, pids[4], 52));
    CHECK_STATUS(MICA_ERR_FULL, mica_scheduler_spawn(&scheduler, &output));
    exit_code = -1;
    CHECK_STATUS(MICA_OK,
                 mica_scheduler_reap(&scheduler, pids[4], &exit_code));
    CHECK(exit_code == 52);
    CHECK_STATUS(MICA_OK, mica_scheduler_spawn(&scheduler, &output));
    CHECK(output == 9u);

    /* Failed queries preserve caller-owned outputs. */
    original_info.pid = 700u;
    original_info.state = MICA_PROCESS_BLOCKED;
    original_info.exit_code = 701;
    info = original_info;
    CHECK_STATUS(MICA_ERR_NOT_FOUND,
                 mica_scheduler_get(&scheduler, 700u, &info));
    CHECK(info.pid == original_info.pid);
    CHECK(info.state == original_info.state);
    CHECK(info.exit_code == original_info.exit_code);
    exit_code = 444;
    CHECK_STATUS(MICA_ERR_STATE,
                 mica_scheduler_reap(&scheduler, pids[0], &exit_code));
    CHECK(exit_code == 444);

    /* PID selection skips live identities even if next_pid wraps or is stale. */
    mica_scheduler_init(&scheduler);
    CHECK_STATUS(MICA_OK, mica_scheduler_spawn(&scheduler, &pids[0]));
    scheduler.next_pid = pids[0];
    CHECK_STATUS(MICA_OK, mica_scheduler_spawn(&scheduler, &pids[1]));
    CHECK(pids[1] == 2u);
    scheduler.next_pid = 0u;
    CHECK_STATUS(MICA_OK, mica_scheduler_spawn(&scheduler, &pids[2]));
    CHECK(pids[2] == 3u);

    /* Public-state corruption is detected without a partial scheduling edit. */
    scheduler.processes[0].state = MICA_PROCESS_RUNNING;
    scheduler.processes[1].state = MICA_PROCESS_RUNNING;
    before = scheduler;
    output = 123u;
    CHECK_STATUS(MICA_ERR_STATE,
                 mica_scheduler_schedule(&scheduler, &output));
    CHECK(output == 123u);
    CHECK(scheduler_equal(&scheduler, &before));
}

static void test_vm_mapping_permissions_and_zeroing(void)
{
    mica_vm_t vm;
    mica_vm_t before;
    mica_address_space_t space;
    mica_address_space_t arbitrary_space;
    uint8_t value;
    size_t frame;
    size_t offset;

    (void)memset(&vm, 0xa5, sizeof(vm));
    (void)memset(&space, 0xa5, sizeof(space));
    mica_vm_init(&vm);
    mica_vm_space_init(&space);
    mica_vm_init(NULL);
    mica_vm_space_init(NULL);
    for (frame = 0u; frame < MICA_PHYSICAL_FRAMES; frame++) {
        CHECK(!vm.frame_used[frame]);
        for (offset = 0u; offset < MICA_PAGE_SIZE; offset++) {
            CHECK(vm.frames[frame][offset] == 0u);
        }
    }
    for (offset = 0u; offset < MICA_VIRTUAL_PAGES; offset++) {
        CHECK(!space.pages[offset].mapped);
        CHECK(!space.pages[offset].writable);
        CHECK(space.pages[offset].frame == 0u);
    }

    CHECK_STATUS(MICA_ERR_ARG, mica_vm_map(NULL, &space, 0u, true));
    CHECK_STATUS(MICA_ERR_ARG, mica_vm_map(&vm, NULL, 0u, true));
    CHECK_STATUS(MICA_ERR_RANGE,
                 mica_vm_map(&vm, &space, MICA_VIRTUAL_PAGES, true));
    CHECK_STATUS(MICA_OK, mica_vm_map(&vm, &space, 2u, true));
    CHECK(space.pages[2].mapped);
    CHECK(space.pages[2].writable);
    CHECK(space.pages[2].frame == 0u);
    CHECK_STATUS(MICA_ERR_EXISTS, mica_vm_map(&vm, &space, 2u, false));

    value = 0xffu;
    CHECK_STATUS(MICA_OK,
                 mica_vm_read_u8(&vm, &space, 2u * MICA_PAGE_SIZE, &value));
    CHECK(value == 0u);
    CHECK_STATUS(MICA_OK,
                 mica_vm_write_u8(&vm, &space, 2u * MICA_PAGE_SIZE, 0x31u));
    CHECK_STATUS(MICA_OK,
                 mica_vm_write_u8(&vm,
                                  &space,
                                  3u * MICA_PAGE_SIZE - 1u,
                                  0x7eu));
    CHECK_STATUS(MICA_OK,
                 mica_vm_read_u8(&vm, &space, 2u * MICA_PAGE_SIZE, &value));
    CHECK(value == 0x31u);
    CHECK_STATUS(MICA_OK,
                 mica_vm_read_u8(&vm,
                                 &space,
                                 3u * MICA_PAGE_SIZE - 1u,
                                 &value));
    CHECK(value == 0x7eu);

    CHECK_STATUS(MICA_OK, mica_vm_map(&vm, &space, 3u, false));
    CHECK(space.pages[3].frame == 1u);
    before = vm;
    CHECK_STATUS(MICA_ERR_PERM,
                 mica_vm_write_u8(&vm, &space, 3u * MICA_PAGE_SIZE, 0x55u));
    CHECK(vm_equal(&vm, &before));
    value = 0xaau;
    CHECK_STATUS(MICA_OK,
                 mica_vm_read_u8(&vm, &space, 3u * MICA_PAGE_SIZE, &value));
    CHECK(value == 0u);

    value = 0x44u;
    CHECK_STATUS(MICA_ERR_NOT_FOUND,
                 mica_vm_read_u8(&vm, &space, 0u, &value));
    CHECK(value == 0x44u);
    CHECK_STATUS(MICA_ERR_RANGE,
                 mica_vm_read_u8(&vm,
                                 &space,
                                 MICA_VIRTUAL_PAGES * MICA_PAGE_SIZE,
                                 &value));
    CHECK(value == 0x44u);
    CHECK_STATUS(MICA_ERR_NOT_FOUND,
                 mica_vm_write_u8(&vm, &space, 0u, 1u));
    CHECK_STATUS(MICA_ERR_RANGE,
                 mica_vm_write_u8(&vm,
                                  &space,
                                  MICA_VIRTUAL_PAGES * MICA_PAGE_SIZE,
                                  1u));

    CHECK_STATUS(MICA_OK, mica_vm_unmap(&vm, &space, 2u));
    CHECK(!space.pages[2].mapped);
    CHECK(!vm.frame_used[0]);
    CHECK_STATUS(MICA_ERR_NOT_FOUND, mica_vm_unmap(&vm, &space, 2u));
    CHECK_STATUS(MICA_OK, mica_vm_map(&vm, &space, 4u, true));
    CHECK(space.pages[4].frame == 0u);
    value = 0xffu;
    CHECK_STATUS(MICA_OK,
                 mica_vm_read_u8(&vm, &space, 4u * MICA_PAGE_SIZE, &value));
    CHECK(value == 0u);
    CHECK_STATUS(MICA_OK,
                 mica_vm_read_u8(&vm,
                                 &space,
                                 5u * MICA_PAGE_SIZE - 1u,
                                 &value));
    CHECK(value == 0u);

    CHECK_STATUS(MICA_ERR_ARG, mica_vm_unmap(NULL, &space, 4u));
    CHECK_STATUS(MICA_ERR_ARG, mica_vm_unmap(&vm, NULL, 4u));
    CHECK_STATUS(MICA_ERR_RANGE,
                 mica_vm_unmap(&vm, &space, MICA_VIRTUAL_PAGES));
    CHECK_STATUS(MICA_ERR_ARG, mica_vm_read_u8(NULL, &space, 0u, &value));
    CHECK_STATUS(MICA_ERR_ARG, mica_vm_read_u8(&vm, NULL, 0u, &value));
    CHECK_STATUS(MICA_ERR_ARG, mica_vm_read_u8(&vm, &space, 0u, NULL));
    CHECK_STATUS(MICA_ERR_ARG, mica_vm_write_u8(NULL, &space, 0u, 0u));
    CHECK_STATUS(MICA_ERR_ARG, mica_vm_write_u8(&vm, NULL, 0u, 0u));

    (void)memset(&arbitrary_space, 0xa5, sizeof(arbitrary_space));
    mica_vm_space_init(&arbitrary_space);
    for (offset = 0u; offset < MICA_VIRTUAL_PAGES; offset++) {
        CHECK(!arbitrary_space.pages[offset].mapped);
        CHECK(!arbitrary_space.pages[offset].writable);
        CHECK(arbitrary_space.pages[offset].frame == 0u);
    }
}

static void test_vm_capacity_isolation_and_corruption(void)
{
    mica_vm_t vm;
    mica_vm_t vm_before;
    mica_address_space_t left;
    mica_address_space_t right;
    mica_address_space_t space_before;
    uint8_t value;
    size_t page;

    mica_vm_init(&vm);
    mica_vm_space_init(&left);
    mica_vm_space_init(&right);
    for (page = 0u; page < MICA_PHYSICAL_FRAMES; page++) {
        mica_address_space_t *owner = page < 4u ? &left : &right;
        size_t virtual_page = page < 4u ? page : page - 4u;

        CHECK_STATUS(MICA_OK,
                     mica_vm_map(&vm, owner, virtual_page, true));
        CHECK(owner->pages[virtual_page].frame == (uint8_t)page);
        CHECK_STATUS(MICA_OK,
                     mica_vm_write_u8(&vm,
                                      owner,
                                      virtual_page * MICA_PAGE_SIZE,
                                      (uint8_t)(page + 1u)));
    }
    vm_before = vm;
    space_before = left;
    CHECK_STATUS(MICA_ERR_FULL, mica_vm_map(&vm, &left, 8u, true));
    CHECK(vm_equal(&vm, &vm_before));
    CHECK(space_equal(&left, &space_before));

    for (page = 0u; page < 4u; page++) {
        value = 0u;
        CHECK_STATUS(MICA_OK,
                     mica_vm_read_u8(&vm,
                                     &left,
                                     page * MICA_PAGE_SIZE,
                                     &value));
        CHECK(value == (uint8_t)(page + 1u));
        value = 0u;
        CHECK_STATUS(MICA_OK,
                     mica_vm_read_u8(&vm,
                                     &right,
                                     page * MICA_PAGE_SIZE,
                                     &value));
        CHECK(value == (uint8_t)(page + 5u));
    }

    CHECK_STATUS(MICA_OK, mica_vm_unmap(&vm, &left, 1u));
    CHECK_STATUS(MICA_OK, mica_vm_map(&vm, &right, 9u, true));
    CHECK(right.pages[9].frame == 1u);
    value = 0xffu;
    CHECK_STATUS(MICA_OK,
                 mica_vm_read_u8(&vm, &right, 9u * MICA_PAGE_SIZE, &value));
    CHECK(value == 0u);

    /* An impossible frame index/accounting mismatch is a state error. */
    right.pages[9].frame = (uint8_t)MICA_PHYSICAL_FRAMES;
    value = 0x66u;
    CHECK_STATUS(MICA_ERR_STATE,
                 mica_vm_read_u8(&vm, &right, 9u * MICA_PAGE_SIZE, &value));
    CHECK(value == 0x66u);
    vm_before = vm;
    space_before = right;
    CHECK_STATUS(MICA_ERR_STATE, mica_vm_unmap(&vm, &right, 9u));
    CHECK(vm_equal(&vm, &vm_before));
    CHECK(space_equal(&right, &space_before));
    right.pages[9].frame = 1u;
    vm.frame_used[1] = false;
    CHECK_STATUS(MICA_ERR_STATE,
                 mica_vm_write_u8(&vm, &right, 9u * MICA_PAGE_SIZE, 1u));
}

static void test_ramfs_names_and_capacity(void)
{
    mica_ramfs_t fs;
    mica_ramfs_t before;
    mica_ramfs_stat_t stat;
    const char *names[MICA_MAX_FILES + 1u] = {
        "f0", "f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8"
    };
    char overlong[MICA_NAME_MAX + 2u] = "abcdefghijklmnop";
    size_t i;

    (void)memset(&fs, 0xa5, sizeof(fs));
    mica_ramfs_init(&fs);
    mica_ramfs_init(NULL);
    for (i = 0u; i < MICA_MAX_FILES; i++) {
        CHECK(!fs.files[i].used);
        CHECK(fs.files[i].name[0] == '\0');
        CHECK(fs.files[i].size == 0u);
        CHECK(fs.files[i].data[0] == 0u);
        CHECK(fs.files[i].data[MICA_FILE_CAPACITY - 1u] == 0u);
    }

    CHECK_STATUS(MICA_ERR_ARG, mica_ramfs_create(NULL, "x"));
    CHECK_STATUS(MICA_ERR_ARG, mica_ramfs_create(&fs, NULL));
    CHECK_STATUS(MICA_ERR_ARG, mica_ramfs_create(&fs, ""));
    CHECK_STATUS(MICA_ERR_ARG, mica_ramfs_create(&fs, "."));
    CHECK_STATUS(MICA_ERR_ARG, mica_ramfs_create(&fs, ".."));
    CHECK_STATUS(MICA_ERR_ARG, mica_ramfs_create(&fs, "a/b"));
    CHECK_STATUS(MICA_ERR_ARG, mica_ramfs_create(&fs, overlong));
    CHECK_STATUS(MICA_OK, mica_ramfs_create(&fs, "abcdefghijklmno"));
    CHECK_STATUS(MICA_ERR_EXISTS,
                 mica_ramfs_create(&fs, "abcdefghijklmno"));
    CHECK_STATUS(MICA_OK, mica_ramfs_unlink(&fs, "abcdefghijklmno"));

    for (i = 0u; i < MICA_MAX_FILES; i++) {
        CHECK_STATUS(MICA_OK, mica_ramfs_create(&fs, names[i]));
    }
    before = fs;
    CHECK_STATUS(MICA_ERR_FULL,
                 mica_ramfs_create(&fs, names[MICA_MAX_FILES]));
    CHECK(ramfs_equal(&fs, &before));
    CHECK_STATUS(MICA_ERR_EXISTS, mica_ramfs_create(&fs, names[0]));
    CHECK_STATUS(MICA_OK, mica_ramfs_unlink(&fs, names[3]));
    CHECK_STATUS(MICA_ERR_NOT_FOUND, mica_ramfs_unlink(&fs, names[3]));
    stat.size = 77u;
    CHECK_STATUS(MICA_ERR_NOT_FOUND,
                 mica_ramfs_stat(&fs, names[3], &stat));
    CHECK(stat.size == 77u);
    CHECK_STATUS(MICA_OK, mica_ramfs_create(&fs, "new"));
    CHECK_STATUS(MICA_OK, mica_ramfs_stat(&fs, "new", &stat));
    CHECK(stat.size == 0u);
    CHECK(fs.files[3].used);
    CHECK(strcmp(fs.files[3].name, "new") == 0);
    for (i = 0u; i < MICA_FILE_CAPACITY; i++) {
        CHECK(fs.files[3].data[i] == 0u);
    }

    CHECK_STATUS(MICA_ERR_ARG, mica_ramfs_unlink(&fs, "."));
    CHECK_STATUS(MICA_ERR_ARG, mica_ramfs_stat(&fs, "..", &stat));
    CHECK_STATUS(MICA_ERR_ARG, mica_ramfs_stat(NULL, "new", &stat));
    CHECK_STATUS(MICA_ERR_ARG, mica_ramfs_stat(&fs, "new", NULL));
}

static void test_ramfs_io_and_atomicity(void)
{
    mica_ramfs_t fs;
    mica_ramfs_t before;
    mica_ramfs_stat_t stat;
    uint8_t hello[5] = { 'h', 'e', 'l', 'l', 'o' };
    uint8_t replacement[2] = { 'A', 'B' };
    uint8_t one = (uint8_t)'X';
    uint8_t output[MICA_FILE_CAPACITY];
    uint8_t output_before[MICA_FILE_CAPACITY];
    size_t amount;

    mica_ramfs_init(&fs);
    CHECK_STATUS(MICA_OK, mica_ramfs_create(&fs, "data"));
    CHECK_STATUS(MICA_OK,
                 mica_ramfs_write(&fs, "data", 0u, hello, sizeof(hello)));
    CHECK_STATUS(MICA_OK, mica_ramfs_stat(&fs, "data", &stat));
    CHECK(stat.size == sizeof(hello));

    (void)memset(output, 0xcc, sizeof(output));
    amount = 999u;
    CHECK_STATUS(MICA_OK,
                 mica_ramfs_read(&fs, "data", 0u, output, 3u, &amount));
    CHECK(amount == 3u);
    CHECK(output[0] == (uint8_t)'h');
    CHECK(output[1] == (uint8_t)'e');
    CHECK(output[2] == (uint8_t)'l');
    CHECK(output[3] == 0xccu);

    amount = 999u;
    CHECK_STATUS(MICA_OK,
                 mica_ramfs_read(&fs,
                                 "data",
                                 sizeof(hello),
                                 NULL,
                                 0u,
                                 &amount));
    CHECK(amount == 0u);
    amount = 999u;
    CHECK_STATUS(MICA_OK,
                 mica_ramfs_read(&fs, "data", 2u, NULL, 0u, &amount));
    CHECK(amount == 0u);

    /* Extending beyond EOF creates a deterministic zero-filled gap. */
    CHECK_STATUS(MICA_OK, mica_ramfs_write(&fs, "data", 7u, &one, 1u));
    CHECK_STATUS(MICA_OK, mica_ramfs_stat(&fs, "data", &stat));
    CHECK(stat.size == 8u);
    amount = 0u;
    CHECK_STATUS(MICA_OK,
                 mica_ramfs_read(&fs, "data", 0u, output, 8u, &amount));
    CHECK(amount == 8u);
    CHECK(memcmp(output, hello, sizeof(hello)) == 0);
    CHECK(output[5] == 0u);
    CHECK(output[6] == 0u);
    CHECK(output[7] == (uint8_t)'X');

    /* An overwrite retains the suffix and does not shrink the file. */
    CHECK_STATUS(MICA_OK,
                 mica_ramfs_write(&fs,
                                  "data",
                                  1u,
                                  replacement,
                                  sizeof(replacement)));
    CHECK_STATUS(MICA_OK, mica_ramfs_stat(&fs, "data", &stat));
    CHECK(stat.size == 8u);
    amount = 0u;
    CHECK_STATUS(MICA_OK,
                 mica_ramfs_read(&fs, "data", 0u, output, 8u, &amount));
    CHECK(output[0] == (uint8_t)'h');
    CHECK(output[1] == (uint8_t)'A');
    CHECK(output[2] == (uint8_t)'B');
    CHECK(output[3] == (uint8_t)'l');
    CHECK(output[7] == (uint8_t)'X');

    before = fs;
    CHECK_STATUS(MICA_OK,
                 mica_ramfs_write(&fs,
                                  "data",
                                  MICA_FILE_CAPACITY,
                                  NULL,
                                  0u));
    CHECK(ramfs_equal(&fs, &before));
    CHECK_STATUS(MICA_ERR_RANGE,
                 mica_ramfs_write(&fs,
                                  "data",
                                  MICA_FILE_CAPACITY,
                                  &one,
                                  1u));
    CHECK(ramfs_equal(&fs, &before));
    CHECK_STATUS(MICA_ERR_RANGE,
                 mica_ramfs_write(&fs,
                                  "data",
                                  MICA_FILE_CAPACITY - 1u,
                                  hello,
                                  2u));
    CHECK(ramfs_equal(&fs, &before));
    CHECK_STATUS(MICA_ERR_RANGE,
                 mica_ramfs_write(&fs,
                                  "data",
                                  MICA_FILE_CAPACITY + 1u,
                                  NULL,
                                  0u));
    CHECK(ramfs_equal(&fs, &before));
    CHECK_STATUS(MICA_ERR_ARG,
                 mica_ramfs_write(&fs, "data", 0u, NULL, 1u));
    CHECK(ramfs_equal(&fs, &before));

    CHECK_STATUS(MICA_OK,
                 mica_ramfs_write(&fs,
                                  "data",
                                  MICA_FILE_CAPACITY - 1u,
                                  &one,
                                  1u));
    CHECK_STATUS(MICA_OK, mica_ramfs_stat(&fs, "data", &stat));
    CHECK(stat.size == MICA_FILE_CAPACITY);
    amount = 0u;
    CHECK_STATUS(MICA_OK,
                 mica_ramfs_read(&fs,
                                 "data",
                                 MICA_FILE_CAPACITY - 1u,
                                 output,
                                 sizeof(output),
                                 &amount));
    CHECK(amount == 1u);
    CHECK(output[0] == (uint8_t)'X');

    (void)memset(output, 0x5a, sizeof(output));
    (void)memcpy(output_before, output, sizeof(output));
    amount = 314u;
    CHECK_STATUS(MICA_ERR_RANGE,
                 mica_ramfs_read(&fs,
                                 "data",
                                 MICA_FILE_CAPACITY + 1u,
                                 output,
                                 sizeof(output),
                                 &amount));
    CHECK(amount == 314u);
    CHECK(memcmp(output, output_before, sizeof(output)) == 0);
    CHECK_STATUS(MICA_ERR_ARG,
                 mica_ramfs_read(&fs, "data", 0u, NULL, 1u, &amount));
    CHECK(amount == 314u);
    CHECK_STATUS(MICA_ERR_ARG,
                 mica_ramfs_read(&fs, "data", 0u, output, 1u, NULL));
    CHECK_STATUS(MICA_ERR_NOT_FOUND,
                 mica_ramfs_read(&fs, "missing", 0u, output, 1u, &amount));
    CHECK(amount == 314u);
    CHECK_STATUS(MICA_ERR_ARG,
                 mica_ramfs_read(&fs, ".", 0u, output, 1u, &amount));
    CHECK(amount == 314u);

    stat.size = 222u;
    CHECK_STATUS(MICA_ERR_NOT_FOUND,
                 mica_ramfs_stat(&fs, "missing", &stat));
    CHECK(stat.size == 222u);
    CHECK_STATUS(MICA_ERR_NOT_FOUND,
                 mica_ramfs_write(&fs, "missing", 0u, &one, 1u));

    /* Input may alias the file: staging prevents overlap surprises. */
    mica_ramfs_init(&fs);
    CHECK_STATUS(MICA_OK, mica_ramfs_create(&fs, "alias"));
    CHECK_STATUS(MICA_OK,
                 mica_ramfs_write(&fs, "alias", 0u, hello, sizeof(hello)));
    CHECK_STATUS(MICA_OK,
                 mica_ramfs_write(&fs,
                                  "alias",
                                  2u,
                                  fs.files[0].data,
                                  4u));
    amount = 0u;
    CHECK_STATUS(MICA_OK,
                 mica_ramfs_read(&fs, "alias", 0u, output, 6u, &amount));
    CHECK(amount == 6u);
    CHECK(output[0] == (uint8_t)'h');
    CHECK(output[1] == (uint8_t)'e');
    CHECK(output[2] == (uint8_t)'h');
    CHECK(output[3] == (uint8_t)'e');
    CHECK(output[4] == (uint8_t)'l');
    CHECK(output[5] == (uint8_t)'l');

    CHECK_STATUS(MICA_OK, mica_ramfs_create(&fs, "Case"));
    CHECK_STATUS(MICA_OK, mica_ramfs_create(&fs, "case"));
    CHECK_STATUS(MICA_ERR_NOT_FOUND,
                 mica_ramfs_stat(&fs, "CASE", &stat));

    /* Corrupt public metadata is rejected before an implementation writes. */
    fs.files[0].size = MICA_FILE_CAPACITY + 1u;
    before = fs;
    CHECK_STATUS(MICA_ERR_STATE,
                 mica_ramfs_write(&fs, "alias", 0u, &one, 1u));
    CHECK(ramfs_equal(&fs, &before));
    amount = 9u;
    CHECK_STATUS(MICA_ERR_STATE,
                 mica_ramfs_read(&fs, "alias", 0u, output, 1u, &amount));
    CHECK(amount == 9u);
    stat.size = 9u;
    CHECK_STATUS(MICA_ERR_STATE, mica_ramfs_stat(&fs, "alias", &stat));
    CHECK(stat.size == 9u);

}

int main(void)
{
    test_constants_and_statuses();
    test_scheduler_round_robin_and_lifecycle();
    test_scheduler_capacity_arguments_and_integrity();
    test_vm_mapping_permissions_and_zeroing();
    test_vm_capacity_isolation_and_corruption();
    test_ramfs_names_and_capacity();
    test_ramfs_io_and_atomicity();

    if (failures != 0) {
        (void)fprintf(stderr, "reference tests: FAIL (%d checks)\n", failures);
        return 1;
    }
    (void)puts("reference tests: PASS");
    return 0;
}
