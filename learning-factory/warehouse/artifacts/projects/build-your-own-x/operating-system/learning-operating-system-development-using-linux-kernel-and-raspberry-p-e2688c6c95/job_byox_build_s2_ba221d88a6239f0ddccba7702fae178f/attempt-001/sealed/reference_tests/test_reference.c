#include "minios.h"

#include <stdint.h>
#include <stdio.h>
#include <string.h>

#define CHECK(condition)                                                       \
    do {                                                                       \
        if (!(condition)) {                                                    \
            (void)printf("FAIL %s:%d: %s\n", __func__, __LINE__, #condition); \
            return 0;                                                          \
        }                                                                      \
    } while (0)

static int test_process_initialization_and_errors(void)
{
    proc_table_t table;
    proc_table_t snapshot;
    const process_t *process = (const process_t *)(uintptr_t)1u;
    uint32_t pid = 77u;
    uint32_t selected = 77u;
    size_t i;

    (void)memset(&table, 0xa5, sizeof(table));
    proc_table_init(NULL);
    proc_table_init(&table);
    CHECK(table.next_pid == 1u && table.current_slot == -1);
    for (i = 0; i < MINIOS_MAX_PROCESSES; ++i) {
        CHECK(table.slots[i].state == PROC_UNUSED);
        CHECK(table.slots[i].pid == 0u);
        CHECK(table.slots[i].parent_pid == 0u);
        CHECK(table.slots[i].entry_point == (uintptr_t)0);
        CHECK(table.slots[i].exit_code == 0);
    }

    CHECK(proc_get(NULL, 1u, &process) == OS_ERR_INVALID);
    CHECK(process == NULL);
    CHECK(proc_get(&table, 0u, &process) == OS_ERR_NOT_FOUND);
    CHECK(process == NULL);
    CHECK(proc_get(&table, 1u, NULL) == OS_ERR_INVALID);
    CHECK(proc_schedule(&table, &selected) == OS_ERR_NOT_FOUND);
    CHECK(selected == 0u && table.current_slot == -1);

    snapshot = table;
    CHECK(proc_spawn(&table, 0u, (uintptr_t)1u, NULL) == OS_ERR_INVALID);
    CHECK(memcmp(&table, &snapshot, sizeof(table)) == 0);
    CHECK(proc_spawn(&table, 99u, (uintptr_t)1u, &pid) == OS_ERR_NOT_FOUND);
    CHECK(pid == 0u && memcmp(&table, &snapshot, sizeof(table)) == 0);
    return 1;
}

static int test_process_lifecycle(void)
{
    proc_table_t table;
    const process_t *process;
    uint32_t first;
    uint32_t second;
    uint32_t third;
    uint32_t selected;
    int32_t exit_code;

    proc_table_init(&table);
    CHECK(proc_spawn(&table, 0u, (uintptr_t)0x10u, &first) == OS_OK);
    CHECK(proc_spawn(&table, first, (uintptr_t)0x20u, &second) == OS_OK);
    CHECK(proc_spawn(&table, first, (uintptr_t)0x30u, &third) == OS_OK);
    CHECK(first == 1u && second == 2u && third == 3u);
    CHECK(proc_get(&table, second, &process) == OS_OK);
    CHECK(process->parent_pid == first && process->entry_point == (uintptr_t)0x20u);

    CHECK(proc_block(&table, first) == OS_ERR_STATE);
    CHECK(proc_schedule(&table, &selected) == OS_OK && selected == first);
    CHECK(proc_schedule(&table, &selected) == OS_OK && selected == second);
    CHECK(proc_block(&table, first) == OS_ERR_STATE);
    CHECK(proc_block(&table, second) == OS_OK && table.current_slot == -1);
    CHECK(proc_wake(&table, first) == OS_ERR_STATE);
    CHECK(proc_schedule(&table, &selected) == OS_OK && selected == first);
    CHECK(proc_wake(&table, second) == OS_OK);
    CHECK(proc_schedule(&table, &selected) == OS_OK && selected == second);

    CHECK(proc_exit(&table, second, -123) == OS_OK);
    CHECK(table.current_slot == -1);
    CHECK(proc_get(&table, second, &process) == OS_OK);
    CHECK(process->state == PROC_ZOMBIE && process->exit_code == -123);
    CHECK(proc_spawn(&table, second, (uintptr_t)0, &selected) == OS_ERR_STATE);
    CHECK(selected == 0u);
    CHECK(proc_wake(&table, second) == OS_ERR_STATE);
    CHECK(proc_exit(&table, second, 0) == OS_ERR_STATE);
    CHECK(proc_reap(&table, second, &exit_code) == OS_OK);
    CHECK(exit_code == -123);
    CHECK(proc_get(&table, second, &process) == OS_ERR_NOT_FOUND);
    CHECK(process == NULL);
    CHECK(table.slots[1].state == PROC_UNUSED && table.slots[1].pid == 0u);
    return 1;
}

static int test_process_capacity_and_pid_exhaustion(void)
{
    proc_table_t table;
    uint32_t pids[MINIOS_MAX_PROCESSES];
    uint32_t pid;
    int32_t code;
    size_t i;

    proc_table_init(&table);
    for (i = 0; i < MINIOS_MAX_PROCESSES; ++i) {
        CHECK(proc_spawn(&table, 0u, (uintptr_t)i, &pids[i]) == OS_OK);
        CHECK(pids[i] == (uint32_t)i + 1u);
    }
    CHECK(proc_spawn(&table, 0u, (uintptr_t)0, &pid) == OS_ERR_FULL);
    CHECK(pid == 0u);
    CHECK(proc_exit(&table, pids[0], 9) == OS_OK);
    CHECK(proc_reap(&table, pids[0], &code) == OS_OK && code == 9);
    CHECK(proc_spawn(&table, 0u, (uintptr_t)0x99u, &pid) == OS_OK);
    CHECK(pid == 9u && table.slots[0].pid == 9u);

    proc_table_init(&table);
    table.next_pid = UINT32_MAX;
    CHECK(proc_spawn(&table, 0u, (uintptr_t)0, &pid) == OS_OK);
    CHECK(pid == UINT32_MAX && table.next_pid == 0u);
    CHECK(proc_exit(&table, pid, 0) == OS_OK);
    CHECK(proc_reap(&table, pid, &code) == OS_OK);
    CHECK(proc_spawn(&table, 0u, (uintptr_t)0, &pid) == OS_ERR_FULL);
    CHECK(pid == 0u);
    return 1;
}

static int test_vm_boundaries_and_permissions(void)
{
    vm_space_t space;
    vm_space_t snapshot;
    uint32_t physical = 99u;
    uint32_t high_virtual = (MINIOS_VIRTUAL_PAGES - 1u) * MINIOS_PAGE_SIZE;
    uint32_t high_frame = (MINIOS_PHYSICAL_FRAMES - 1u) * MINIOS_PAGE_SIZE;
    size_t i;

    (void)memset(&space, 0xa5, sizeof(space));
    vm_space_init(NULL);
    vm_space_init(&space);
    for (i = 0; i < MINIOS_MAX_MAPPINGS; ++i) {
        CHECK(space.mappings[i].present == 0u);
        CHECK(space.mappings[i].reserved == 0u);
    }
    CHECK(vm_map(NULL, 0u, 0u, VM_READ) == OS_ERR_INVALID);
    CHECK(vm_map(&space, 1u, 0u, VM_READ) == OS_ERR_INVALID);
    CHECK(vm_map(&space, 0u, 1u, VM_READ) == OS_ERR_INVALID);
    CHECK(vm_map(&space, MINIOS_VIRTUAL_PAGES * MINIOS_PAGE_SIZE,
                 0u, VM_READ) == OS_ERR_INVALID);
    CHECK(vm_map(&space, 0u,
                 MINIOS_PHYSICAL_FRAMES * MINIOS_PAGE_SIZE,
                 VM_READ) == OS_ERR_INVALID);
    CHECK(vm_map(&space, 0u, 0u, 0u) == OS_ERR_INVALID);
    CHECK(vm_map(&space, 0u, 0u, (uint8_t)0x80u) == OS_ERR_INVALID);

    CHECK(vm_map(&space, high_virtual, high_frame,
                 (uint8_t)(VM_READ | VM_WRITE | VM_USER)) == OS_OK);
    snapshot = space;
    CHECK(vm_map(&space, high_virtual, 0u, VM_READ) == OS_ERR_EXISTS);
    CHECK(memcmp(&space, &snapshot, sizeof(space)) == 0);
    CHECK(vm_translate(&space, high_virtual + MINIOS_PAGE_SIZE - 1u,
                       (uint8_t)(VM_READ | VM_WRITE), &physical) == OS_OK);
    CHECK(physical == high_frame + MINIOS_PAGE_SIZE - 1u);
    CHECK(vm_translate(&space, high_virtual, VM_EXEC, &physical) == OS_ERR_PERM);
    CHECK(physical == 0u);
    CHECK(vm_translate(&space, high_virtual, 0u, &physical) == OS_ERR_INVALID);
    CHECK(physical == 0u);
    CHECK(vm_translate(&space, high_virtual, VM_READ, NULL) == OS_ERR_INVALID);
    CHECK(vm_translate(NULL, high_virtual, VM_READ, &physical) == OS_ERR_INVALID);
    CHECK(physical == 0u);
    CHECK(vm_unmap(&space, high_virtual + 1u) == OS_ERR_INVALID);
    CHECK(vm_unmap(&space, high_virtual) == OS_OK);
    CHECK(vm_unmap(&space, high_virtual) == OS_ERR_NOT_FOUND);
    return 1;
}

static int test_vm_capacity_and_aliasing(void)
{
    vm_space_t space;
    uint32_t physical;
    size_t i;

    vm_space_init(&space);
    for (i = 0; i < MINIOS_MAX_MAPPINGS; ++i) {
        CHECK(vm_map(&space, (uint32_t)i * MINIOS_PAGE_SIZE,
                     0u, VM_READ) == OS_OK);
    }
    CHECK(vm_map(&space, (uint32_t)MINIOS_MAX_MAPPINGS * MINIOS_PAGE_SIZE,
                 MINIOS_PAGE_SIZE, VM_READ) == OS_ERR_FULL);
    CHECK(vm_translate(&space, 7u * MINIOS_PAGE_SIZE + 55u,
                       VM_READ, &physical) == OS_OK);
    CHECK(physical == 55u);
    CHECK(vm_unmap(&space, 3u * MINIOS_PAGE_SIZE) == OS_OK);
    CHECK(vm_map(&space, 12u * MINIOS_PAGE_SIZE,
                 2u * MINIOS_PAGE_SIZE, VM_EXEC) == OS_OK);
    return 1;
}

static int test_filesystem_names_and_capacity(void)
{
    static const char *const names[MINIOS_FS_MAX_FILES] = {
        "/a", "/b", "/c", "/d", "/e", "/f", "/g", "/h"
    };
    ramfs_t fs;
    char maximum[MINIOS_FS_NAME_STORAGE];
    char too_long[MINIOS_FS_NAME_STORAGE + 1u];
    size_t i;

    fs_init(NULL);
    fs_init(&fs);
    CHECK(fs_create(NULL, "/a") == OS_ERR_INVALID);
    CHECK(fs_create(&fs, NULL) == OS_ERR_INVALID);
    CHECK(fs_create(&fs, "relative") == OS_ERR_INVALID);
    CHECK(fs_create(&fs, "/") == OS_ERR_INVALID);
    CHECK(fs_create(&fs, "/a/b") == OS_ERR_INVALID);
    CHECK(fs_create(&fs, "/bad space") == OS_ERR_INVALID);
    maximum[0] = '/';
    too_long[0] = '/';
    for (i = 1u; i <= MINIOS_FS_NAME_CHARS; ++i) {
        maximum[i] = 'x';
        too_long[i] = 'y';
    }
    maximum[MINIOS_FS_NAME_CHARS + 1u] = '\0';
    too_long[MINIOS_FS_NAME_CHARS + 1u] = 'y';
    too_long[MINIOS_FS_NAME_CHARS + 2u] = '\0';
    CHECK(fs_create(&fs, maximum) == OS_OK);
    CHECK(fs_unlink(&fs, maximum) == OS_OK);
    CHECK(fs_create(&fs, too_long) == OS_ERR_INVALID);

    for (i = 0; i < MINIOS_FS_MAX_FILES; ++i) {
        CHECK(fs_create(&fs, names[i]) == OS_OK);
    }
    CHECK(fs_create(&fs, "/z") == OS_ERR_FULL);
    CHECK(fs_create(&fs, "/a") == OS_ERR_EXISTS);
    return 1;
}

static int test_filesystem_io_and_atomicity(void)
{
    static const uint8_t payload[] = {1u, 2u, 3u, 4u};
    static const uint8_t last = 0x5au;
    ramfs_t fs;
    ramfs_t snapshot;
    uint8_t output[16];
    size_t amount;
    size_t size;
    size_t slot;
    size_t i;

    fs_init(&fs);
    CHECK(fs_create(&fs, "/data") == OS_OK);
    CHECK(fs_write(&fs, "/data", 3u, payload, sizeof(payload), &amount) == OS_OK);
    CHECK(amount == sizeof(payload));
    CHECK(fs_stat(&fs, "/data", &size) == OS_OK && size == 7u);
    (void)memset(output, 0xff, sizeof(output));
    CHECK(fs_read(&fs, "/data", 0u, output, sizeof(output), &amount) == OS_OK);
    CHECK(amount == 7u);
    CHECK(output[0] == 0u && output[1] == 0u && output[2] == 0u);
    CHECK(memcmp(&output[3], payload, sizeof(payload)) == 0);

    snapshot = fs;
    CHECK(fs_write(&fs, "/data", MINIOS_FS_FILE_CAPACITY, &last, 1u,
                   &amount) == OS_ERR_NO_SPACE);
    CHECK(amount == 0u && memcmp(&fs, &snapshot, sizeof(fs)) == 0);
    CHECK(fs_write(&fs, "/data", MINIOS_FS_FILE_CAPACITY + 1u, NULL, 0u,
                   &amount) == OS_ERR_NO_SPACE);
    CHECK(memcmp(&fs, &snapshot, sizeof(fs)) == 0);
    CHECK(fs_write(&fs, "/data", MINIOS_FS_FILE_CAPACITY, NULL, 0u,
                   &amount) == OS_OK);
    CHECK(amount == 0u && memcmp(&fs, &snapshot, sizeof(fs)) == 0);
    CHECK(fs_write(&fs, "/data", 0u, NULL, 1u, &amount) == OS_ERR_INVALID);
    CHECK(fs_write(&fs, "/missing", 0u, payload, 1u, &amount) ==
          OS_ERR_NOT_FOUND);
    CHECK(fs_write(&fs, "/data", 0u, payload, 1u, NULL) == OS_ERR_INVALID);

    CHECK(fs_read(&fs, "/data", SIZE_MAX, NULL, 0u, &amount) == OS_OK);
    CHECK(amount == 0u);
    CHECK(fs_read(&fs, "/data", 0u, NULL, 1u, &amount) == OS_ERR_INVALID);
    CHECK(fs_read(&fs, "/missing", 0u, output, 1u, &amount) ==
          OS_ERR_NOT_FOUND);
    CHECK(fs_stat(&fs, "/data", NULL) == OS_ERR_INVALID);

    CHECK(fs_write(&fs, "/data", MINIOS_FS_FILE_CAPACITY - 1u,
                   &last, 1u, &amount) == OS_OK);
    CHECK(fs_stat(&fs, "/data", &size) == OS_OK);
    CHECK(size == MINIOS_FS_FILE_CAPACITY);
    CHECK(fs_read(&fs, "/data", MINIOS_FS_FILE_CAPACITY - 1u,
                  output, sizeof(output), &amount) == OS_OK);
    CHECK(amount == 1u && output[0] == last);

    for (slot = 0; slot < MINIOS_FS_MAX_FILES; ++slot) {
        if (fs.files[slot].used != 0u) {
            break;
        }
    }
    CHECK(slot < MINIOS_FS_MAX_FILES);
    CHECK(fs_unlink(&fs, "/data") == OS_OK);
    CHECK(fs.files[slot].used == 0u && fs.files[slot].size == 0u);
    for (i = 0; i < MINIOS_FS_NAME_STORAGE; ++i) {
        CHECK(fs.files[slot].name[i] == '\0');
    }
    for (i = 0; i < MINIOS_FS_FILE_CAPACITY; ++i) {
        CHECK(fs.files[slot].data[i] == 0u);
    }
    CHECK(fs_unlink(&fs, "/data") == OS_ERR_NOT_FOUND);
    return 1;
}

typedef int (*test_fn_t)(void);

typedef struct {
    const char *name;
    test_fn_t run;
} test_case_t;

int main(void)
{
    static const test_case_t cases[] = {
        {"process initialization and errors", test_process_initialization_and_errors},
        {"process lifecycle", test_process_lifecycle},
        {"process capacity and PID exhaustion", test_process_capacity_and_pid_exhaustion},
        {"VM boundaries and permissions", test_vm_boundaries_and_permissions},
        {"VM capacity and aliasing", test_vm_capacity_and_aliasing},
        {"filesystem names and capacity", test_filesystem_names_and_capacity},
        {"filesystem I/O and atomicity", test_filesystem_io_and_atomicity}
    };
    size_t passed = 0u;
    size_t i;

    for (i = 0; i < sizeof(cases) / sizeof(cases[0]); ++i) {
        int result = cases[i].run();
        (void)printf("[%s] %s\n", result != 0 ? "PASS" : "FAIL", cases[i].name);
        if (result != 0) {
            ++passed;
        }
    }
    (void)printf("reference contract tests: %zu/%zu passed\n", passed,
                 sizeof(cases) / sizeof(cases[0]));
    return passed == sizeof(cases) / sizeof(cases[0]) ? 0 : 1;
}
