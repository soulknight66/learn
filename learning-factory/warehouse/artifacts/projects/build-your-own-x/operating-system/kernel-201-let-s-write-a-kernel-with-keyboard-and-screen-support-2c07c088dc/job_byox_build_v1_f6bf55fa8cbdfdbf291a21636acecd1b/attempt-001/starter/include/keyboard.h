#ifndef KEYSTROKE_KERNEL_KEYBOARD_H
#define KEYSTROKE_KERNEL_KEYBOARD_H

#include <stdbool.h>
#include <stdint.h>

#define KEYBOARD_QUEUE_CAPACITY 16u

typedef enum key_code {
    KEY_CODE_NONE = 0,
    KEY_CODE_ESCAPE,
    KEY_CODE_BACKSPACE,
    KEY_CODE_TAB,
    KEY_CODE_ENTER,
    KEY_CODE_LEFT_SHIFT,
    KEY_CODE_RIGHT_SHIFT,
    KEY_CODE_LEFT_CTRL,
    KEY_CODE_RIGHT_CTRL,
    KEY_CODE_LEFT_ALT,
    KEY_CODE_RIGHT_ALT,
    KEY_CODE_CAPS_LOCK,
    KEY_CODE_CHARACTER,
    KEY_CODE_ARROW_UP,
    KEY_CODE_ARROW_DOWN,
    KEY_CODE_ARROW_LEFT,
    KEY_CODE_ARROW_RIGHT,
    KEY_CODE_DELETE
} key_code_t;

enum keyboard_modifier {
    KEY_MOD_SHIFT = 1u << 0,
    KEY_MOD_CAPS = 1u << 1,
    KEY_MOD_CTRL = 1u << 2,
    KEY_MOD_ALT = 1u << 3
};

typedef struct key_event {
    key_code_t code;
    char ascii;
    bool pressed;
    uint8_t modifiers;
} key_event_t;

typedef struct keyboard_decoder {
    bool extended;
    bool left_shift;
    bool right_shift;
    bool left_ctrl;
    bool right_ctrl;
    bool left_alt;
    bool right_alt;
    bool caps_lock;
    uint8_t pause_bytes_left;
} keyboard_decoder_t;

typedef struct keyboard_queue {
    key_event_t events[KEYBOARD_QUEUE_CAPACITY];
    uint8_t head;
    uint8_t tail;
    uint32_t dropped;
} keyboard_queue_t;

void keyboard_decoder_init(keyboard_decoder_t *decoder);
bool keyboard_feed(keyboard_decoder_t *decoder, uint8_t byte, key_event_t *event_out);

void keyboard_queue_init(keyboard_queue_t *queue);
bool keyboard_queue_push_isr(keyboard_queue_t *queue, const key_event_t *event);
bool keyboard_queue_pop(keyboard_queue_t *queue, key_event_t *event_out);
uint32_t keyboard_queue_dropped(const keyboard_queue_t *queue);

#endif
