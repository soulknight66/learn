#include <stdint.h>

#include "terminal.h"
#include "test_common.h"

static uint16_t expected_cell(char byte, uint8_t color)
{
    return (uint16_t)((uint16_t)color << 8) | (uint8_t)byte;
}

void run_terminal_public_tests(void)
{
    uint16_t guarded[8];
    terminal_t terminal;
    size_t index;

    for (index = 0u; index < 8u; ++index) {
        guarded[index] = 0xa55au;
    }

    CHECK(!terminal_init(NULL, &guarded[1], 3u, 2u, 0x1fu));
    CHECK(!terminal_init(&terminal, NULL, 3u, 2u, 0x1fu));
    CHECK(terminal_init(&terminal, &guarded[1], 3u, 2u, 0x1fu));
    CHECK(guarded[0] == 0xa55au);
    CHECK(guarded[7] == 0xa55au);
    for (index = 1u; index <= 6u; ++index) {
        CHECK(guarded[index] == expected_cell(' ', 0x1fu));
    }

    terminal_write_n(&terminal, "ab\nc", 4u);
    CHECK(guarded[1] == expected_cell('a', 0x1fu));
    CHECK(guarded[2] == expected_cell('b', 0x1fu));
    CHECK(guarded[4] == expected_cell('c', 0x1fu));
    CHECK(terminal.row == 1u);
    CHECK(terminal.column == 1u);

    terminal_clear(&terminal);
    terminal_write_n(&terminal, "abcdefg", 7u);
    CHECK(guarded[1] == expected_cell('d', 0x1fu));
    CHECK(guarded[2] == expected_cell('e', 0x1fu));
    CHECK(guarded[3] == expected_cell('f', 0x1fu));
    CHECK(guarded[4] == expected_cell('g', 0x1fu));
    CHECK(guarded[0] == 0xa55au);
    CHECK(guarded[7] == 0xa55au);
}
