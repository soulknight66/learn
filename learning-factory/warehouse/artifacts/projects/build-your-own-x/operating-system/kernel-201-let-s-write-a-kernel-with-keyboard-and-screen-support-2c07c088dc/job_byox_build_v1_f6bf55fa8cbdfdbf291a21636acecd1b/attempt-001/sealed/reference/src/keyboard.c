#include "keyboard.h"

#include <stddef.h>

static const char unshifted[128] = {
    [0x02] = '1', [0x03] = '2', [0x04] = '3', [0x05] = '4',
    [0x06] = '5', [0x07] = '6', [0x08] = '7', [0x09] = '8',
    [0x0a] = '9', [0x0b] = '0', [0x0c] = '-', [0x0d] = '=',
    [0x10] = 'q', [0x11] = 'w', [0x12] = 'e', [0x13] = 'r',
    [0x14] = 't', [0x15] = 'y', [0x16] = 'u', [0x17] = 'i',
    [0x18] = 'o', [0x19] = 'p', [0x1a] = '[', [0x1b] = ']',
    [0x1e] = 'a', [0x1f] = 's', [0x20] = 'd', [0x21] = 'f',
    [0x22] = 'g', [0x23] = 'h', [0x24] = 'j', [0x25] = 'k',
    [0x26] = 'l', [0x27] = ';', [0x28] = '\'', [0x29] = '`',
    [0x2b] = '\\', [0x2c] = 'z', [0x2d] = 'x', [0x2e] = 'c',
    [0x2f] = 'v', [0x30] = 'b', [0x31] = 'n', [0x32] = 'm',
    [0x33] = ',', [0x34] = '.', [0x35] = '/', [0x39] = ' '
};

static const char shifted[128] = {
    [0x02] = '!', [0x03] = '@', [0x04] = '#', [0x05] = '$',
    [0x06] = '%', [0x07] = '^', [0x08] = '&', [0x09] = '*',
    [0x0a] = '(', [0x0b] = ')', [0x0c] = '_', [0x0d] = '+',
    [0x1a] = '{', [0x1b] = '}', [0x27] = ':', [0x28] = '"',
    [0x29] = '~', [0x2b] = '|', [0x33] = '<', [0x34] = '>',
    [0x35] = '?', [0x39] = ' '
};

static uint8_t modifier_bits(const keyboard_decoder_t *decoder)
{
    uint8_t bits = 0u;

    if (decoder->left_shift || decoder->right_shift) {
        bits |= KEY_MOD_SHIFT;
    }
    if (decoder->caps_lock) {
        bits |= KEY_MOD_CAPS;
    }
    if (decoder->left_ctrl || decoder->right_ctrl) {
        bits |= KEY_MOD_CTRL;
    }
    if (decoder->left_alt || decoder->right_alt) {
        bits |= KEY_MOD_ALT;
    }
    return bits;
}

static key_code_t base_key_code(uint8_t scan)
{
    switch (scan) {
    case 0x01: return KEY_CODE_ESCAPE;
    case 0x0e: return KEY_CODE_BACKSPACE;
    case 0x0f: return KEY_CODE_TAB;
    case 0x1c: return KEY_CODE_ENTER;
    case 0x1d: return KEY_CODE_LEFT_CTRL;
    case 0x2a: return KEY_CODE_LEFT_SHIFT;
    case 0x36: return KEY_CODE_RIGHT_SHIFT;
    case 0x38: return KEY_CODE_LEFT_ALT;
    case 0x3a: return KEY_CODE_CAPS_LOCK;
    default:
        return unshifted[scan] == 0 ? KEY_CODE_NONE : KEY_CODE_CHARACTER;
    }
}

static key_code_t extended_key_code(uint8_t scan)
{
    switch (scan) {
    case 0x1d: return KEY_CODE_RIGHT_CTRL;
    case 0x38: return KEY_CODE_RIGHT_ALT;
    case 0x48: return KEY_CODE_ARROW_UP;
    case 0x50: return KEY_CODE_ARROW_DOWN;
    case 0x4b: return KEY_CODE_ARROW_LEFT;
    case 0x4d: return KEY_CODE_ARROW_RIGHT;
    case 0x53: return KEY_CODE_DELETE;
    default: return KEY_CODE_NONE;
    }
}

static void update_modifier(keyboard_decoder_t *decoder,
                            key_code_t code,
                            bool pressed)
{
    switch (code) {
    case KEY_CODE_LEFT_SHIFT: decoder->left_shift = pressed; break;
    case KEY_CODE_RIGHT_SHIFT: decoder->right_shift = pressed; break;
    case KEY_CODE_LEFT_CTRL: decoder->left_ctrl = pressed; break;
    case KEY_CODE_RIGHT_CTRL: decoder->right_ctrl = pressed; break;
    case KEY_CODE_LEFT_ALT: decoder->left_alt = pressed; break;
    case KEY_CODE_RIGHT_ALT: decoder->right_alt = pressed; break;
    case KEY_CODE_CAPS_LOCK:
        if (pressed) {
            decoder->caps_lock = !decoder->caps_lock;
        }
        break;
    default: break;
    }
}

