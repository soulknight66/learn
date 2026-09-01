#include "tinykernel.h"

#include <stdio.h>
#include <string.h>

static int failures;

#define CHECK(condition) check_result((condition), #condition, __LINE__)

static void check_result(int passed, const char *expression, int line)
{
    if (!passed) {
        fprintf(stderr, "line %d: check failed: %s\n", line, expression);
        ++failures;
    }
}

static void test_frames(void)
{
    tk_frame_allocator_t frames;
    int frame;

    tk_frames_init(NULL, 4u);
    CHECK(tk_frame_alloc(NULL) == -1);
    CHECK(tk_frame_free(NULL, 0u) == -1);
    CHECK(tk_frame_available(NULL) == 0u);

    tk_frames_init(&frames, 0u);
    CHECK(tk_frame_available(&frames) == 0u);
    tk_frames_init(&frames, TK_MAX_FRAMES + 1u);
    CHECK(tk_frame_available(&frames) == 0u);
    tk_frames_init(&frames, 3u);
    for (frame = 0; frame < 3; ++frame) {
        CHECK(tk_frame_alloc(&frames) == frame);
    }
    CHECK(tk_frame_alloc(&frames) == -1);
    CHECK(tk_frame_free(&frames, 2u) == 0);
    CHECK(tk_frame_alloc(&frames) == 2);
}

static void test_scheduler_capacity(void)
{
    tk_scheduler_t scheduler;
    uint32_t pid;

    tk_scheduler_init(&scheduler);
    for (pid = 1u; pid <= TK_MAX_PROCESSES; ++pid) {
        CHECK(tk_process_spawn(&scheduler) == (int)pid);
    }
    CHECK(tk_process_spawn(&scheduler) == -1);
    CHECK(tk_process_wake(&scheduler, 1u) == -1);
    CHECK(tk_process_exit(&scheduler, 1u) == 0);
    CHECK(tk_process_exit(&scheduler, 1u) == -1);
    CHECK(tk_process_spawn(&scheduler) == (int)TK_MAX_PROCESSES + 1);
    CHECK(tk_process_state(&scheduler, 1u) == TK_UNUSED);
}

static void test_scheduler_cursor(void)
{
    tk_scheduler_t scheduler;
    int first;
    int second;
    int third;

    tk_scheduler_init(NULL);
    CHECK(tk_process_spawn(NULL) == -1);
    CHECK(tk_schedule(NULL) == -1);
    CHECK(tk_current_pid(NULL) == -1);

    tk_scheduler_init(&scheduler);
    first = tk_process_spawn(&scheduler);
    second = tk_process_spawn(&scheduler);
    third = tk_process_spawn(&scheduler);
    CHECK(tk_schedule(&scheduler) == first);
    CHECK(tk_schedule(&scheduler) == second);
    CHECK(tk_process_block(&scheduler, (uint32_t)second) == 0);
    CHECK(tk_schedule(&scheduler) == third);
    CHECK(tk_process_block(&scheduler, (uint32_t)third) == 0);
    CHECK(tk_schedule(&scheduler) == first);
    CHECK(tk_process_block(&scheduler, (uint32_t)second) == -1);
    CHECK(tk_process_wake(&scheduler, (uint32_t)second) == 0);
    CHECK(tk_process_wake(&scheduler, (uint32_t)second) == -1);
}

static void test_vm_failures(void)
{
    tk_frame_allocator_t frames;
    tk_address_space_t space;
    uint32_t result = 0xDEADBEEFu;

    tk_frames_init(&frames, 1u);
    tk_vm_init(&space, &frames);
    CHECK(tk_vm_map(NULL, 0u, TK_VM_READ) == -1);
    CHECK(tk_vm_map(&space, 1u, TK_VM_READ) == -1);
    CHECK(tk_vm_map(&space, 0u, TK_VM_WRITE) == -1);
    CHECK(tk_vm_map(&space, 0u, (uint8_t)(TK_VM_READ | 0x80u)) == -1);
    CHECK(tk_frame_available(&frames) == 1u);
    CHECK(tk_vm_map(&space, 0u, TK_VM_READ | TK_VM_USER) == 0);
    CHECK(tk_vm_map(&space, TK_PAGE_SIZE, TK_VM_READ) == -1);
    CHECK(tk_vm_translate(&space, 17u, 0u, &result) == 0);
    CHECK(result == 17u);
    result = 0xDEADBEEFu;
    CHECK(tk_vm_translate(&space, 0u, TK_VM_WRITE, &result) == -1);
    CHECK(result == 0xDEADBEEFu);
    CHECK(tk_vm_translate(&space, 0u, 0x80u, &result) == -1);
    CHECK(tk_vm_translate(&space, 0u, 0u, NULL) == -1);
    CHECK(tk_vm_unmap(&space, 2u) == -1);
    CHECK(tk_vm_unmap(&space, 0u) == 0);
    CHECK(tk_vm_unmap(&space, 0u) == -1);
}

