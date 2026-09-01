# Tradeoffs

## Decoder versus ISR monolith

The implementation spends a small amount of state and call overhead to keep byte decoding pure.
That makes malformed-prefix and modifier behavior deterministic under host tests. Inlining all logic
inside the ISR would save little and couple tests to privileged I/O.

## Event queue versus direct rendering

The queue bounds interrupt latency and keeps VGA scrolling out of IRQ context. Its fixed storage can
lose input under sustained load; drop-newest plus a counter is an explicit failure mode. Dynamic
allocation is inappropriate this early in boot and would add more failure paths.

## Structured key events versus a byte queue

Structured events retain make/break, physical category, and modifiers while still offering ASCII
for this simple echo client. They consume more space than bytes. A mature input stack would likely
use richer key identifiers and perform layout/Unicode translation above the hardware driver.

## Legacy hardware versus portable interfaces

VGA text memory and the 8259/8042 path produce a compact teaching kernel and work with many PC
emulators. They exclude UEFI-only machines, USB-only keyboards, APIC routing, graphics framebuffers,
and non-x86 systems. The pure terminal and decoder boundaries reduce, but do not erase, that debt.

## Atomic builtins versus interrupt masking

Acquire/release builtins state queue publication directly and compile without libc for byte indices
on i386. This remains a deliberately narrow SPSC design. A general SMP kernel needs explicit memory
model documentation, cache-line/layout attention, and a strategy for multiple producers.
