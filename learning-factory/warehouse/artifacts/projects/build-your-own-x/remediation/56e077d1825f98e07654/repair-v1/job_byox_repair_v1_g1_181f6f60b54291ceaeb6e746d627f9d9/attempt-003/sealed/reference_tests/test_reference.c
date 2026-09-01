#include "tinyarm.h"

#include <stdint.h>
#include <stdio.h>
#include <string.h>

#define REQUIRE(expression)                                                       \
    do {                                                                          \
        if (!(expression)) {                                                      \
            fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, #expression); \
            return 1;                                                             \
        }                                                                         \
    } while (0)

typedef struct {
    int calls;
    uint64_t observed[4];
} sleepy_t;

static mk_step_result_t sleep_once(struct mk_kernel *kernel, mk_pid_t pid,
                                   void *userdata) {
    sleepy_t *state = (sleepy_t *)userdata;
    (void)pid;
    state->observed[state->calls] = kernel->now;
    state->calls += 1;
    if (state->calls == 1) {
        if (mk_sleep_current(kernel, 2u) != MK_OK) {
            return (mk_step_result_t)99;
        }
        return MK_STEP_CONTINUE;
    }
    return MK_STEP_EXIT;
}

typedef struct {
    int label;
    int calls;
    int *trace;
    size_t *length;
} runner_t;

static mk_step_result_t run_three(struct mk_kernel *kernel, mk_pid_t pid,
                                  void *userdata) {
    runner_t *runner = (runner_t *)userdata;
    (void)kernel;
    (void)pid;
    runner->trace[*runner->length] = runner->label;
    *runner->length += 1u;
    runner->calls += 1;
    return runner->calls == 3 ? MK_STEP_EXIT : MK_STEP_CONTINUE;
}

static mk_step_result_t keep_yielding(struct mk_kernel *kernel, mk_pid_t pid,
                                      void *userdata) {
    (void)kernel;
    (void)pid;
    (void)userdata;
    return MK_STEP_YIELD;
}

typedef struct {
    mk_pid_t replacement_pid;
    mk_status_t exit_status;
    mk_status_t reap_status;
    mk_status_t nested_tick_status;
    int outer_calls;
    int replacement_calls;
} reentrant_t;

static mk_step_result_t replacement_continues(struct mk_kernel *kernel,
                                               mk_pid_t pid, void *userdata) {
    reentrant_t *state = (reentrant_t *)userdata;
    (void)kernel;
    (void)pid;
    state->replacement_calls += 1;
    return MK_STEP_CONTINUE;
}

static mk_step_result_t exit_reap_replace_and_tick(struct mk_kernel *kernel,
                                                    mk_pid_t pid,
                                                    void *userdata) {
    reentrant_t *state = (reentrant_t *)userdata;
    state->outer_calls += 1;
    state->exit_status = mk_exit_current(kernel, 19);
    state->reap_status = mk_reap(kernel, pid, NULL);
    state->replacement_pid = mk_spawn(kernel, replacement_continues, state);
    state->nested_tick_status = mk_tick(kernel);
    return MK_STEP_EXIT;
}

