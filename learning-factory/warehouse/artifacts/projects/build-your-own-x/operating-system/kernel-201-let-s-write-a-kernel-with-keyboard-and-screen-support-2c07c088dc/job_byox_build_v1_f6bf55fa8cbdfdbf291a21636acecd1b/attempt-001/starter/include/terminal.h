#ifndef KEYSTROKE_KERNEL_TERMINAL_H
#define KEYSTROKE_KERNEL_TERMINAL_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define TERMINAL_TAB_WIDTH 4u

typedef struct terminal {
    volatile uint16_t *cells;
    size_t width;
    size_t height;
    size_t row;
    size_t column;
    uint8_t color;
} terminal_t;

bool terminal_init(terminal_t *terminal,
                   volatile uint16_t *cells,
                   size_t width,
                   size_t height,
                   uint8_t color);
void terminal_clear(terminal_t *terminal);
void terminal_putc(terminal_t *terminal, char byte);
void terminal_write_n(terminal_t *terminal, const char *bytes, size_t length);

#endif
