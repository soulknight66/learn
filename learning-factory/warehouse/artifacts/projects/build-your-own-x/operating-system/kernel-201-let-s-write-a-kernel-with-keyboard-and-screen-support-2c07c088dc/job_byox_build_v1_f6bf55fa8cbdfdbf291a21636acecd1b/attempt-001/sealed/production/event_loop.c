#include <stdbool.h>

#include "interrupts.h"
#include "terminal.h"

static void interrupts_disable(void)
{
    __asm__ volatile ("cli" : : : "memory");
}

static void interrupts_enable(void)
{
    __asm__ volatile ("sti" : : : "memory");
}

static void enable_and_halt(void)
{
    /* x86 recognizes an interrupt only after the instruction following STI. */
    __asm__ volatile ("sti\n\thlt" : : : "memory");
}

__attribute__((noreturn))
void single_core_event_loop(terminal_t *terminal)
{
    key_event_t event;

    for (;;) {
        bool have_event;

        interrupts_disable();
        have_event = input_next_event(&event);
        if (!have_event) {
            enable_and_halt();
            continue;
        }
        interrupts_enable();

        if (event.pressed && event.ascii != 0) {
            terminal_putc(terminal, event.ascii);
        }
    }
}