static int test_initialization_and_scheduler(void) {
    mk_kernel_t kernel;
    mk_kernel_t before;
    sleepy_t sleepy = {0, {0u, 0u, 0u, 0u}};
    int trace[6] = {0, 0, 0, 0, 0, 0};
    size_t length = 0u;
    runner_t first = {1, 0, trace, &length};
    runner_t second = {2, 0, trace, &length};

    memset(&kernel, 0xa5, sizeof(kernel));
    before = kernel;
    REQUIRE(mk_init(&kernel, 0u) == MK_ERR_INVALID);
    REQUIRE(memcmp(&kernel, &before, sizeof(kernel)) == 0);
    REQUIRE(mk_init(&kernel, MK_MAX_QUANTUM + 1u) == MK_ERR_INVALID);
    REQUIRE(mk_init(&kernel, 1u) == MK_OK);
    REQUIRE(kernel.now == 0u);
    REQUIRE(kernel.current_slot == -1 && kernel.last_slot == -1);
    REQUIRE(mk_vm_free_frames(&kernel) == MK_FRAME_COUNT);
    REQUIRE(mk_fs_free_blocks(&kernel) == MK_FS_BLOCK_COUNT);
    REQUIRE(mk_tick(&kernel) == MK_ERR_NOT_FOUND);
    REQUIRE(kernel.now == 0u);

    REQUIRE(mk_spawn(&kernel, sleep_once, &sleepy) == 1u);
    REQUIRE(mk_run(&kernel, 10u) == 3u);
    REQUIRE(sleepy.calls == 2);
    REQUIRE(sleepy.observed[0] == 0u && sleepy.observed[1] == 2u);
    REQUIRE(kernel.now == 3u);

    REQUIRE(mk_init(&kernel, 2u) == MK_OK);
    REQUIRE(mk_spawn(&kernel, run_three, &first) == 1u);
    REQUIRE(mk_spawn(&kernel, run_three, &second) == 2u);
    REQUIRE(mk_run(&kernel, 20u) == 6u);
    REQUIRE(length == 6u);
    REQUIRE(trace[0] == 1 && trace[1] == 1 && trace[2] == 2);
    REQUIRE(trace[3] == 2 && trace[4] == 1 && trace[5] == 2);
    REQUIRE(mk_current_pid(&kernel) == 0u);
    return 0;
}

static int test_lifecycle_capacity_and_reap(void) {
    mk_kernel_t kernel;
    mk_pid_t pids[MK_MAX_TASKS];
    size_t index;
    int exit_code = 0;

    REQUIRE(mk_init(&kernel, 1u) == MK_OK);
    REQUIRE(mk_spawn(&kernel, NULL, NULL) == 0u);
    for (index = 0u; index < MK_MAX_TASKS; ++index) {
        pids[index] = mk_spawn(&kernel, keep_yielding, NULL);
        REQUIRE(pids[index] == (mk_pid_t)(index + 1u));
    }
    REQUIRE(mk_spawn(&kernel, keep_yielding, NULL) == 0u);
    REQUIRE(mk_kill(&kernel, pids[2], 37) == MK_OK);
    REQUIRE(mk_task(&kernel, pids[2])->state == MK_TASK_ZOMBIE);
    REQUIRE(mk_spawn(&kernel, keep_yielding, NULL) == 0u);
    REQUIRE(mk_reap(&kernel, pids[2], &exit_code) == MK_OK);
    REQUIRE(exit_code == 37);
    REQUIRE(mk_task(&kernel, pids[2]) == NULL);
    REQUIRE(mk_spawn(&kernel, keep_yielding, NULL) == MK_MAX_TASKS + 1u);
    REQUIRE(mk_kill(&kernel, pids[2], 0) == MK_ERR_NOT_FOUND);
    REQUIRE(mk_reap(&kernel, pids[0], NULL) == MK_ERR_STATE);
    REQUIRE(mk_sleep_current(&kernel, 1u) == MK_ERR_STATE);
    return 0;
}

static int test_reentrant_callback_preserves_task_identity(void) {
    mk_kernel_t kernel;
    reentrant_t state = {0u, MK_ERR_STATE, MK_ERR_STATE, MK_ERR_STATE, 0, 0};
    mk_pid_t original_pid;
    const mk_task_t *replacement;

    REQUIRE(mk_init(&kernel, 2u) == MK_OK);
    original_pid = mk_spawn(&kernel, exit_reap_replace_and_tick, &state);
    REQUIRE(original_pid == 1u);
    REQUIRE(mk_tick(&kernel) == MK_OK);
    REQUIRE(state.outer_calls == 1);
    REQUIRE(state.exit_status == MK_OK);
    REQUIRE(state.reap_status == MK_OK);
    REQUIRE(state.replacement_pid == 2u);
    REQUIRE(state.nested_tick_status == MK_OK);
    REQUIRE(state.replacement_calls == 1);
    REQUIRE(mk_task(&kernel, original_pid) == NULL);
    replacement = mk_task(&kernel, state.replacement_pid);
    REQUIRE(replacement != NULL);
    REQUIRE(replacement->state == MK_TASK_RUNNING);
    REQUIRE(replacement->steps == 1u);
    REQUIRE(replacement->quantum_left == 1u);
    REQUIRE(mk_current_pid(&kernel) == state.replacement_pid);
    REQUIRE(kernel.now == 2u);
    return 0;
}

