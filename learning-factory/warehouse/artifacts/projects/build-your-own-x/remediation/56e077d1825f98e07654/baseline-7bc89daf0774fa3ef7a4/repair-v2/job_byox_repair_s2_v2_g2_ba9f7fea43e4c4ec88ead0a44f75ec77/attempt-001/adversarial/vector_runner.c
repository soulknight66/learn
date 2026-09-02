#include "kernel/ramfs.h"
#include "kernel/scheduler.h"
#include "kernel/vm.h"

#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define FAIL(message)                                                          \
    do {                                                                       \
        fprintf(stderr, "vector_runner: %s: %s\n", case_name, (message));     \
        return 1;                                                              \
    } while (false)

#define REQUIRE(condition)                                                     \
    do {                                                                       \
        if (!(condition)) {                                                    \
            FAIL(#condition);                                                  \
        }                                                                      \
    } while (false)

static const char *case_name;

static void no_op(void *argument) {
    (void)argument;
}

static bool parse_u32(const char *text, uint32_t *value) {
    char *end;
    unsigned long long parsed;

    errno = 0;
    end = (char *)0;
    parsed = strtoull(text, &end, 10);
    if (errno != 0 || end == text || *end != '\0' || parsed > UINT32_MAX) {
        return false;
    }
    *value = (uint32_t)parsed;
    return true;
}

static bool bytes_are_zero(const void *object, size_t size) {
    const unsigned char *bytes = (const unsigned char *)object;
    size_t index;

    for (index = 0u; index < size; ++index) {
        if (bytes[index] != 0u) {
            return false;
        }
    }
    return true;
}

static int pid_terminal(uint32_t next_pid) {
    lf_scheduler_t scheduler;

    lf_scheduler_init(&scheduler);
    scheduler.next_pid = next_pid;
    REQUIRE(lf_scheduler_spawn(&scheduler, no_op, (void *)0) == UINT32_MAX);
    REQUIRE(lf_scheduler_spawn(&scheduler, no_op, (void *)0) == 0u);
    REQUIRE(lf_scheduler_invariant(&scheduler));
    return 0;
}

static int pid_stale_reuse(uint32_t initial_next_pid) {
    lf_scheduler_t scheduler;
    uint32_t old_pid;
    uint32_t replacement_pid;
    int32_t old_slot;

    lf_scheduler_init(&scheduler);
    scheduler.next_pid = initial_next_pid;
    old_pid = lf_scheduler_spawn(&scheduler, no_op, (void *)0);
    REQUIRE(old_pid == 1u);
    old_slot = lf_scheduler_slot_of(&scheduler, old_pid);
    REQUIRE(old_slot == 0);
    REQUIRE(lf_scheduler_rotate(&scheduler) == old_pid);
    REQUIRE(lf_scheduler_exit_current(&scheduler) == 0u);
    REQUIRE(lf_scheduler_reap(&scheduler, old_pid));
    REQUIRE(lf_scheduler_slot_of(&scheduler, old_pid) == LF_NO_SLOT);
    replacement_pid = lf_scheduler_spawn(&scheduler, no_op, (void *)0);
    REQUIRE(replacement_pid == 2u);
    REQUIRE(lf_scheduler_slot_of(&scheduler, replacement_pid) == old_slot);
    return 0;
}

static int scheduler_duplicate(uint32_t first_slot, uint32_t duplicate_slot) {
    lf_scheduler_t scheduler;
    unsigned char snapshot[sizeof(scheduler)];
    uint32_t first;

    REQUIRE(first_slot == 0u && duplicate_slot == 1u);
    lf_scheduler_init(&scheduler);
    first = lf_scheduler_spawn(&scheduler, no_op, (void *)0);
    REQUIRE(first == 1u);
    REQUIRE(lf_scheduler_spawn(&scheduler, no_op, (void *)0) == 2u);
    scheduler.tasks[duplicate_slot].pid = scheduler.tasks[first_slot].pid;
    REQUIRE(!lf_scheduler_invariant(&scheduler));
    memcpy(snapshot, &scheduler, sizeof(snapshot));
    REQUIRE(lf_scheduler_rotate(&scheduler) == 0u);
    REQUIRE(memcmp(snapshot, &scheduler, sizeof(snapshot)) == 0);
    return 0;
}

static int scheduler_mismatch(uint32_t running_slot, uint32_t current_slot) {
    lf_scheduler_t scheduler;
    unsigned char snapshot[sizeof(scheduler)];

    REQUIRE(running_slot == 0u && current_slot == 1u);
    lf_scheduler_init(&scheduler);
    REQUIRE(lf_scheduler_spawn(&scheduler, no_op, (void *)0) == 1u);
    REQUIRE(lf_scheduler_spawn(&scheduler, no_op, (void *)0) == 2u);
    REQUIRE(lf_scheduler_rotate(&scheduler) == 1u);
    REQUIRE(scheduler.tasks[running_slot].state == LF_TASK_RUNNING);
    scheduler.current_slot = (int32_t)current_slot;
    REQUIRE(!lf_scheduler_invariant(&scheduler));
    memcpy(snapshot, &scheduler, sizeof(snapshot));
    REQUIRE(lf_scheduler_rotate(&scheduler) == 0u);
    REQUIRE(memcmp(snapshot, &scheduler, sizeof(snapshot)) == 0);
    return 0;
}

static int frame_exact_top(uint32_t base, uint32_t count) {
    lf_frame_pool_t pool;

    REQUIRE(base == UINT32_C(0xfffff000) && count == 1u);
    REQUIRE(lf_frame_pool_init(&pool, base, count));
    REQUIRE(lf_frame_alloc(&pool) == base);
    return 0;
}

static int frame_past_top(uint32_t base, uint32_t count) {
    lf_frame_pool_t pool;
    unsigned char snapshot[sizeof(pool)];

    REQUIRE(base == UINT32_C(0xfffff000) && count == 2u);
    memset(&pool, 0xa5, sizeof(pool));
    memcpy(snapshot, &pool, sizeof(snapshot));
    REQUIRE(!lf_frame_pool_init(&pool, base, count));
    REQUIRE(memcmp(snapshot, &pool, sizeof(snapshot)) == 0);
    return 0;
}

static int permission_subset(uint32_t mapped, uint32_t requested) {
    lf_vm_space_t space;
    uint32_t output = UINT32_C(0x13579bdf);

    lf_vm_space_init(&space);
    REQUIRE(lf_vm_map(&space, UINT32_C(0x40000000), UINT32_C(0x00100000),
                      (uint8_t)mapped));
    REQUIRE(!lf_vm_translate(&space, UINT32_C(0x40000020), (uint8_t)requested,
                             &output));
    REQUIRE(output == UINT32_C(0x13579bdf));
    return 0;
}

static int vm_final_byte(uint32_t virtual_base, uint32_t virtual_address,
                         uint32_t physical_base, uint32_t requested) {
    lf_vm_space_t space;
    uint32_t output = 0u;

    lf_vm_space_init(&space);
    REQUIRE(lf_vm_map(&space, virtual_base, physical_base, (uint8_t)requested));
    REQUIRE(lf_vm_translate(&space, virtual_address, (uint8_t)requested, &output));
    REQUIRE(output == UINT32_MAX);
    return 0;
}

static int ramfs_addition_wrap(uint32_t offset, uint32_t length) {
    lf_ramfs_t filesystem;
    unsigned char snapshot[sizeof(filesystem)];
    uint8_t source[2] = {1u, 2u};

    REQUIRE(length == 2u);
    lf_ramfs_init(&filesystem);
    REQUIRE(lf_ramfs_create(&filesystem, "wrap") == LF_OK);
    memcpy(snapshot, &filesystem, sizeof(snapshot));
    REQUIRE(lf_ramfs_write(&filesystem, "wrap", offset, source, length) ==
            LF_ERR_RANGE);
    REQUIRE(memcmp(snapshot, &filesystem, sizeof(snapshot)) == 0);
    return 0;
}

static int ramfs_full(uint32_t capacity) {
    static const char *const names[LF_RAMFS_MAX_FILES] = {
        "a", "b", "c", "d", "e", "f", "g", "h"
    };
    lf_ramfs_t filesystem;
    unsigned char snapshot[sizeof(filesystem)];
    uint32_t index;

    REQUIRE(capacity == LF_RAMFS_MAX_FILES);
    lf_ramfs_init(&filesystem);
    for (index = 0u; index < capacity; ++index) {
        REQUIRE(lf_ramfs_create(&filesystem, names[index]) == LF_OK);
    }
    memcpy(snapshot, &filesystem, sizeof(snapshot));
    REQUIRE(lf_ramfs_create(&filesystem, "full") == LF_ERR_NO_SPACE);
    REQUIRE(memcmp(snapshot, &filesystem, sizeof(snapshot)) == 0);
    return 0;
}

static int null_zero_read(uint32_t length) {
    lf_ramfs_t filesystem;

    REQUIRE(length == 0u);
    lf_ramfs_init(&filesystem);
    REQUIRE(lf_ramfs_create(&filesystem, "empty") == LF_OK);
    REQUIRE(lf_ramfs_read(&filesystem, "empty", 0u, (void *)0, length) == 0);
    return 0;
}

static int ramfs_scrub_reuse(uint32_t payload_byte, uint32_t length) {
    lf_ramfs_t filesystem;
    uint8_t payload[LF_RAMFS_FILE_MAX];
    uint32_t index;

    REQUIRE(payload_byte <= UINT8_MAX && length == LF_RAMFS_FILE_MAX);
    memset(payload, (int)payload_byte, sizeof(payload));
    lf_ramfs_init(&filesystem);
    REQUIRE(lf_ramfs_create(&filesystem, "victim") == LF_OK);
    REQUIRE(lf_ramfs_write(&filesystem, "victim", 0u, payload, length) ==
            (int32_t)length);
    REQUIRE(lf_ramfs_unlink(&filesystem, "victim") == LF_OK);
    REQUIRE(bytes_are_zero(&filesystem.files[0], sizeof(filesystem.files[0])));
    REQUIRE(lf_ramfs_create(&filesystem, "replacement") == LF_OK);
    REQUIRE(filesystem.files[0].size == 0u);
    for (index = 0u; index < LF_RAMFS_FILE_MAX; ++index) {
        REQUIRE(filesystem.files[0].data[index] == 0u);
    }
    return 0;
}

int main(int argc, char **argv) {
    uint32_t values[4];
    int index;

    if (argc < 2) {
        fputs("vector_runner: missing case\n", stderr);
        return 2;
    }
    case_name = argv[1];
    if (argc > 6) {
        FAIL("too many arguments");
    }
    for (index = 2; index < argc; ++index) {
        if (!parse_u32(argv[index], &values[index - 2])) {
            FAIL("invalid unsigned argument");
        }
    }

    if (strcmp(case_name, "pid_terminal_value") == 0 && argc == 3) {
        return pid_terminal(values[0]);
    }
    if (strcmp(case_name, "pid_stale_reuse") == 0 && argc == 3) {
        return pid_stale_reuse(values[0]);
    }
    if (strcmp(case_name, "scheduler_duplicate_pid") == 0 && argc == 4) {
        return scheduler_duplicate(values[0], values[1]);
    }
    if (strcmp(case_name, "scheduler_current_mismatch") == 0 && argc == 4) {
        return scheduler_mismatch(values[0], values[1]);
    }
    if (strcmp(case_name, "frame_exact_top") == 0 && argc == 4) {
        return frame_exact_top(values[0], values[1]);
    }
    if (strcmp(case_name, "frame_past_top") == 0 && argc == 4) {
        return frame_past_top(values[0], values[1]);
    }
    if (strcmp(case_name, "permission_subset") == 0 && argc == 4) {
        return permission_subset(values[0], values[1]);
    }
    if (strcmp(case_name, "vm_final_physical_byte") == 0 && argc == 6) {
        return vm_final_byte(values[0], values[1], values[2], values[3]);
    }
    if (strcmp(case_name, "ramfs_addition_wrap") == 0 && argc == 4) {
        return ramfs_addition_wrap(values[0], values[1]);
    }
    if (strcmp(case_name, "ramfs_full_capacity_create") == 0 && argc == 3) {
        return ramfs_full(values[0]);
    }
    if (strcmp(case_name, "null_zero_read") == 0 && argc == 3) {
        return null_zero_read(values[0]);
    }
    if (strcmp(case_name, "ramfs_scrub_reuse") == 0 && argc == 4) {
        return ramfs_scrub_reuse(values[0], values[1]);
    }
    FAIL("unknown case or wrong argument count");
}