static char translated_ascii(const keyboard_decoder_t *decoder,
                             key_code_t code,
                             uint8_t scan,
                             bool pressed)
{
    bool shift;
    char base;

    if (!pressed) {
        return 0;
    }
    switch (code) {
    case KEY_CODE_ESCAPE: return '\x1b';
    case KEY_CODE_BACKSPACE: return '\b';
    case KEY_CODE_TAB: return '\t';
    case KEY_CODE_ENTER: return '\n';
    case KEY_CODE_CHARACTER: break;
    default: return 0;
    }

    base = unshifted[scan];
    shift = decoder->left_shift || decoder->right_shift;
    if (base >= 'a' && base <= 'z') {
        if (shift != decoder->caps_lock) {
            return (char)(base - 'a' + 'A');
        }
        return base;
    }
    if (shift && shifted[scan] != 0) {
        return shifted[scan];
    }
    return base;
}

void keyboard_decoder_init(keyboard_decoder_t *decoder)
{
    decoder->extended = false;
    decoder->left_shift = false;
    decoder->right_shift = false;
    decoder->left_ctrl = false;
    decoder->right_ctrl = false;
    decoder->left_alt = false;
    decoder->right_alt = false;
    decoder->caps_lock = false;
    decoder->pause_bytes_left = 0u;
}

bool keyboard_feed(keyboard_decoder_t *decoder, uint8_t byte, key_event_t *event_out)
{
    bool was_extended;
    bool pressed;
    uint8_t scan;
    key_code_t code;

    if (decoder == NULL || event_out == NULL) {
        return false;
    }
    if (decoder->pause_bytes_left != 0u) {
        --decoder->pause_bytes_left;
        return false;
    }

    was_extended = decoder->extended;
    if (!was_extended && byte == 0xe0u) {
        decoder->extended = true;
        return false;
    }
    decoder->extended = false;
    if (!was_extended && byte == 0xe1u) {
        decoder->pause_bytes_left = 5u;
        return false;
    }

    pressed = (byte & 0x80u) == 0u;
    scan = byte & 0x7fu;
    code = was_extended ? extended_key_code(scan) : base_key_code(scan);
    if (code == KEY_CODE_NONE) {
        return false;
    }

    update_modifier(decoder, code, pressed);
    event_out->code = code;
    event_out->pressed = pressed;
    event_out->modifiers = modifier_bits(decoder);
    event_out->ascii = translated_ascii(decoder, code, scan, pressed);
    return true;
}

void keyboard_queue_init(keyboard_queue_t *queue)
{
    __atomic_store_n(&queue->head, 0u, __ATOMIC_RELAXED);
    __atomic_store_n(&queue->tail, 0u, __ATOMIC_RELAXED);
    __atomic_store_n(&queue->dropped, 0u, __ATOMIC_RELAXED);
}

bool keyboard_queue_push_isr(keyboard_queue_t *queue, const key_event_t *event)
{
    uint8_t head = __atomic_load_n(&queue->head, __ATOMIC_RELAXED);
    uint8_t tail = __atomic_load_n(&queue->tail, __ATOMIC_ACQUIRE);
    uint8_t next = (uint8_t)((head + 1u) % KEYBOARD_QUEUE_CAPACITY);

    if (next == tail) {
        (void)__atomic_fetch_add(&queue->dropped, 1u, __ATOMIC_RELAXED);
        return false;
    }
    queue->events[head] = *event;
    __atomic_store_n(&queue->head, next, __ATOMIC_RELEASE);
    return true;
}

bool keyboard_queue_pop(keyboard_queue_t *queue, key_event_t *event_out)
{
    uint8_t tail = __atomic_load_n(&queue->tail, __ATOMIC_RELAXED);
    uint8_t head = __atomic_load_n(&queue->head, __ATOMIC_ACQUIRE);

    if (tail == head) {
        return false;
    }
    *event_out = queue->events[tail];
    __atomic_store_n(
        &queue->tail,
        (uint8_t)((tail + 1u) % KEYBOARD_QUEUE_CAPACITY),
        __ATOMIC_RELEASE);
    return true;
}

uint32_t keyboard_queue_dropped(const keyboard_queue_t *queue)
{
    return __atomic_load_n(&queue->dropped, __ATOMIC_RELAXED);
}