static int test_vm_translation_atomicity_and_cleanup(void) {
    mk_kernel_t kernel;
    mk_pid_t first;
    mk_pid_t second;
    uint8_t initial[2] = {0xaau, 0xbbu};
    uint8_t crossing[4] = {1u, 2u, 3u, 4u};
    uint8_t output[4] = {0u, 0u, 0u, 0u};
    size_t first_frame;

    REQUIRE(mk_init(&kernel, 1u) == MK_OK);
    first = mk_spawn(&kernel, keep_yielding, NULL);
    second = mk_spawn(&kernel, keep_yielding, NULL);
    REQUIRE(first != 0u && second != 0u);
    REQUIRE(mk_vm_map(&kernel, first, 1u, MK_VM_READ) == MK_ERR_RANGE);
    REQUIRE(mk_vm_map(&kernel, first, 0u, 0u) == MK_ERR_INVALID);
    REQUIRE(mk_vm_map(&kernel, first, 0u, MK_VM_READ | MK_VM_WRITE) == MK_OK);
    first_frame = mk_task(&kernel, first)->pages[0].frame;
    REQUIRE(first_frame == 0u);
    REQUIRE(mk_vm_map(&kernel, first, 0u, MK_VM_READ) == MK_ERR_EXISTS);
    REQUIRE(mk_vm_map(&kernel, first, MK_PAGE_SIZE, MK_VM_READ) == MK_OK);
    REQUIRE(mk_vm_write(&kernel, first, MK_PAGE_SIZE - 2u, initial,
                        sizeof(initial)) == MK_OK);
    REQUIRE(mk_vm_write(&kernel, first, MK_PAGE_SIZE - 2u, crossing,
                        sizeof(crossing)) == MK_ERR_PERMISSION);
    REQUIRE(mk_vm_read(&kernel, first, MK_PAGE_SIZE - 2u, output, 2u) == MK_OK);
    REQUIRE(output[0] == 0xaau && output[1] == 0xbbu);
    REQUIRE(mk_vm_read(&kernel, first, MK_USER_SIZE, NULL, 0u) == MK_OK);
    REQUIRE(mk_vm_read(&kernel, first, MK_USER_SIZE, output, 1u) == MK_ERR_RANGE);
    REQUIRE(mk_vm_unmap(&kernel, first, 0u) == MK_OK);
    REQUIRE(kernel.frames[first_frame][MK_PAGE_SIZE - 1u] == 0u);
    REQUIRE(mk_vm_map(&kernel, second, 0u, MK_VM_READ) == MK_OK);
    REQUIRE(mk_task(&kernel, second)->pages[0].frame == first_frame);
    REQUIRE(mk_vm_read(&kernel, second, 0u, output, sizeof(output)) == MK_OK);
    REQUIRE(output[0] == 0u && output[1] == 0u && output[2] == 0u &&
            output[3] == 0u);
    REQUIRE(mk_vm_map(&kernel, second, MK_PAGE_SIZE, MK_VM_READ) == MK_OK);
    REQUIRE(mk_vm_free_frames(&kernel) == MK_FRAME_COUNT - 3u);
    REQUIRE(mk_kill(&kernel, second, -9) == MK_OK);
    REQUIRE(mk_vm_free_frames(&kernel) == MK_FRAME_COUNT - 1u);
    REQUIRE(mk_vm_read(&kernel, second, 0u, output, 0u) == MK_ERR_NOT_FOUND);
    return 0;
}

static void fill_pattern(uint8_t *buffer, size_t length, uint8_t seed) {
    size_t index;
    for (index = 0u; index < length; ++index) {
        buffer[index] = (uint8_t)(seed + (uint8_t)(index * 13u));
    }
}

