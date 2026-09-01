#include <stddef.h>
#include <stdint.h>

static size_t console_cell;

void console_write(const char *text)
{
    volatile uint16_t *const video = (volatile uint16_t *)(uintptr_t)0xB8000u;
    const uint16_t style = (uint16_t)0x0Fu << 8;

    while (text != NULL && *text != '\0') {
        if (*text == '\n') {
            console_cell += 80u - (console_cell % 80u);
        } else {
            video[console_cell] = style | (uint8_t)*text;
            ++console_cell;
        }
        if (console_cell >= 80u * 25u) {
            console_cell = 0u;
        }
        ++text;
    }
}
