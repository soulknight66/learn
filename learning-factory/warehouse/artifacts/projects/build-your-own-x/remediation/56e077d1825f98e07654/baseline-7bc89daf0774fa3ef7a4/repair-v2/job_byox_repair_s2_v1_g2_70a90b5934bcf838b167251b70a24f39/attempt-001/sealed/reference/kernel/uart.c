#include "kernel/uart.h"

#include <stdint.h>

#define LF_UART0_BASE UINT32_C(0x101f1000)
#define LF_UART_DATA 0u
#define LF_UART_FLAGS 6u
#define LF_UART_TX_FULL (1u << 5)

static volatile uint32_t *uart_register(uint32_t word_offset) {
    return (volatile uint32_t *)(uintptr_t)(LF_UART0_BASE + word_offset * 4u);
}

void lf_uart_putc(char character) {
    if (character == '\n') {
        lf_uart_putc('\r');
    }
    while ((*uart_register(LF_UART_FLAGS) & LF_UART_TX_FULL) != 0u) {
    }
    *uart_register(LF_UART_DATA) = (uint32_t)(uint8_t)character;
}

void lf_uart_puts(const char *text) {
    if (text == (const char *)0) {
        return;
    }
    while (*text != '\0') {
        lf_uart_putc(*text);
        ++text;
    }
}