static int test_filesystem_boundaries_and_alias(void) {
    mk_kernel_t kernel;
    uint8_t input[MK_FS_MAX_FILE_SIZE];
    uint8_t output[MK_FS_MAX_FILE_SIZE];
    uint8_t expected_alias[MK_FS_BLOCK_SIZE];
    size_t got = 0u;
    size_t size = 0u;
    int first_block;

    REQUIRE(mk_init(&kernel, 1u) == MK_OK);
    REQUIRE(mk_fs_create(&kernel, "/") == MK_ERR_INVALID);
    REQUIRE(mk_fs_create(&kernel, "/bad/name") == MK_ERR_INVALID);
    REQUIRE(mk_fs_create(&kernel, "/bad space") == MK_ERR_INVALID);
    REQUIRE(mk_fs_create(&kernel, "/alpha") == MK_OK);
    fill_pattern(input, sizeof(input), 7u);
    REQUIRE(mk_fs_write(&kernel, "/alpha", input, 131u) == MK_OK);
    REQUIRE(mk_fs_free_blocks(&kernel) == MK_FS_BLOCK_COUNT - 3u);
    memset(output, 0, sizeof(output));
    REQUIRE(mk_fs_read(&kernel, "/alpha", 61u, output, 75u, &got) == MK_OK);
    REQUIRE(got == 70u);
    REQUIRE(memcmp(output, &input[61], got) == 0);
    REQUIRE(mk_fs_read(&kernel, "/alpha", 999u, output, sizeof(output), &got) == MK_OK);
    REQUIRE(got == 0u);

    first_block = kernel.inodes[0].blocks[0];
    REQUIRE(first_block >= 0);
    memcpy(expected_alias, kernel.blocks[first_block], sizeof(expected_alias));
    REQUIRE(mk_fs_write(&kernel, "/alpha", kernel.blocks[first_block],
                        sizeof(expected_alias)) == MK_OK);
    REQUIRE(mk_fs_stat(&kernel, "/alpha", &size) == MK_OK);
    REQUIRE(size == sizeof(expected_alias));
    memset(output, 0, sizeof(output));
    REQUIRE(mk_fs_read(&kernel, "/alpha", 0u, output, sizeof(output), &got) == MK_OK);
    REQUIRE(got == sizeof(expected_alias));
    REQUIRE(memcmp(output, expected_alias, got) == 0);
    REQUIRE(mk_fs_free_blocks(&kernel) == MK_FS_BLOCK_COUNT - 1u);
    REQUIRE(mk_fs_write(&kernel, "/alpha", NULL, 0u) == MK_OK);
    REQUIRE(mk_fs_free_blocks(&kernel) == MK_FS_BLOCK_COUNT);
    REQUIRE(mk_fs_unlink(&kernel, "/alpha") == MK_OK);
    REQUIRE(mk_fs_stat(&kernel, "/alpha", &size) == MK_ERR_NOT_FOUND);
    return 0;
}

static int test_filesystem_enospc_is_atomic(void) {
    mk_kernel_t kernel;
    uint8_t old_data[MK_FS_BLOCK_SIZE];
    uint8_t fill[MK_FS_MAX_FILE_SIZE];
    uint8_t proposed[2u * MK_FS_BLOCK_SIZE];
    uint8_t output[MK_FS_BLOCK_SIZE];
    size_t got = 0u;
    size_t size = 0u;

    fill_pattern(old_data, sizeof(old_data), 3u);
    fill_pattern(fill, sizeof(fill), 11u);
    fill_pattern(proposed, sizeof(proposed), 91u);
    REQUIRE(mk_init(&kernel, 1u) == MK_OK);
    REQUIRE(mk_fs_create(&kernel, "/target") == MK_OK);
    REQUIRE(mk_fs_write(&kernel, "/target", old_data, sizeof(old_data)) == MK_OK);
    REQUIRE(mk_fs_create(&kernel, "/a") == MK_OK);
    REQUIRE(mk_fs_create(&kernel, "/b") == MK_OK);
    REQUIRE(mk_fs_create(&kernel, "/c") == MK_OK);
    REQUIRE(mk_fs_create(&kernel, "/d") == MK_OK);
    REQUIRE(mk_fs_write(&kernel, "/a", fill, sizeof(fill)) == MK_OK);
    REQUIRE(mk_fs_write(&kernel, "/b", fill, sizeof(fill)) == MK_OK);
    REQUIRE(mk_fs_write(&kernel, "/c", fill, sizeof(fill)) == MK_OK);
    REQUIRE(mk_fs_write(&kernel, "/d", fill, 3u * MK_FS_BLOCK_SIZE) == MK_OK);
    REQUIRE(mk_fs_free_blocks(&kernel) == 0u);
    REQUIRE(mk_fs_write(&kernel, "/target", proposed, sizeof(proposed)) ==
            MK_ERR_NO_SPACE);
    REQUIRE(mk_fs_stat(&kernel, "/target", &size) == MK_OK);
    REQUIRE(size == sizeof(old_data));
    REQUIRE(mk_fs_read(&kernel, "/target", 0u, output, sizeof(output), &got) == MK_OK);
    REQUIRE(got == sizeof(old_data));
    REQUIRE(memcmp(output, old_data, sizeof(old_data)) == 0);
    REQUIRE(mk_fs_free_blocks(&kernel) == 0u);
    REQUIRE(mk_fs_unlink(&kernel, "/b") == MK_OK);
    REQUIRE(mk_fs_free_blocks(&kernel) == MK_FS_DIRECT_BLOCKS);
    return 0;
}

