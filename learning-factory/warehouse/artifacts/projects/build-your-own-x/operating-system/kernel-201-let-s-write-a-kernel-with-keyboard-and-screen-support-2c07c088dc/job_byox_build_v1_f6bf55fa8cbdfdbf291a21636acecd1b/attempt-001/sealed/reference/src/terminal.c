#include "terminal.h"

static uint16_t make_cell(char byte, uint8_t color)
{
    return (uint16_t)((uint16_t)color << 8) | (uint8_t)byte;
}

static void blank_row(terminal_t *terminal, size_t row)
{
    size_t column;

    for (column = 0u; column < terminal->width; ++column) {
        terminal->cells[row * terminal->width + column] =
            make_cell(' ', terminal->color);
    }
}

static void scroll_if_needed(terminal_t *terminal)
{
    size_t row;
    size_t column;

    if (terminal->row < terminal->height) {
        return;
    }

    for (row = 1u; row < terminal->height; ++row) {
        for (column = 0u; column < terminal->width; ++column) {
            terminal->cells[(row - 1u) * terminal->width + column] =
                terminal->cells[row * terminal->width + column];
        }
    }
    blank_row(terminal, terminal->height - 1u);
    terminal->row = terminal->height - 1u;
}

static void put_printable(terminal_t *terminal, char byte)
{
    terminal->cells[terminal->row * terminal->width + terminal->column] =
        make_cell(byte, terminal->color);
    ++terminal->column;
    if (terminal->column == terminal->width) {
        terminal->column = 0u;
        ++terminal->row;
        scroll_if_needed(terminal);
    }
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
    size_t row;

    for (row = 0u; row < terminal->height; ++row) {
        blank_row(terminal, row);
    }
    terminal->row = 0u;
    terminal->column = 0u;
}

void terminal_putc(terminal_t *terminal, char byte)
{
    uint8_t value = (uint8_t)byte;

    switch (byte) {
    case '\n':
        terminal->column = 0u;
        ++terminal->row;
        scroll_if_needed(terminal);
        return;
    case '\r':
        terminal->column = 0u;
        return;
    case '\b':
        if (terminal->column != 0u) {
            --terminal->column;
            terminal->cells[terminal->row * terminal->width + terminal->column] =
                make_cell(' ', terminal->color);
        }
        return;
    case '\t': {
        size_t spaces = TERMINAL_TAB_WIDTH - (terminal->column % TERMINAL_TAB_WIDTH);
        size_t index;
        for (index = 0u; index < spaces; ++index) {
            put_printable(terminal, ' ');
        }
        return;
    }
    default:
        if (value >= 0x20u && value <= 0x7eu) {
            put_printable(terminal, byte);
        }
        return;
    }
}

void terminal_write_n(terminal_t *terminal, const char *bytes, size_t length)
{
    size_t index;

    for (index = 0u; index < length; ++index) {
        terminal_putc(terminal, bytes[index]);
    }
}
