#include <stdint.h>

#include "keyboard.h"
#include "test_common.h"

void run_keyboard_public_tests(void)
{
    keyboard_decoder_t decoder;
    key_event_t event = {KEY_CODE_NONE, 0, false, 0u};

    keyboard_decoder_init(&decoder);
    CHECK(keyboard_feed(&decoder, 0x1eu, &event));
    CHECK(event.code == KEY_CODE_CHARACTER);
    CHECK(event.pressed);
    CHECK(event.ascii == 'a');
    CHECK(event.modifiers == 0u);

    CHECK(keyboard_feed(&decoder, 0x9eu, &event));
    CHECK(!event.pressed);
    CHECK(event.ascii == 0);

    CHECK(keyboard_feed(&decoder, 0x2au, &event));
    CHECK(event.code == KEY_CODE_LEFT_SHIFT);
    CHECK((event.modifiers & KEY_MOD_SHIFT) != 0u);
    CHECK(keyboard_feed(&decoder, 0x1eu, &event));
    CHECK(event.ascii == 'A');
    CHECK(keyboard_feed(&decoder, 0xaau, &event));
    CHECK(event.code == KEY_CODE_LEFT_SHIFT);
    CHECK((event.modifiers & KEY_MOD_SHIFT) == 0u);

    CHECK(!keyboard_feed(&decoder, 0xe0u, &event));
    CHECK(keyboard_feed(&decoder, 0x48u, &event));
    CHECK(event.code == KEY_CODE_ARROW_UP);
    CHECK(event.pressed);
    CHECK(event.ascii == 0);
}

void run_queue_public_tests(void)
{
    keyboard_queue_t queue;
    key_event_t event;
    key_event_t output;
    unsigned int index;

    keyboard_queue_init(&queue);
    output.code = KEY_CODE_DELETE;
    CHECK(!keyboard_queue_pop(&queue, &output));
    CHECK(output.code == KEY_CODE_DELETE);

    event.code = KEY_CODE_CHARACTER;
    event.pressed = true;
    event.modifiers = 0u;
    for (index = 0u; index < KEYBOARD_QUEUE_CAPACITY - 1u; ++index) {
        event.ascii = (char)('a' + index);
        CHECK(keyboard_queue_push_isr(&queue, &event));
    }
    event.ascii = 'z';
    CHECK(!keyboard_queue_push_isr(&queue, &event));
    CHECK(keyboard_queue_dropped(&queue) == 1u);

    for (index = 0u; index < KEYBOARD_QUEUE_CAPACITY - 1u; ++index) {
        CHECK(keyboard_queue_pop(&queue, &output));
        CHECK(output.ascii == (char)('a' + index));
    }
    CHECK(!keyboard_queue_pop(&queue, &output));
}
