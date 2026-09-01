#include "interrupts.h"

#include "io.h"

static keyboard_decoder_t decoder;
static keyboard_queue_t queue;

void interrupts_init(void)
{
    keyboard_decoder_init(&decoder);
    keyboard_queue_init(&queue);

    /* TODO(student): install IRQ1's IDT gate, remap/mask the PIC, and load the IDT. */
}

void keyboard_isr_c(void)
{
    key_event_t event;
    uint8_t byte = io_in8(0x60u);

    if (keyboard_feed(&decoder, byte, &event)) {
        (void)keyboard_queue_push_isr(&queue, &event);
    }

    /* TODO(student): acknowledge the master PIC even when no event was emitted. */
}

bool input_next_event(key_event_t *event_out)
{
    return keyboard_queue_pop(&queue, event_out);
}

uint32_t input_dropped_events(void)
{
    return keyboard_queue_dropped(&queue);
}
