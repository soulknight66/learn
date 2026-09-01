# Concepts

## Device state is a stream, not a lookup

A keyboard byte is not always a character. Prefixes modify the next byte, break bytes release keys,
and modifier history changes later translation. Model decoding as a state machine. Keeping it free of
port I/O makes every state transition reproducible in host tests.

## Interrupt and foreground ownership

The IRQ handler should do bounded work: read the device, update the decoder, enqueue, acknowledge.
Rendering is foreground work. This separates timing-sensitive hardware service from policy and gives
the two contexts an explicit ownership boundary. The queue is SPSC: one interrupt producer, one main
consumer. That is not automatically a multi-core or multi-producer design.

## A screen is memory with policy

VGA text mode exposes cells, but cursor movement, tabs, erasure, wrapping, and scrolling are software
policy. Passing an arbitrary cell array into the terminal logic turns memory safety and edge behavior
into ordinary tests. Only integration selects physical address `0xb8000`.

## Freestanding is not hosted C

The C language still works without an operating system, but libc generally does not. Fixed-width
types, explicit loops, a linker script, assembly entry code, and port instructions replace services
a hosted process normally receives. `volatile` describes observable device accesses; it is not a
general concurrency primitive. The queue uses acquire/release compiler builtins for publication.

## Where the broader OS concepts fit

This challenge stops at kernel I/O and deliberately does not pretend otherwise:

- **Processes** would require saved CPU contexts, scheduling, privilege transitions, and per-process
  state. Keyboard events might later feed a terminal-owning process.
- **Virtual memory** would replace unconditional physical addresses with explicit mappings and page
  permissions. Early boot commonly touches VGA physical memory before that layer exists.
- **Filesystems** would consume block-device services and a cache, not keyboard scan codes. A shell
  could eventually connect keyboard input to filesystem operations, but that is many layers later.

The useful lesson is architectural: isolate mechanism now so later subsystems can depend on an
interface instead of hard-coded device access.
