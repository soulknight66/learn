#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

#include "keyboard.h"
#include "terminal.h"

static unsigned int checks;
static unsigned int failures;
static uint32_t random_state = 0x6d2b79f5u;

#define CHECK(condition)                                                        \
    do {                                                                        \
        ++checks;                                                               \
        if (!(condition)) {                                                     \
            fprintf(stderr, "%s:%d: failed: %s\n", __FILE__, __LINE__,         \
                    #condition);                                                \
            ++failures;                                                         \
        }                                                                       \
    } while (0)

static uint32_t next_random(void)
{
    uint32_t value = random_state;
    value ^= value << 13;
    value ^= value >> 17;
    value ^= value << 5;
    random_state = value;
    return value;
}

static void stress_terminal(void)
{
    static const unsigned char bytes[] = {
        0x00u, 0x01u, '\b', '\t', '\n', '\r', 0x1fu, ' ', 'A', 'z', '~',
        0x7fu, 0x80u, 0xffu
    };
    uint16_t storage[47];
    terminal_t terminal;
    size_t width;
    size_t height;
    size_t index;

    for (height = 1u; height <= 5u; ++height) {
        for (width = 1u; width <= 9u; ++width) {
            size_t extent = width * height;
            for (index = 0u; index < 47u; ++index) {
                storage[index] = 0xc33cu;
            }
            CHECK(terminal_init(&terminal, &storage[1], width, height, 0x4fu));
            for (index = 0u; index < 2000u; ++index) {
                unsigned char byte = bytes[next_random() % sizeof(bytes)];
                terminal_putc(&terminal, (char)byte);
                CHECK(terminal.row < height);
                CHECK(terminal.column < width);
                CHECK(storage[0] == 0xc33cu);
                CHECK(storage[extent + 1u] == 0xc33cu);
            }
        }
    }
}

static uint8_t expected_modifiers(const keyboard_decoder_t *decoder)
{
    uint8_t value = 0u;
    if (decoder->left_shift || decoder->right_shift) value |= KEY_MOD_SHIFT;
    if (decoder->caps_lock) value |= KEY_MOD_CAPS;
    if (decoder->left_ctrl || decoder->right_ctrl) value |= KEY_MOD_CTRL;
    if (decoder->left_alt || decoder->right_alt) value |= KEY_MOD_ALT;
    return value;
}

static void stress_decoder(void)
{
    keyboard_decoder_t first;
    keyboard_decoder_t second;
    key_event_t first_event;
    key_event_t second_event;
    size_t index;

    keyboard_decoder_init(&first);
    keyboard_decoder_init(&second);
    for (index = 0u; index < 250000u; ++index) {
        uint8_t byte = (uint8_t)next_random();
        bool first_emitted = keyboard_feed(&first, byte, &first_event);
        bool second_emitted = keyboard_feed(&second, byte, &second_event);

        CHECK(first_emitted == second_emitted);
        CHECK(first.extended == second.extended);
        CHECK(first.pause_bytes_left == second.pause_bytes_left);
        if (first_emitted) {
            CHECK(first_event.code > KEY_CODE_NONE && first_event.code <= KEY_CODE_DELETE);
            CHECK(first_event.modifiers == expected_modifiers(&first));
            CHECK(first_event.code == second_event.code);
            CHECK(first_event.ascii == second_event.ascii);
            CHECK(first_event.pressed == second_event.pressed);
            if (!first_event.pressed) {
                CHECK(first_event.ascii == 0);
            }
            if (first_event.ascii != 0) {
                CHECK(first_event.pressed);
            }
        }
    }
}

static bool same_event(const key_event_t *left, const key_event_t *right)
{
    return left->code == right->code && left->ascii == right->ascii &&
           left->pressed == right->pressed && left->modifiers == right->modifiers;
}

static void stress_queue(void)
{
    key_event_t model[KEYBOARD_QUEUE_CAPACITY - 1u];
    size_t model_count = 0u;
    uint32_t expected_drops = 0u;
    keyboard_queue_t queue;
    size_t operation;

    keyboard_queue_init(&queue);
    for (operation = 0u; operation < 200000u; ++operation) {
        if ((next_random() & 3u) != 0u) {
            key_event_t event;
            bool accepted;
            event.code = (key_code_t)(1u + next_random() % KEY_CODE_DELETE);
            event.ascii = (char)next_random();
            event.pressed = (next_random() & 1u) != 0u;
            event.modifiers = (uint8_t)(next_random() & 0x0fu);
            accepted = keyboard_queue_push_isr(&queue, &event);
            if (model_count == KEYBOARD_QUEUE_CAPACITY - 1u) {
                CHECK(!accepted);
                ++expected_drops;
            } else {
                CHECK(accepted);
                model[model_count++] = event;
            }
        } else {
            key_event_t output = {KEY_CODE_DELETE, '!', true, 0xffu};
            key_event_t before = output;
            bool popped = keyboard_queue_pop(&queue, &output);
            if (model_count == 0u) {
                CHECK(!popped);
                CHECK(same_event(&output, &before));
            } else {
                size_t index;
                CHECK(popped);
                CHECK(same_event(&output, &model[0]));
                for (index = 1u; index < model_count; ++index) {
                    model[index - 1u] = model[index];
                }
                --model_count;
            }
        }
        CHECK(keyboard_queue_dropped(&queue) == expected_drops);
    }
}

int main(void)
{
    stress_terminal();
    stress_decoder();
    stress_queue();

    if (failures != 0u) {
        fprintf(stderr, "adversarial stress: FAIL (%u/%u)\n", failures, checks);
        return 1;
    }
    printf("adversarial stress: PASS (%u invariant checks)\n", checks);
    return 0;
}
