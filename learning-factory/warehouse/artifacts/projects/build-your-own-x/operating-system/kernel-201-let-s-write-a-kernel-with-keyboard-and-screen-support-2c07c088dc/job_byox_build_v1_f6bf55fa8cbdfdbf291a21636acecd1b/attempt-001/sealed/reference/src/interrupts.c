#include "interrupts.h"

#include <stddef.h>
#include <stdint.h>

#include "io.h"

#define IDT_ENTRY_COUNT 256u
#define KEYBOARD_VECTOR 0x21u
#define KERNEL_CODE_SELECTOR 0x08u
#define INTERRUPT_GATE_PRESENT 0x8eu

#define PIC_MASTER_COMMAND 0x20u
#define PIC_MASTER_DATA 0x21u
#define PIC_SLAVE_COMMAND 0xa0u
#define PIC_SLAVE_DATA 0xa1u
#define PIC_EOI 0x20u

typedef struct idt_entry {
    uint16_t offset_low;
    uint16_t selector;
    uint8_t reserved;
    uint8_t attributes;
    uint16_t offset_high;
} __attribute__((packed)) idt_entry_t;

typedef struct idt_pointer {
    uint16_t limit;
    uint32_t base;
} __attribute__((packed)) idt_pointer_t;

static idt_entry_t idt[IDT_ENTRY_COUNT];
static keyboard_decoder_t decoder;
static keyboard_queue_t queue;

extern void idt_load(const idt_pointer_t *pointer);
extern void keyboard_isr_stub(void);

static void set_gate(uint8_t vector, void (*handler)(void))
{
    uintptr_t address = (uintptr_t)handler;

    idt[vector].offset_low = (uint16_t)(address & 0xffffu);
    idt[vector].selector = KERNEL_CODE_SELECTOR;
    idt[vector].reserved = 0u;
    idt[vector].attributes = INTERRUPT_GATE_PRESENT;
    idt[vector].offset_high = (uint16_t)((address >> 16) & 0xffffu);
}

static void remap_and_mask_pic(void)
{
    io_out8(PIC_MASTER_COMMAND, 0x11u);
    io_wait();
    io_out8(PIC_SLAVE_COMMAND, 0x11u);
    io_wait();
    io_out8(PIC_MASTER_DATA, 0x20u);
    io_wait();
    io_out8(PIC_SLAVE_DATA, 0x28u);
    io_wait();
    io_out8(PIC_MASTER_DATA, 0x04u);
    io_wait();
    io_out8(PIC_SLAVE_DATA, 0x02u);
    io_wait();
    io_out8(PIC_MASTER_DATA, 0x01u);
    io_wait();
    io_out8(PIC_SLAVE_DATA, 0x01u);
    io_wait();

    /* Unmask only IRQ1. The slave remains entirely masked. */
    io_out8(PIC_MASTER_DATA, 0xfdu);
    io_out8(PIC_SLAVE_DATA, 0xffu);
}

void interrupts_init(void)
{
    idt_pointer_t pointer;

    keyboard_decoder_init(&decoder);
    keyboard_queue_init(&queue);
    set_gate(KEYBOARD_VECTOR, keyboard_isr_stub);
    remap_and_mask_pic();

    pointer.limit = (uint16_t)(sizeof(idt) - 1u);
    pointer.base = (uint32_t)(uintptr_t)&idt[0];
    idt_load(&pointer);
}

void keyboard_isr_c(void)
{
    key_event_t event;
    uint8_t byte = io_in8(0x60u);

    if (keyboard_feed(&decoder, byte, &event)) {
        (void)keyboard_queue_push_isr(&queue, &event);
    }
    io_out8(PIC_MASTER_COMMAND, PIC_EOI);
}

bool input_next_event(key_event_t *event_out)
{
    return keyboard_queue_pop(&queue, event_out);
}

uint32_t input_dropped_events(void)
{
    return keyboard_queue_dropped(&queue);
}
