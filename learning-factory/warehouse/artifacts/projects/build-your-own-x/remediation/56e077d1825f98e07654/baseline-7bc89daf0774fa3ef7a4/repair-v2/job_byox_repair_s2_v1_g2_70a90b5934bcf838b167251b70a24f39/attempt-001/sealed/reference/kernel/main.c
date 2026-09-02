#include "kernel/mmu.h"
#include "kernel/ramfs.h"
#include "kernel/runtime.h"
#include "kernel/uart.h"
#include "kernel/vm.h"

#include <stdbool.h>
#include <stdint.h>

static uint8_t task_stacks[2][1024] __attribute__((aligned(8)));
static lf_runtime_t runtime;

static bool bytes_equal(const uint8_t *left, const uint8_t *right,
                        uint32_t length) {
    uint32_t index;
    for (index = 0u; index < length; ++index) {
        if (left[index] != right[index]) {
            return false;
        }
    }
    return true;
}

static void marker_task(void *argument) {
    char marker = *(const char *)argument;
    uint32_t iteration;

    for (iteration = 0u; iteration < 3u; ++iteration) {
        lf_uart_putc(marker);
        lf_runtime_yield();
    }
}

static bool exercise_vm(void) {
    lf_frame_pool_t pool;
    lf_vm_space_t left;
    lf_vm_space_t right;
    uint32_t frame;
    uint32_t translated = 0u;

    if (!lf_frame_pool_init(&pool, UINT32_C(0x00200000), 8u)) {
        return false;
    }
    frame = lf_frame_alloc(&pool);
    if (frame == LF_INVALID_PADDR || !lf_frame_retain(&pool, frame)) {
        return false;
    }
    lf_vm_space_init(&left);
    lf_vm_space_init(&right);
    if (!lf_vm_map(&left, UINT32_C(0x40000000), frame,
                   LF_VM_READ | LF_VM_WRITE) ||
        !lf_vm_map(&right, UINT32_C(0x50000000), frame, LF_VM_READ) ||
        !lf_vm_translate(&left, UINT32_C(0x40000123), LF_VM_WRITE,
                         &translated) ||
        translated != frame + UINT32_C(0x123) ||
        lf_vm_translate(&right, UINT32_C(0x50000000), LF_VM_WRITE,
                        &translated)) {
        return false;
    }
    return lf_frame_release(&pool, frame) && lf_frame_release(&pool, frame) &&
           lf_frame_refcount(&pool, frame) == 0u;
}

static bool exercise_ramfs(void) {
    static const uint8_t message[] = {'k', 'e', 'r', 'n', 'e', 'l'};
    uint8_t output[sizeof(message)];
    uint32_t size = 0u;
    lf_ramfs_t filesystem;

    lf_ramfs_init(&filesystem);
    if (lf_ramfs_create(&filesystem, "motd") != LF_OK ||
        lf_ramfs_write(&filesystem, "motd", 0u, message,
                       (uint32_t)sizeof(message)) != (int32_t)sizeof(message) ||
        lf_ramfs_size(&filesystem, "motd", &size) != LF_OK ||
        size != (uint32_t)sizeof(message) ||
        lf_ramfs_read(&filesystem, "motd", 0u, output,
                      (uint32_t)sizeof(output)) != (int32_t)sizeof(output)) {
        return false;
    }
    return bytes_equal(message, output, (uint32_t)sizeof(message));
}

int kernel_main(void) {
    static const char marker_a = 'A';
    static const char marker_b = 'B';

    lf_uart_puts("LF-KERNEL boot\n");
    if (!lf_mmu_enable_identity()) {
        lf_uart_puts("FAIL mmu\n");
        return 1;
    }
    lf_uart_puts("mmu: on\n");

    if (!exercise_vm()) {
        lf_uart_puts("FAIL vm\n");
        return 2;
    }
    lf_uart_puts("vm: ok\n");

    if (!exercise_ramfs()) {
        lf_uart_puts("FAIL ramfs\n");
        return 3;
    }
    lf_uart_puts("ramfs: ok\n");

    lf_runtime_init(&runtime);
    if (lf_runtime_spawn(&runtime, marker_task, (void *)&marker_a,
                         task_stacks[0], sizeof(task_stacks[0])) == 0u ||
        lf_runtime_spawn(&runtime, marker_task, (void *)&marker_b,
                         task_stacks[1], sizeof(task_stacks[1])) == 0u) {
        lf_uart_puts("FAIL spawn\n");
        return 4;
    }
    lf_uart_puts("tasks: ");
    if (!lf_runtime_start(&runtime)) {
        lf_uart_puts("FAIL start\n");
        return 5;
    }
    lf_uart_puts("\nPASS reference\n");
    return 0;
}
