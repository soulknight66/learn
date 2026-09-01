# Requirements

The words **must**, **must not**, and **should** are normative. Public tests cover only a subset;
the numbered requirements are the complete contract.

## R1 — freestanding boundary

- Kernel-linked C must compile as C11 with `-ffreestanding` and without libc calls.
- Architecture-specific I/O must remain behind `starter/include/io.h`.
- The final artifact must be a 32-bit i386 ELF with a Multiboot v1 header in the first 8192 bytes.
- The boot path must install a keyboard IRQ gate, remap the legacy PIC, unmask IRQ1, and acknowledge
  each handled keyboard IRQ. It must not enable interrupts before the queue and decoder are initialized.

## R2 — terminal model

`terminal_init(term, cells, width, height, color)` must return `false` for a null pointer or a zero
dimension. On success it must reset the cursor to `(0,0)`, retain the supplied color, and fill every
cell with a space in that color. A VGA cell is `(color << 8) | byte`.

`terminal_putc` and `terminal_write_n` must implement:

- printable bytes (`0x20` through `0x7e`), including ordinary wrap at the right edge;
- newline (`\n`), which moves to column zero on the next row;
- carriage return (`\r`), which moves to column zero without changing rows;
- backspace (`\b`), which erases one cell on the current row and does nothing in column zero;
- tab (`\t`), which writes spaces up to the next multiple-of-four column; and
- ignoring other C0 control bytes.

Advancing below the last row must scroll rows upward by one, blank the last row using the current
color, and leave the cursor on its first valid column. No write may escape the supplied cell extent.

## R3 — keyboard byte stream

`keyboard_feed` consumes one PS/2 Set-1 byte and returns whether it produced one complete event.

- A lone `0xe0` is a prefix, not an event. Exactly the next byte is interpreted as extended.
- The decoder must distinguish key press (make) from release (break) using bit 7.
- It must track left/right Shift, Ctrl, Alt, and Caps Lock. Caps Lock toggles only on its make byte.
- Letters use `Shift XOR Caps Lock`; digits and punctuation use Shift only.
- Supported printable US-layout keys are digits, letters, space, `` `-=[]\\;',./ `` and their
  shifted forms. Enter, Tab, Backspace, Escape, modifiers, Caps Lock, extended arrow keys, and
  extended Delete must have stable `key_code_t` values.
- Make events for printable/control-text keys carry their ASCII byte. Break events and non-text keys
  carry `ascii == 0`.
- Every emitted event contains a modifier snapshot **after** processing that byte.
- Unsupported bytes must be safely consumed and return no event; an unsupported extended byte must
  also clear prefix state.

Pause/Break's multi-byte `0xe1` sequence, scan-code negotiation, keyboard LEDs, typematic policy,
international layouts, and USB HID are out of scope.

## R4 — IRQ event queue

The queue has `KEYBOARD_QUEUE_CAPACITY == 16` slots and deliberately reserves one slot to distinguish
full from empty, so at most 15 events are retained. It must preserve FIFO order between one IRQ-side
producer and one main-loop consumer.

On full, `keyboard_queue_push_isr` must leave existing events unchanged, drop the newest event,
return `false`, and increment the dropped counter exactly once. Pop on empty returns `false` without
modifying the caller's output. Queue publication/consumption must use compiler/CPU ordering suitable
for a single-core i386 producer/consumer pair.

## R5 — integration behavior

The IRQ handler reads exactly one data byte from port `0x60`, feeds it to the decoder, queues any
event produced, and then sends end-of-interrupt to the master PIC. The foreground loop echoes only
pressed events with nonzero ASCII to the terminal. It should use `hlt` while idle rather than spin.

## R6 — evidence and limitations

A host test pass validates pure C state machines, not real hardware. An ELF link validates layout,
not successful boot. Record these levels separately; never infer emulator, hardware, performance,
security, processes, virtual memory, or filesystem support from either result.