static int test_fixed_resource_exhaustion(void) {
    mk_kernel_t kernel;
    mk_pid_t first;
    mk_pid_t second;
    mk_pid_t third;
    size_t page;
    size_t index;
    char path[8];

    REQUIRE(mk_init(&kernel, 1u) == MK_OK);
    first = mk_spawn(&kernel, keep_yielding, NULL);
    second = mk_spawn(&kernel, keep_yielding, NULL);
    third = mk_spawn(&kernel, keep_yielding, NULL);
    REQUIRE(first != 0u && second != 0u && third != 0u);
    for (page = 0u; page < MK_USER_PAGE_COUNT; ++page) {
        REQUIRE(mk_vm_map(&kernel, first, page * MK_PAGE_SIZE,
                          MK_VM_READ | MK_VM_WRITE) == MK_OK);
        REQUIRE(mk_vm_map(&kernel, second, page * MK_PAGE_SIZE,
                          MK_VM_READ | MK_VM_WRITE) == MK_OK);
    }
    REQUIRE(mk_vm_free_frames(&kernel) == 0u);
    REQUIRE(mk_vm_map(&kernel, third, 0u, MK_VM_READ) == MK_ERR_NO_SPACE);
    REQUIRE(mk_kill(&kernel, first, 0) == MK_OK);
    REQUIRE(mk_vm_free_frames(&kernel) == MK_USER_PAGE_COUNT);
    REQUIRE(mk_vm_map(&kernel, third, 0u, MK_VM_READ) == MK_OK);
    REQUIRE(mk_task(&kernel, third)->pages[0].frame == 0u);

    REQUIRE(mk_init(&kernel, 1u) == MK_OK);
    REQUIRE(mk_fs_create(&kernel, "/abcdefghijklmnopqrstuvw") == MK_OK);
    REQUIRE(mk_fs_unlink(&kernel, "/abcdefghijklmnopqrstuvw") == MK_OK);
    for (index = 0u; index < MK_MAX_FILES; ++index) {
        REQUIRE(snprintf(path, sizeof(path), "/f%zu", index) > 0);
        REQUIRE(mk_fs_create(&kernel, path) == MK_OK);
    }
    REQUIRE(mk_fs_create(&kernel, "/overflow") == MK_ERR_NO_SPACE);

    REQUIRE(mk_init(&kernel, 1u) == MK_OK);
    kernel.next_pid = UINT32_MAX;
    REQUIRE(mk_spawn(&kernel, keep_yielding, NULL) == UINT32_MAX);
    REQUIRE(mk_spawn(&kernel, keep_yielding, NULL) == 0u);
    return 0;
}

int main(void) {
    int failures = 0;
    failures += test_initialization_and_scheduler();
    failures += test_lifecycle_capacity_and_reap();
    failures += test_reentrant_callback_preserves_task_identity();
    failures += test_vm_translation_atomicity_and_cleanup();
    failures += test_filesystem_boundaries_and_alias();
    failures += test_filesystem_enospc_is_atomic();
    failures += test_fixed_resource_exhaustion();
    if (failures != 0) {
        fprintf(stderr, "%d sealed test group(s) failed\n", failures);
        return 1;
    }
    puts("sealed reference tests: 7 groups passed");
    return 0;
}
