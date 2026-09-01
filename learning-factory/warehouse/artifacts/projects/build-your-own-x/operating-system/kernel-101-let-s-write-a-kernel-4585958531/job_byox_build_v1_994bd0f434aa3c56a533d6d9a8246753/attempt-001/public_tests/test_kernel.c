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

static void stage1(void)
{
    tk_frame_allocator_t frames;

    tk_frames_init(&frames, 4u);
    CHECK(tk_frame_available(&frames) == 4u);
    CHECK(tk_frame_alloc(&frames) == 0);
    CHECK(tk_frame_alloc(&frames) == 1);
    CHECK(tk_frame_available(&frames) == 2u);
    CHECK(tk_frame_free(&frames, 0u) == 0);
    CHECK(tk_frame_free(&frames, 0u) == -1);
    CHECK(tk_frame_alloc(&frames) == 0);
    CHECK(tk_frame_free(&frames, 9u) == -1);
    CHECK(tk_frame_available(&frames) == 2u);
}

static void stage2(void)
{
    tk_scheduler_t scheduler;
    int first;
    int second;

    tk_scheduler_init(&scheduler);
    first = tk_process_spawn(&scheduler);
    second = tk_process_spawn(&scheduler);
    CHECK(first == 1);
    CHECK(second == 2);
    CHECK(tk_schedule(&scheduler) == first);
    CHECK(tk_current_pid(&scheduler) == first);
    CHECK(tk_schedule(&scheduler) == second);
    CHECK(tk_process_block(&scheduler, (uint32_t)second) == 0);
    CHECK(tk_current_pid(&scheduler) == -1);
    CHECK(tk_schedule(&scheduler) == first);
    CHECK(tk_process_wake(&scheduler, (uint32_t)second) == 0);
    CHECK(tk_process_exit(&scheduler, (uint32_t)first) == 0);
    CHECK(tk_schedule(&scheduler) == second);
    CHECK(tk_process_state(&scheduler, 999u) == TK_UNUSED);
}

static void stage3(void)
{
    tk_frame_allocator_t frames;
    tk_address_space_t space;
    uint32_t physical = 0xA5A5A5A5u;

    tk_frames_init(&frames, 3u);
    tk_vm_init(&space, &frames);
    CHECK(tk_vm_map(&space, 0x4001u, TK_VM_READ) == -1);
    CHECK(tk_vm_map(&space, 0x4000u, TK_VM_WRITE) == -1);
    CHECK(tk_vm_map(&space, 0x4000u, TK_VM_READ | TK_VM_WRITE) == 0);
    CHECK(tk_vm_mapping_count(&space) == 1u);
    CHECK(tk_frame_available(&frames) == 2u);
    CHECK(tk_vm_map(&space, 0x4000u, TK_VM_READ) == -1);
    CHECK(tk_frame_available(&frames) == 2u);
    CHECK(tk_vm_translate(&space, 0x4123u, TK_VM_READ, &physical) == 0);
    CHECK(physical == 0x123u);
    physical = 0xA5A5A5A5u;
    CHECK(tk_vm_translate(&space, 0x4000u, TK_VM_EXEC, &physical) == -1);
    CHECK(physical == 0xA5A5A5A5u);
    CHECK(tk_vm_unmap(&space, 0x4000u) == 0);
    CHECK(tk_frame_available(&frames) == 3u);
    CHECK(tk_vm_mapping_count(&space) == 0u);
}

static void stage4(void)
{
    tk_fs_t fs;
    static const uint8_t input[] = {0u, 1u, 2u, 0u, 4u};
    uint8_t output[sizeof(input)] = {9u, 9u, 9u, 9u, 9u};

    tk_fs_init(&fs);
    CHECK(tk_fs_create(&fs, "notes") == 0);
    CHECK(tk_fs_create(&fs, "notes") == -1);
    CHECK(tk_fs_write(&fs, "notes", input, sizeof(input)) == 0);
    CHECK(tk_fs_size(&fs, "notes") == (int)sizeof(input));
    CHECK(tk_fs_read(&fs, "notes", output, sizeof(output)) == (int)sizeof(input));
    CHECK(memcmp(input, output, sizeof(input)) == 0);
    output[0] = 77u;
    CHECK(tk_fs_read(&fs, "notes", output, sizeof(output) - 1u) == -1);
    CHECK(output[0] == 77u);
    CHECK(tk_fs_file_count(&fs) == 1u);
    CHECK(tk_fs_unlink(&fs, "notes") == 0);
    CHECK(tk_fs_file_count(&fs) == 0u);
    CHECK(tk_fs_read(&fs, "notes", output, sizeof(output)) == -1);
}

static int wants_stage(const char *selection, char stage)
{
    return strcmp(selection, "all") == 0 ||
           (selection[0] == stage && selection[1] == '\0');
}

int main(int argc, char **argv)
{
    const char *selection = argc == 2 ? argv[1] : "all";

    if (wants_stage(selection, '1')) {
        stage1();
    }
    if (wants_stage(selection, '2')) {
        stage2();
    }
    if (wants_stage(selection, '3')) {
        stage3();
    }
    if (wants_stage(selection, '4')) {
        stage4();
    }
    if (strcmp(selection, "all") != 0 &&
        strcmp(selection, "1") != 0 && strcmp(selection, "2") != 0 &&
        strcmp(selection, "3") != 0 && strcmp(selection, "4") != 0) {
        fprintf(stderr, "usage: %s [all|1|2|3|4]\n", argv[0]);
        return 2;
    }
    if (failures != 0) {
        fprintf(stderr, "public tests: %d failure(s)\n", failures);
        return 1;
    }
    printf("public tests: PASS (%s)\n", selection);
    return 0;
}
