#include <stddef.h>
#include <stdint.h>

#define UART0_BASE 0x09000000u
#define UART_DATA 0x000u
#define UART_FLAGS 0x018u
#define UART_TX_FULL (1u << 5)
#define TASK_COUNT 2u
#define STACK_WORDS 256u

typedef enum {
    ARM_TASK_READY = 0,
    ARM_TASK_RUNNING = 1,
    ARM_TASK_ZOMBIE = 2
} arm_task_state_t;

typedef void (*arm_task_entry_t)(void);

typedef struct {
    uint32_t *stack_pointer;
    arm_task_entry_t entry;
    arm_task_state_t state;
    uint32_t stack[STACK_WORDS] __attribute__((aligned(8)));
} arm_task_t;

extern void arm_context_switch(uint32_t **old_stack_pointer,
                               uint32_t *new_stack_pointer);

static arm_task_t tasks[TASK_COUNT];
static uint32_t *scheduler_stack_pointer;
static int current_task = -1;

static volatile uint32_t *uart_register(uint32_t offset) {
    return (volatile uint32_t *)(uintptr_t)(UART0_BASE + offset);
}

static void uart_putc(char value) {
    while ((*uart_register(UART_FLAGS) & UART_TX_FULL) != 0u) {
    }
    *uart_register(UART_DATA) = (uint32_t)(uint8_t)value;
}

static void uart_puts(const char *text) {
    while (*text != '\0') {
        uart_putc(*text);
        ++text;
    }
}

static void arm_yield(void) {
    int slot = current_task;
    if (slot < 0 || slot >= (int)TASK_COUNT) {
        return;
    }
    if (tasks[slot].state == ARM_TASK_RUNNING) {
        tasks[slot].state = ARM_TASK_READY;
    }
    arm_context_switch(&tasks[slot].stack_pointer, scheduler_stack_pointer);
}

static void task_a(void) {
    unsigned int index;
    for (index = 0u; index < 4u; ++index) {
        uart_putc('A');
        arm_yield();
    }
}

static void task_b(void) {
    unsigned int index;
    for (index = 0u; index < 4u; ++index) {
        uart_putc('B');
        arm_yield();
    }
}

static void task_bootstrap(void) __attribute__((noreturn));

static void task_bootstrap(void) {
    int slot = current_task;
    if (slot >= 0 && slot < (int)TASK_COUNT) {
        tasks[slot].entry();
        tasks[slot].state = ARM_TASK_ZOMBIE;
        arm_yield();
    }
    for (;;) {
        __asm__ volatile("wfi");
    }
}

static void create_task(size_t slot, arm_task_entry_t entry) {
    uint32_t *top = &tasks[slot].stack[STACK_WORDS];
    size_t index;
    top = (uint32_t *)((uintptr_t)top & ~(uintptr_t)7u);
    top -= 9u;
    for (index = 0u; index < 8u; ++index) {
        top[index] = 0u;
    }
    top[8] = (uint32_t)(uintptr_t)task_bootstrap;
    tasks[slot].stack_pointer = top;
    tasks[slot].entry = entry;
    tasks[slot].state = ARM_TASK_READY;
}

void arm_kernel_main(void) {
    size_t cursor = TASK_COUNT - 1u;
    size_t dead = 0u;
    uart_puts("tinyarm: cooperative tasks\n");
    create_task(0u, task_a);
    create_task(1u, task_b);
    while (dead != TASK_COUNT) {
        size_t checked;
        dead = 0u;
        for (checked = 0u; checked < TASK_COUNT; ++checked) {
            cursor = (cursor + 1u) % TASK_COUNT;
            if (tasks[cursor].state == ARM_TASK_ZOMBIE) {
                dead += 1u;
            } else if (tasks[cursor].state == ARM_TASK_READY) {
                current_task = (int)cursor;
                tasks[cursor].state = ARM_TASK_RUNNING;
                arm_context_switch(&scheduler_stack_pointer,
                                   tasks[cursor].stack_pointer);
                current_task = -1;
            }
        }
    }
    uart_puts("\ntinyarm: done\n");
    for (;;) {
        __asm__ volatile("wfi");
    }
}
