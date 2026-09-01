#include "terminal.h"

static uint16_t make_cell(char byte, uint8_t color)
{
    return (uint16_t)((uint16_t)color << 8) | (uint8_t)byte;
}

bool terminal_init(terminal_t *terminal,
                   volatile uint16_t *cells,
                   size_t width,
                   size_t height,
                   uint8_t color)
{
    if (terminal == NULL || cells == NULL || width == 0u || height == 0u) {
        return false;
    }

    terminal->cells = cells;
    terminal->width = width;
    terminal->height = height;
    terminal->row = 0u;
    terminal->column = 0u;
    terminal->color = color;
    terminal_clear(terminal);
    return true;
}

void terminal_clear(terminal_t *terminal)
{
    size_t index;

    /* TODO(student): blank exactly width * height cells with make_cell(' ', color). */
    (void)make_cell;
    for (index = 0u; index < terminal->width * terminal->height; ++index) {
        terminal->cells[index] = 0u;
    }
    terminal->row = 0u;
    terminal->column = 0u;
}

void terminal_putc(terminal_t *terminal, char byte)
{
    /* TODO(student): implement control bytes, wrapping, and bounded scrolling. */
    (void)terminal;
    (void)byte;
}

void terminal_write_n(terminal_t *terminal, const char *bytes, size_t length)
{
    size_t index;

    for (index = 0u; index < length; ++index) {
        terminal_putc(terminal, bytes[index]);
    }
}
