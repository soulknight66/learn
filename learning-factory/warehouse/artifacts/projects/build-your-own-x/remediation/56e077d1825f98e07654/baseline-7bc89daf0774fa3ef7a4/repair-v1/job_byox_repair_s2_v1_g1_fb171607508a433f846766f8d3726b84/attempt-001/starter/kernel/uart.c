#include "kernel/uart.h"

/* Stage 1: implement bounded polling against the PL011 registers documented in
 * environment/README.md. */
void lf_uart_putc(char character) {
    (void)character;
}

void lf_uart_puts(const char *text) {
    (void)text;
}
