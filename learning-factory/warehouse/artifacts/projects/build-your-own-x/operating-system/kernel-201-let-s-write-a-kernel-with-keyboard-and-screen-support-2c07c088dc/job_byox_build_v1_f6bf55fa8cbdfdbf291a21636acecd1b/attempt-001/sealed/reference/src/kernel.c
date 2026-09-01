#include <stddef.h>
#include <stdint.h>

#include "interrupts.h"
#include "io.h"
#include "terminal.h"

void kernel_main(void)
{
    static const char greeting[] = "Keystroke Kernel Lab\nType to echo: ";
    terminal_t terminal;
    key_event_t event;

    (void)terminal_init(&terminal, (volatile uint16_t *)0xb8000u, 80u, 25u, 0x07u);
    terminal_write_n(&terminal, greeting, sizeof(greeting) - 1u);
    interrupts_init();
    cpu_interrupt_enable();

    for (;;) {
        while (input_next_event(&event)) {
            if (event.pressed && event.ascii != 0) {
                terminal_putc(&terminal, event.ascii);
            }
        }
        cpu_halt();
    }
}
