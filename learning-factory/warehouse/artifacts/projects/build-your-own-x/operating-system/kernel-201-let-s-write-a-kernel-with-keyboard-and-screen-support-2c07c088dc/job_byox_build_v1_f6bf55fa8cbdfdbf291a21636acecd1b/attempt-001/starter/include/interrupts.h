#ifndef KEYSTROKE_KERNEL_INTERRUPTS_H
#define KEYSTROKE_KERNEL_INTERRUPTS_H

#include <stdbool.h>
#include <stdint.h>

#include "keyboard.h"

void interrupts_init(void);
void keyboard_isr_c(void);
bool input_next_event(key_event_t *event_out);
uint32_t input_dropped_events(void);

#endif
