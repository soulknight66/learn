#include <stddef.h>
#include <stdint.h>

#include "terminal.h"
#include "test.h"

static uint16_t cell(char byte, uint8_t color)
{
    return (uint16_t)((uint16_t)color << 8) | (uint8_t)byte;
}

static void test_init_and_clear(void)
{
    terminal_t terminal = {0};
    uint16_t guarded[8];
    size_t index;

    for (index = 0u; index < 8u; ++index) {
        guarded[index] = 0xa55au;
    }
    CHECK(!terminal_init(NULL, &guarded[1], 3u, 2u, 0x1fu));
    CHECK(!terminal_init(&terminal, NULL, 3u, 2u, 0x1fu));
    CHECK(!terminal_init(&terminal, &guarded[1], 0u, 2u, 0x1fu));
    CHECK(!terminal_init(&terminal, &guarded[1], 3u, 0u, 0x1fu));
    CHECK(terminal_init(&terminal, &guarded[1], 3u, 2u, 0x1fu));
    CHECK(terminal.cells == &guarded[1]);
    CHECK(terminal.width == 3u && terminal.height == 2u);
    CHECK(terminal.row == 0u && terminal.column == 0u);
    CHECK(terminal.color == 0x1fu);
    CHECK(guarded[0] == 0xa55au && guarded[7] == 0xa55au);
    for (index = 1u; index <= 6u; ++index) {
        CHECK(guarded[index] == cell(' ', 0x1fu));
    }

    guarded[3] = cell('x', 0x02u);
    terminal.row = 1u;
    terminal.column = 2u;
    terminal_clear(&terminal);
    CHECK(terminal.row == 0u && terminal.column == 0u);
    CHECK(guarded[3] == cell(' ', 0x1fu));
    CHECK(guarded[0] == 0xa55au && guarded[7] == 0xa55au);
}

static void test_controls(void)
{
    terminal_t terminal;
    uint16_t cells[16];

    CHECK(terminal_init(&terminal, cells, 8u, 2u, 0x07u));
    terminal_write_n(&terminal, "A\tB", 3u);
    CHECK(terminal.row == 0u && terminal.column == 5u);
    CHECK(cells[0] == cell('A', 0x07u));
    CHECK(cells[1] == cell(' ', 0x07u));
    CHECK(cells[3] == cell(' ', 0x07u));
    CHECK(cells[4] == cell('B', 0x07u));

    terminal_putc(&terminal, '\b');
    CHECK(terminal.column == 4u);
    CHECK(cells[4] == cell(' ', 0x07u));
    terminal_putc(&terminal, '\r');
    terminal_putc(&terminal, 'Z');
    CHECK(cells[0] == cell('Z', 0x07u));
    CHECK(terminal.column == 1u);

    terminal_putc(&terminal, '\n');
    CHECK(terminal.row == 1u && terminal.column == 0u);
    terminal_putc(&terminal, '\b');
    CHECK(terminal.row == 1u && terminal.column == 0u);

    terminal_putc(&terminal, '\x01');
    terminal_putc(&terminal, '\x7f');
    terminal_putc(&terminal, (char)0x80u);
    CHECK(terminal.row == 1u && terminal.column == 0u);
}

static void test_wrap_scroll_and_guards(void)
{
    terminal_t terminal;
    uint16_t guarded[8];
    size_t index;

    for (index = 0u; index < 8u; ++index) {
        guarded[index] = 0xbeefu;
    }
    CHECK(terminal_init(&terminal, &guarded[1], 3u, 2u, 0x2eu));
    terminal_write_n(&terminal, "abcdef", 6u);
    CHECK(terminal.row == 1u && terminal.column == 0u);
    CHECK(guarded[1] == cell('d', 0x2eu));
    CHECK(guarded[2] == cell('e', 0x2eu));
    CHECK(guarded[3] == cell('f', 0x2eu));
    CHECK(guarded[4] == cell(' ', 0x2eu));

    terminal_write_n(&terminal, "gh\n", 3u);
    CHECK(guarded[1] == cell('g', 0x2eu));
    CHECK(guarded[2] == cell('h', 0x2eu));
    CHECK(guarded[3] == cell(' ', 0x2eu));
    CHECK(guarded[4] == cell(' ', 0x2eu));
    CHECK(terminal.row == 1u && terminal.column == 0u);
    CHECK(guarded[0] == 0xbeefu && guarded[7] == 0xbeefu);
}

static void test_narrow_terminal_tab(void)
{
    terminal_t terminal;
    uint16_t cells[6];

    CHECK(terminal_init(&terminal, cells, 3u, 2u, 0x07u));
    terminal_putc(&terminal, '\t');
    CHECK(terminal.row == 1u && terminal.column == 1u);
    CHECK(cells[0] == cell(' ', 0x07u));
    CHECK(cells[3] == cell(' ', 0x07u));
}

static void test_single_cell_scroll(void)
{
    terminal_t terminal;
    uint16_t one_cell;

    CHECK(terminal_init(&terminal, &one_cell, 1u, 1u, 0x70u));
    terminal_putc(&terminal, 'X');
    CHECK(one_cell == cell(' ', 0x70u));
    CHECK(terminal.row == 0u && terminal.column == 0u);
}

void run_terminal_tests(void)
{
    test_init_and_clear();
    test_controls();
    test_wrap_scroll_and_guards();
    test_narrow_terminal_tab();
    test_single_cell_scroll();
}
