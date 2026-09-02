#include "kernel/runtime.h"
#include "kernel/uart.h"

#include <stdbool.h>
#include <stdint.h>

static lf_runtime_t runtime;
static uint8_t outer_stack[1024] __attribute__((aligned(8)));
static uint8_t replacement_stack[1024] __attribute__((aligned(8)));
static uint32_t outer_pid;
static volatile uint32_t phase;
static volatile uint32_t replacement_runs;
static volatile bool setup_failed;

static void replacement_task(void *argument) {
    (void)argument;
    ++replacement_runs;
    if (phase == 1u) {
        lf_uart_puts("REPLACEMENT-RAN\n");
    } else {
        lf_uart_puts("RETURN-REPLACEMENT-RAN\n");
    }
}

static void outer_task(void *argument) {
    uint32_t replacement_pid;

    (void)argument;
    if (lf_scheduler_exit_current(&runtime.scheduler) != 0u ||
        !lf_scheduler_reap(&runtime.scheduler, outer_pid)) {
        setup_failed = true;
        lf_uart_puts("PROBE-SETUP-FAILED\n");
        return;
    }

    replacement_pid = lf_runtime_spawn(&runtime, replacement_task, (void *)0,
                                        replacement_stack,
                                        sizeof(replacement_stack));
    if (replacement_pid == 0u ||
        lf_scheduler_rotate(&runtime.scheduler) != replacement_pid) {
        setup_failed = true;
        lf_uart_puts("PROBE-SETUP-FAILED\n");
        return;
    }

    if (phase == 1u) {
        lf_runtime_yield();
        lf_uart_puts("OUTER-RETURN\n");
    }
}

static bool run_phase(uint32_t selected_phase) {
    phase = selected_phase;
    lf_runtime_init(&runtime);
    outer_pid = lf_runtime_spawn(&runtime, outer_task, (void *)0, outer_stack,
                                 sizeof(outer_stack));
    return outer_pid != 0u && lf_runtime_start(&runtime);
}

int kernel_main(void) {
    lf_uart_puts("REENTRANT-PROBE\n");

    if (!run_phase(1u) || setup_failed || replacement_runs != 1u) {
        lf_uart_puts("BUG-STALE-RETURN-KILLED-REPLACEMENT\n");
        return 1;
    }
    if (!run_phase(2u) || setup_failed || replacement_runs != 2u) {
        lf_uart_puts("BUG-STALE-RETURN-KILLED-REPLACEMENT\n");
        return 2;
    }

    lf_uart_puts("NO-BUG\n");
    return 0;
}