static void test_vm_table_capacity(void)
{
    tk_frame_allocator_t frames;
    tk_address_space_t space;
    size_t index;
    size_t before;

    tk_frames_init(&frames, TK_MAX_FRAMES);
    tk_vm_init(&space, &frames);
    for (index = 0; index < TK_MAX_MAPPINGS; ++index) {
        CHECK(tk_vm_map(&space, (uint32_t)index * TK_PAGE_SIZE, TK_VM_READ) == 0);
    }
    CHECK(tk_vm_mapping_count(&space) == TK_MAX_MAPPINGS);
    before = tk_frame_available(&frames);
    CHECK(tk_vm_map(&space, (uint32_t)TK_MAX_MAPPINGS * TK_PAGE_SIZE,
                    TK_VM_READ) == -1);
    CHECK(tk_frame_available(&frames) == before);
    CHECK(tk_vm_map(&space, 0u, TK_VM_READ) == -1);
    CHECK(tk_frame_available(&frames) == before);
}

static void test_filesystem_boundaries(void)
{
    tk_fs_t fs;
    char max_name[TK_NAME_CAPACITY];
    char unterminated[TK_NAME_CAPACITY];
    uint8_t data[TK_FILE_CAPACITY];
    uint8_t output[TK_FILE_CAPACITY];
    size_t index;

    for (index = 0; index < TK_NAME_CAPACITY - 1u; ++index) {
        max_name[index] = 'n';
    }
    max_name[TK_NAME_CAPACITY - 1u] = '\0';
    for (index = 0; index < TK_NAME_CAPACITY; ++index) {
        unterminated[index] = 'x';
    }
    for (index = 0; index < TK_FILE_CAPACITY; ++index) {
        data[index] = (uint8_t)index;
        output[index] = 0xCCu;
    }

    tk_fs_init(NULL);
    tk_fs_init(&fs);
    CHECK(tk_fs_create(&fs, NULL) == -1);
    CHECK(tk_fs_create(&fs, "") == -1);
    CHECK(tk_fs_create(&fs, unterminated) == -1);
    CHECK(tk_fs_create(&fs, max_name) == 0);
    CHECK(tk_fs_write(&fs, max_name, data, TK_FILE_CAPACITY) == 0);
    CHECK(tk_fs_write(&fs, max_name, data, TK_FILE_CAPACITY + 1u) == -1);
    CHECK(tk_fs_size(&fs, max_name) == (int)TK_FILE_CAPACITY);
    CHECK(tk_fs_read(&fs, max_name, output, TK_FILE_CAPACITY - 1u) == -1);
    CHECK(output[0] == 0xCCu);
    CHECK(tk_fs_read(&fs, max_name, output, TK_FILE_CAPACITY) ==
          (int)TK_FILE_CAPACITY);
    CHECK(memcmp(data, output, TK_FILE_CAPACITY) == 0);
    CHECK(tk_fs_write(&fs, max_name, NULL, 0u) == 0);
    CHECK(tk_fs_read(&fs, max_name, NULL, 0u) == 0);
}

static void test_filesystem_capacity(void)
{
    tk_fs_t fs;
    char name[5];
    size_t index;

    tk_fs_init(&fs);
    for (index = 0; index < TK_MAX_FILES; ++index) {
        name[0] = 'f';
        name[1] = (char)('0' + (index / 10u));
        name[2] = (char)('0' + (index % 10u));
        name[3] = '\0';
        CHECK(tk_fs_create(&fs, name) == 0);
    }
    CHECK(tk_fs_create(&fs, "extra") == -1);
    CHECK(tk_fs_file_count(&fs) == TK_MAX_FILES);
    CHECK(tk_fs_unlink(&fs, "f07") == 0);
    CHECK(tk_fs_create(&fs, "new") == 0);
    CHECK(tk_fs_file_count(&fs) == TK_MAX_FILES);
}

int main(void)
{
    test_frames();
    test_scheduler_capacity();
    test_scheduler_cursor();
    test_vm_failures();
    test_vm_table_capacity();
    test_filesystem_boundaries();
    test_filesystem_capacity();

    if (failures != 0) {
        fprintf(stderr, "reference tests: %d failure(s)\n", failures);
        return 1;
    }
    puts("reference tests: PASS");
    return 0;
}
