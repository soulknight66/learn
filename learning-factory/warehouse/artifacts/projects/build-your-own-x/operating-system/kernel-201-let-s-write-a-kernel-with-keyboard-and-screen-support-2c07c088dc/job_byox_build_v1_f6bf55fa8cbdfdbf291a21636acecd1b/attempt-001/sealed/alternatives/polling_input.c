#include <stdbool.h>
#include <stdint.h>

#include "io.h"
#include "keyboard.h"

#define PS2_STATUS_PORT 0x64u
#define PS2_DATA_PORT 0x60u
#define PS2_OUTPUT_FULL 0x01u
#define PS2_AUXILIARY_DATA 0x20u
#define PS2_ERROR_BITS 0xc0u

bool polling_keyboard_try_event(keyboard_decoder_t *decoder, key_event_t *event_out)
{
    uint8_t status = io_in8(PS2_STATUS_PORT);

    if ((status & PS2_OUTPUT_FULL) == 0u) {
        return false;
    }
    if ((status & (PS2_AUXILIARY_DATA | PS2_ERROR_BITS)) != 0u) {
        (void)io_in8(PS2_DATA_PORT);
        return false;
    }
    return keyboard_feed(decoder, io_in8(PS2_DATA_PORT), event_out);
}
