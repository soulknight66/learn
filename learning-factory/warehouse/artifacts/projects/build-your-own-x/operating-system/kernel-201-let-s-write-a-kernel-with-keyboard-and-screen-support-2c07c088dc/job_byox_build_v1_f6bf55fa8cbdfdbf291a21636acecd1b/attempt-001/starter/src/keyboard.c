#include "keyboard.h"

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
    /* TODO(student): consume prefixes, update modifiers, and translate supported Set-1 bytes. */
    (void)decoder;
    (void)byte;
    (void)event_out;
    return false;
}

void keyboard_queue_init(keyboard_queue_t *queue)
{
    queue->head = 0u;
    queue->tail = 0u;
    queue->dropped = 0u;
}

bool keyboard_queue_push_isr(keyboard_queue_t *queue, const key_event_t *event)
{
    /* TODO(student): publish one event, reserving one slot and dropping newest on full. */
    (void)queue;
    (void)event;
    return false;
}

bool keyboard_queue_pop(keyboard_queue_t *queue, key_event_t *event_out)
{
    /* TODO(student): consume one event in FIFO order with matching memory ordering. */
    (void)queue;
    (void)event_out;
    return false;
}

uint32_t keyboard_queue_dropped(const keyboard_queue_t *queue)
{
    return __atomic_load_n(&queue->dropped, __ATOMIC_RELAXED);
}
