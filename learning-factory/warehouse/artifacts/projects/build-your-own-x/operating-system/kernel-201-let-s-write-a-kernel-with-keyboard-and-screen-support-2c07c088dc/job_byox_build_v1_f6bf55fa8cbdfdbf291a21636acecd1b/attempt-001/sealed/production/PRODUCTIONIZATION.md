# Productionization assessment

Status: **not productionized**. `event_loop.c` is only a focused sketch for the single-core idle
race; it is not a production implementation and is not linked into the reference kernel.

Before considering real deployment:

- define and validate the complete boot ABI, GDT, exception IDT, stacks, and panic reporting;
- discover/map a firmware framebuffer or console rather than assuming legacy VGA;
- initialize and identify the input controller, handle status/error bits, commands, ACK/resend,
  scan-set negotiation, LEDs, and USB/HID alternatives;
- replace 8259-only routing with an interrupt-controller abstraction and handle spurious interrupts;
- specify SMP synchronization and ownership rather than relying on a single IRQ producer;
- close the idle/wakeup race, add scheduler wait queues, and route input through a TTY/session layer;
- validate buffer extents and integer arithmetic, expose loss telemetry, and define recovery policy;
- add exception/emulator/hardware tests across supported platforms, reproducible cross-toolchains,
  static analysis, and release provenance; and
- perform security review for privilege boundaries, DMA/device trust, denial of service, and parser
  state exhaustion.

No production, security, performance, portability, or transfer-readiness claim is made here.
