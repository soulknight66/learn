#ifndef KEYSTROKE_KERNEL_IO_H
#define KEYSTROKE_KERNEL_IO_H

#include <stdint.h>

static inline uint8_t io_in8(uint16_t port)
{
    uint8_t value;
    __asm__ volatile ("inb %1, %0" : "=a"(value) : "Nd"(port));
    return value;
}

static inline void io_out8(uint16_t port, uint8_t value)
{
    __asm__ volatile ("outb %0, %1" : : "a"(value), "Nd"(port));
}

static inline void io_wait(void)
{
    io_out8(0x80u, 0u);
}

static inline void cpu_interrupt_enable(void)
{
    __asm__ volatile ("sti" : : : "memory");
}

static inline void cpu_halt(void)
{
    __asm__ volatile ("hlt" : : : "memory");
}

#endif
