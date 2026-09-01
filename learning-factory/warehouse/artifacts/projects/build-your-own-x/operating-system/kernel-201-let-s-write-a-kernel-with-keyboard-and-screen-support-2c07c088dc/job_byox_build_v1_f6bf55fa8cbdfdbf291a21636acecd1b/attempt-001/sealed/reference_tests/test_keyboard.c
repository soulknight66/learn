#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "keyboard.h"
#include "test.h"

static key_event_t feed_event(keyboard_decoder_t *decoder, uint8_t byte)
{
    key_event_t event = {KEY_CODE_NONE, 0, false, 0u};
    CHECK(keyboard_feed(decoder, byte, &event));
    return event;
}

static void test_letters_and_releases(void)
{
    static const uint8_t scans[] = {
        0x1e, 0x30, 0x2e, 0x20, 0x12, 0x21, 0x22, 0x23, 0x17,
        0x24, 0x25, 0x26, 0x32, 0x31, 0x18, 0x19, 0x10, 0x13,
        0x1f, 0x14, 0x16, 0x2f, 0x11, 0x2d, 0x15, 0x2c
    };
    keyboard_decoder_t decoder;
    key_event_t event;
    size_t index;

    keyboard_decoder_init(&decoder);
    for (index = 0u; index < sizeof(scans); ++index) {
        event = feed_event(&decoder, scans[index]);
        CHECK(event.code == KEY_CODE_CHARACTER);
        CHECK(event.ascii == (char)('a' + index));
        CHECK(event.pressed);
        event = feed_event(&decoder, (uint8_t)(scans[index] | 0x80u));
        CHECK(event.code == KEY_CODE_CHARACTER);
        CHECK(event.ascii == 0);
        CHECK(!event.pressed);
    }
}

static void test_shift_caps_and_symbols(void)
{
    static const uint8_t symbol_scans[] = {
        0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09,
        0x0a, 0x0b, 0x0c, 0x0d, 0x1a, 0x1b, 0x27, 0x28,
        0x29, 0x2b, 0x33, 0x34, 0x35, 0x39
    };
    static const char unshifted_symbols[] = "1234567890-=[];'`\\,./ ";
    static const char shifted_symbols[] = "!@#$%^&*()_+{}:\"~|<>? ";
    keyboard_decoder_t decoder;
    key_event_t event;
    size_t index;

    keyboard_decoder_init(&decoder);
    event = feed_event(&decoder, 0x2au);
    CHECK(event.code == KEY_CODE_LEFT_SHIFT);
    CHECK(event.modifiers == KEY_MOD_SHIFT);
    event = feed_event(&decoder, 0x36u);
    CHECK(event.code == KEY_CODE_RIGHT_SHIFT);
    event = feed_event(&decoder, 0xaau);
    CHECK((event.modifiers & KEY_MOD_SHIFT) != 0u);
    event = feed_event(&decoder, 0x1eu);
    CHECK(event.ascii == 'A');
    event = feed_event(&decoder, 0xb6u);
    CHECK((event.modifiers & KEY_MOD_SHIFT) == 0u);

    event = feed_event(&decoder, 0x3au);
    CHECK(event.code == KEY_CODE_CAPS_LOCK);
    CHECK(event.modifiers == KEY_MOD_CAPS);
    CHECK(feed_event(&decoder, 0x1eu).ascii == 'A');
    (void)feed_event(&decoder, 0x2au);
    CHECK(feed_event(&decoder, 0x1eu).ascii == 'a');
    (void)feed_event(&decoder, 0xaau);
    event = feed_event(&decoder, 0xbau);
    CHECK((event.modifiers & KEY_MOD_CAPS) != 0u);
    (void)feed_event(&decoder, 0x3au);
    CHECK(feed_event(&decoder, 0x1eu).ascii == 'a');

    for (index = 0u; index < sizeof(symbol_scans); ++index) {
        CHECK(feed_event(&decoder, symbol_scans[index]).ascii == unshifted_symbols[index]);
    }
    (void)feed_event(&decoder, 0x2au);
    for (index = 0u; index < sizeof(symbol_scans); ++index) {
        CHECK(feed_event(&decoder, symbol_scans[index]).ascii == shifted_symbols[index]);
    }
}

