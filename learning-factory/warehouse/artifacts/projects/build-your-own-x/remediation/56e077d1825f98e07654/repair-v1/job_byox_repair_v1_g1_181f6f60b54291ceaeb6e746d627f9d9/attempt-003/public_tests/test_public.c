#include "tinyarm.h"

#include <stdio.h>
#include <string.h>

#define CHECK(expression)                                                         \
    do {                                                                          \
        if (!(expression)) {                                                      \
            fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, #expression); \
            return 1;                                                             \
        }                                                                         \
    } while (0)

typedef struct {
    int label;
    int calls;
    int *trace;
    size_t *trace_length;
} trace_task_t;

static mk_step_result_t trace_step(struct mk_kernel *kernel, mk_pid_t pid,
                                   void *userdata) {
    trace_task_t *task = (trace_task_t *)userdata;
    (void)kernel;
    (void)pid;
    task->trace[*task->trace_length] = task->label;
    *task->trace_length += 1u;
    task->calls += 1;
    return task->calls == 2 ? MK_STEP_EXIT : MK_STEP_CONTINUE;
}

static mk_step_result_t idle_step(struct mk_kernel *kernel, mk_pid_t pid,
                                  void *userdata) {
    (void)kernel;
    (void)pid;
    (void)userdata;
    return MK_STEP_YIELD;
}

static int test_round_robin(void) {
    mk_kernel_t kernel;
    int trace[4] = {0, 0, 0, 0};
    size_t trace_length = 0u;
    trace_task_t first = {1, 0, trace, &trace_length};
    trace_task_t second = {2, 0, trace, &trace_length};
    mk_pid_t p1;
    mk_pid_t p2;

    CHECK(mk_init(&kernel, 1u) == MK_OK);
    p1 = mk_spawn(&kernel, trace_step, &first);
    p2 = mk_spawn(&kernel, trace_step, &second);
    CHECK(p1 == 1u);
    CHECK(p2 == 2u);
    CHECK(mk_run(&kernel, 8u) == 4u);
    CHECK(trace_length == 4u);
    CHECK(trace[0] == 1 && trace[1] == 2 && trace[2] == 1 && trace[3] == 2);
    CHECK(!mk_has_live_tasks(&kernel));
    CHECK(mk_task(&kernel, p1)->state == MK_TASK_ZOMBIE);
    CHECK(mk_task(&kernel, p2)->state == MK_TASK_ZOMBIE);
    return 0;
}

static int test_vm_permissions(void) {
    mk_kernel_t kernel;
    mk_pid_t pid;
    const unsigned char input[] = {0x10u, 0x20u, 0x30u, 0x40u};
    unsigned char output[sizeof(input)] = {0u};

    CHECK(mk_init(&kernel, 2u) == MK_OK);
    pid = mk_spawn(&kernel, idle_step, NULL);
    CHECK(pid != 0u);
    CHECK(mk_vm_map(&kernel, pid, 0u, MK_VM_READ | MK_VM_WRITE) == MK_OK);
    CHECK(mk_vm_write(&kernel, pid, 7u, input, sizeof(input)) == MK_OK);
    CHECK(mk_vm_read(&kernel, pid, 7u, output, sizeof(output)) == MK_OK);
    CHECK(memcmp(input, output, sizeof(input)) == 0);
    CHECK(mk_vm_map(&kernel, pid, MK_PAGE_SIZE, MK_VM_READ) == MK_OK);
    CHECK(mk_vm_write(&kernel, pid, MK_PAGE_SIZE, input, 1u) == MK_ERR_PERMISSION);
    return 0;
}

static int test_filesystem_round_trip(void) {
    mk_kernel_t kernel;
    const char message[] = "small deterministic file";
    char output[32] = {0};
    size_t size = 0u;
    size_t got = 0u;

    CHECK(mk_init(&kernel, 1u) == MK_OK);
    CHECK(mk_fs_create(&kernel, "/notes") == MK_OK);
    CHECK(mk_fs_create(&kernel, "/notes") == MK_ERR_EXISTS);
    CHECK(mk_fs_write(&kernel, "/notes", message, sizeof(message) - 1u) == MK_OK);
    CHECK(mk_fs_stat(&kernel, "/notes", &size) == MK_OK);
    CHECK(size == sizeof(message) - 1u);
    CHECK(mk_fs_read(&kernel, "/notes", 6u, output, 13u, &got) == MK_OK);
    CHECK(got == 13u);
    CHECK(memcmp(output, "deterministic", 13u) == 0);
    CHECK(mk_fs_unlink(&kernel, "/notes") == MK_OK);
    CHECK(mk_fs_stat(&kernel, "/notes", &size) == MK_ERR_NOT_FOUND);
    return 0;
}

int main(void) {
    int failures = 0;
    failures += test_round_robin();
    failures += test_vm_permissions();
    failures += test_filesystem_round_trip();
    if (failures != 0) {
        fprintf(stderr, "%d public test group(s) failed\n", failures);
        return 1;
    }
    puts("public tests: 3 groups passed");
    return 0;
}
