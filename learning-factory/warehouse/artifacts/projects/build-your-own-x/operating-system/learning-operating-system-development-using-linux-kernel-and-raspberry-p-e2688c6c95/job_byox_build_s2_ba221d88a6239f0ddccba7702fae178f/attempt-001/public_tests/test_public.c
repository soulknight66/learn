#include "minios.h"

#include <stdio.h>
#include <string.h>

#define EXPECT(condition)                                                     \
    do {                                                                      \
        if (!(condition)) {                                                   \
            (void)printf("  line %d: expected %s\n", __LINE__, #condition); \
            return 0;                                                         \
        }                                                                     \
    } while (0)

static int test_initializers(void)
{
    proc_table_t table;
    vm_space_t space;
    ramfs_t fs;
    size_t i;

    (void)memset(&table, 0xa5, sizeof(table));
    (void)memset(&space, 0xa5, sizeof(space));
    (void)memset(&fs, 0xa5, sizeof(fs));
    proc_table_init(&table);
    vm_space_init(&space);
    fs_init(&fs);

    EXPECT(table.next_pid == 1u);
    EXPECT(table.current_slot == -1);
    for (i = 0; i < MINIOS_MAX_PROCESSES; ++i) {
        EXPECT(table.slots[i].state == PROC_UNUSED);
        EXPECT(table.slots[i].pid == 0u);
    }
    for (i = 0; i < MINIOS_MAX_MAPPINGS; ++i) {
        EXPECT(space.mappings[i].present == 0u);
    }
    for (i = 0; i < MINIOS_FS_MAX_FILES; ++i) {
        EXPECT(fs.files[i].used == 0u);
        EXPECT(fs.files[i].size == 0u);
    }
    return 1;
}

static int test_process_round_robin(void)
{
    proc_table_t table;
    const process_t *process = NULL;
    uint32_t first = 0;
    uint32_t second = 0;
    uint32_t selected = 0;
    int32_t code = 0;

    proc_table_init(&table);
    EXPECT(proc_spawn(&table, 0, (uintptr_t)0x1000u, &first) == OS_OK);
    EXPECT(proc_spawn(&table, first, (uintptr_t)0x2000u, &second) == OS_OK);
    EXPECT(first == 1u && second == 2u);
    EXPECT(proc_schedule(&table, &selected) == OS_OK && selected == first);
    EXPECT(proc_schedule(&table, &selected) == OS_OK && selected == second);
    EXPECT(proc_block(&table, second) == OS_OK);
    EXPECT(proc_schedule(&table, &selected) == OS_OK && selected == first);
    EXPECT(proc_wake(&table, second) == OS_OK);
    EXPECT(proc_schedule(&table, &selected) == OS_OK && selected == second);
    EXPECT(proc_exit(&table, second, -17) == OS_OK);
    EXPECT(proc_get(&table, second, &process) == OS_OK);
    EXPECT(process != NULL && process->state == PROC_ZOMBIE);
    EXPECT(proc_reap(&table, second, &code) == OS_OK && code == -17);
    EXPECT(proc_get(&table, second, &process) == OS_ERR_NOT_FOUND);
    EXPECT(process == NULL);
    return 1;
}

static int test_process_rejections(void)
{
    proc_table_t table;
    uint32_t pid = 99;
    uint32_t i;

    proc_table_init(&table);
    EXPECT(proc_spawn(&table, 777u, (uintptr_t)0, &pid) == OS_ERR_NOT_FOUND);
    EXPECT(pid == 0u);
    for (i = 0; i < MINIOS_MAX_PROCESSES; ++i) {
        EXPECT(proc_spawn(&table, 0, (uintptr_t)i, &pid) == OS_OK);
    }
    EXPECT(proc_spawn(&table, 0, (uintptr_t)0, &pid) == OS_ERR_FULL);
    EXPECT(pid == 0u);
    EXPECT(proc_block(&table, 1u) == OS_ERR_STATE);
    return 1;
}

static int test_virtual_memory(void)
{
    vm_space_t space;
    uint32_t physical = 123u;

    vm_space_init(&space);
    EXPECT(vm_map(&space, 0x1000u, 0x5000u,
                  (uint8_t)(VM_READ | VM_WRITE | VM_USER)) == OS_OK);
    EXPECT(vm_translate(&space, 0x1123u, VM_READ, &physical) == OS_OK);
    EXPECT(physical == 0x5123u);
    EXPECT(vm_translate(&space, 0x1123u, VM_EXEC, &physical) == OS_ERR_PERM);
    EXPECT(physical == 0u);
    EXPECT(vm_map(&space, 0x1000u, 0x6000u, VM_READ) == OS_ERR_EXISTS);
    EXPECT(vm_map(&space, 0x1001u, 0x6000u, VM_READ) == OS_ERR_INVALID);
    EXPECT(vm_map(&space, 0x2000u, 0x6001u, VM_READ) == OS_ERR_INVALID);
    EXPECT(vm_unmap(&space, 0x1000u) == OS_OK);
    EXPECT(vm_translate(&space, 0x1000u, VM_READ, &physical) ==
           OS_ERR_NOT_FOUND);
    return 1;
}

static int test_filesystem(void)
{
    static const uint8_t abc[] = {'a', 'b', 'c'};
    static const uint8_t z[] = {'z'};
    uint8_t output[8];
    uint8_t snapshot[8];
    ramfs_t fs;
    size_t amount = 99u;
    size_t size = 99u;

    fs_init(&fs);
    EXPECT(fs_create(&fs, "/note") == OS_OK);
    EXPECT(fs_create(&fs, "/note") == OS_ERR_EXISTS);
    EXPECT(fs_create(&fs, "/bad/name") == OS_ERR_INVALID);
    EXPECT(fs_write(&fs, "/note", 0, abc, sizeof(abc), &amount) == OS_OK);
    EXPECT(amount == sizeof(abc));
    EXPECT(fs_write(&fs, "/note", 5, z, sizeof(z), &amount) == OS_OK);
    EXPECT(fs_stat(&fs, "/note", &size) == OS_OK && size == 6u);
    (void)memset(output, 0xff, sizeof(output));
    EXPECT(fs_read(&fs, "/note", 0, output, sizeof(output), &amount) == OS_OK);
    EXPECT(amount == 6u);
    EXPECT(output[0] == 'a' && output[1] == 'b' && output[2] == 'c');
    EXPECT(output[3] == 0u && output[4] == 0u && output[5] == 'z');

    (void)memcpy(snapshot, output, sizeof(snapshot));
    EXPECT(fs_write(&fs, "/note", MINIOS_FS_FILE_CAPACITY, z, 1u,
                    &amount) == OS_ERR_NO_SPACE);
    EXPECT(amount == 0u);
    EXPECT(fs_stat(&fs, "/note", &size) == OS_OK && size == 6u);
    (void)memset(output, 0xff, sizeof(output));
    EXPECT(fs_read(&fs, "/note", 0, output, sizeof(output), &amount) == OS_OK);
    EXPECT(memcmp(output, snapshot, 6u) == 0);
    EXPECT(fs_unlink(&fs, "/note") == OS_OK);
    EXPECT(fs_stat(&fs, "/note", &size) == OS_ERR_NOT_FOUND);
    EXPECT(size == 0u);
    return 1;
}

typedef int (*test_function_t)(void);

typedef struct {
    const char *name;
    test_function_t function;
} test_case_t;

int main(void)
{
    static const test_case_t tests[] = {
        {"initializers", test_initializers},
        {"process round robin", test_process_round_robin},
        {"process rejections", test_process_rejections},
        {"virtual memory", test_virtual_memory},
        {"RAM filesystem", test_filesystem}
    };
    size_t i;
    size_t passed = 0;

    for (i = 0; i < sizeof(tests) / sizeof(tests[0]); ++i) {
        int ok = tests[i].function();
        (void)printf("[%s] %s\n", ok != 0 ? "PASS" : "FAIL", tests[i].name);
        if (ok != 0) {
            ++passed;
        }
    }
    (void)printf("%zu/%zu public checks passed\n", passed,
                 sizeof(tests) / sizeof(tests[0]));
    return passed == sizeof(tests) / sizeof(tests[0]) ? 0 : 1;
}
