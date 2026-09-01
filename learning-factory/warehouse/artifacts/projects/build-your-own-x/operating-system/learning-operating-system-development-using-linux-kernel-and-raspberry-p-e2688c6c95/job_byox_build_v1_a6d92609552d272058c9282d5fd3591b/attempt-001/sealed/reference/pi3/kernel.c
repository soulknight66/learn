#include <stdint.h>

#define PI3_UART0_BASE ((uintptr_t)0x3f201000u)
#define UART_DR_OFFSET ((uintptr_t)0x00u)
#define UART_FR_OFFSET ((uintptr_t)0x18u)
#define UART_FR_TX_FULL (1u << 5)

static volatile uint32_t *uart_register(uintptr_t offset)
{
    return (volatile uint32_t *)(PI3_UART0_BASE + offset);
}

static void uart_putc(char character)
{
    while ((*uart_register(UART_FR_OFFSET) & UART_FR_TX_FULL) != 0u) {
        __asm__ volatile("nop");
    }
    *uart_register(UART_DR_OFFSET) = (uint32_t)(uint8_t)character;
}

static void uart_puts(const char *text)
{
    while (*text != '\0') {
        if (*text == '\n') {
            uart_putc('\r');
        }
        uart_putc(*text);
        ++text;
    }
}

void pi_main(void)
{
    uart_puts("PebbleOS Pi 3 boot probe\n");
    for (;;) {
        __asm__ volatile("wfe");
    }
}