static void test_special_extended_and_prefix_reset(void)
{
    static const uint8_t arrow_scans[] = {0x48u, 0x50u, 0x4bu, 0x4du, 0x53u};
    static const key_code_t arrow_codes[] = {
        KEY_CODE_ARROW_UP, KEY_CODE_ARROW_DOWN, KEY_CODE_ARROW_LEFT,
        KEY_CODE_ARROW_RIGHT, KEY_CODE_DELETE
    };
    keyboard_decoder_t decoder;
    key_event_t event;
    size_t index;

    keyboard_decoder_init(&decoder);
    CHECK(feed_event(&decoder, 0x01u).ascii == '\x1b');
    CHECK(feed_event(&decoder, 0x0eu).ascii == '\b');
    CHECK(feed_event(&decoder, 0x0fu).ascii == '\t');
    CHECK(feed_event(&decoder, 0x1cu).ascii == '\n');

    for (index = 0u; index < sizeof(arrow_scans); ++index) {
        CHECK(!keyboard_feed(&decoder, 0xe0u, &event));
        event = feed_event(&decoder, arrow_scans[index]);
        CHECK(event.code == arrow_codes[index]);
        CHECK(event.ascii == 0 && event.pressed);
        CHECK(!keyboard_feed(&decoder, 0xe0u, &event));
        event = feed_event(&decoder, (uint8_t)(arrow_scans[index] | 0x80u));
        CHECK(event.code == arrow_codes[index]);
        CHECK(!event.pressed);
    }

    CHECK(!keyboard_feed(&decoder, 0xe0u, &event));
    CHECK(!keyboard_feed(&decoder, 0x20u, &event));
    CHECK(feed_event(&decoder, 0x1eu).ascii == 'a');

    CHECK(!keyboard_feed(&decoder, 0xe0u, &event));
    event = feed_event(&decoder, 0x1du);
    CHECK(event.code == KEY_CODE_RIGHT_CTRL);
    CHECK((event.modifiers & KEY_MOD_CTRL) != 0u);
    CHECK(!keyboard_feed(&decoder, 0xe0u, &event));
    event = feed_event(&decoder, 0x9du);
    CHECK((event.modifiers & KEY_MOD_CTRL) == 0u);
}

static void test_pause_and_unsupported(void)
{
    static const uint8_t pause_tail[] = {0x1du, 0x45u, 0xe1u, 0x9du, 0xc5u};
    keyboard_decoder_t decoder;
    key_event_t event = {KEY_CODE_DELETE, '!', true, 0xffu};
    size_t index;

    keyboard_decoder_init(&decoder);
    CHECK(!keyboard_feed(NULL, 0x1eu, &event));
    CHECK(!keyboard_feed(&decoder, 0x1eu, NULL));
    CHECK(!keyboard_feed(&decoder, 0x00u, &event));
    CHECK(event.code == KEY_CODE_DELETE && event.ascii == '!');

    CHECK(!keyboard_feed(&decoder, 0xe1u, &event));
    for (index = 0u; index < sizeof(pause_tail); ++index) {
        CHECK(!keyboard_feed(&decoder, pause_tail[index], &event));
    }
    CHECK(feed_event(&decoder, 0x1eu).ascii == 'a');
}

static void test_ctrl_alt_state(void)
{
    keyboard_decoder_t decoder;
    key_event_t event;

    keyboard_decoder_init(&decoder);
    event = feed_event(&decoder, 0x1du);
    CHECK(event.code == KEY_CODE_LEFT_CTRL);
    CHECK(event.modifiers == KEY_MOD_CTRL);
    event = feed_event(&decoder, 0x38u);
    CHECK(event.code == KEY_CODE_LEFT_ALT);
    CHECK(event.modifiers == (KEY_MOD_CTRL | KEY_MOD_ALT));
    event = feed_event(&decoder, 0x9du);
    CHECK(event.modifiers == KEY_MOD_ALT);
    event = feed_event(&decoder, 0xb8u);
    CHECK(event.modifiers == 0u);
}

static key_event_t numbered_event(unsigned int number)
{
    key_event_t event;
    event.code = KEY_CODE_CHARACTER;
    event.ascii = (char)number;
    event.pressed = true;
    event.modifiers = (uint8_t)(number >> 8);
    return event;
}

static void test_queue(void)
{
    keyboard_queue_t queue;
    key_event_t input;
    key_event_t output;
    unsigned int index;

    keyboard_queue_init(&queue);
    output = numbered_event(999u);
    CHECK(!keyboard_queue_pop(&queue, &output));
    CHECK(output.ascii == numbered_event(999u).ascii);

    for (index = 0u; index < KEYBOARD_QUEUE_CAPACITY - 1u; ++index) {
        input = numbered_event(index);
        CHECK(keyboard_queue_push_isr(&queue, &input));
    }
    input = numbered_event(100u);
    CHECK(!keyboard_queue_push_isr(&queue, &input));
    input = numbered_event(101u);
    CHECK(!keyboard_queue_push_isr(&queue, &input));
    CHECK(keyboard_queue_dropped(&queue) == 2u);

    for (index = 0u; index < 7u; ++index) {
        CHECK(keyboard_queue_pop(&queue, &output));
        CHECK((unsigned char)output.ascii == index);
    }
    for (index = 15u; index < 22u; ++index) {
        input = numbered_event(index);
        CHECK(keyboard_queue_push_isr(&queue, &input));
    }
    for (index = 7u; index < 22u; ++index) {
        CHECK(keyboard_queue_pop(&queue, &output));
        CHECK((unsigned char)output.ascii == index);
    }
    CHECK(!keyboard_queue_pop(&queue, &output));

    input = numbered_event(42u);
    CHECK(keyboard_queue_push_isr(&queue, &input));
    CHECK(keyboard_queue_pop(&queue, &output));
    CHECK((unsigned char)output.ascii == 42u);
    CHECK(keyboard_queue_dropped(&queue) == 2u);

    keyboard_queue_init(&queue);
    CHECK(keyboard_queue_dropped(&queue) == 0u);
    CHECK(!keyboard_queue_pop(&queue, &output));
}

void run_keyboard_tests(void)
{
    test_letters_and_releases();
    test_shift_caps_and_symbols();
    test_special_extended_and_prefix_reset();
    test_pause_and_unsupported();
    test_ctrl_alt_state();
    test_queue();
}
