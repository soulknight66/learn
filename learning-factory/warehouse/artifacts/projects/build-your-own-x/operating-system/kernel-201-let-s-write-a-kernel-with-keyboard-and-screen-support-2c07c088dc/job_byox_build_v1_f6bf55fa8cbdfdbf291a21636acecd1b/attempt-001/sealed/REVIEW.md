# Reference implementation review

Review date: 2026-08-31. Scope: static review plus supported host compilation/tests; no emulator or
physical-hardware execution.

## What is supported by local evidence

- Pure terminal and decoder/queue code compile as strict hosted C11 and pass deterministic boundary
  tests.
- The same sources compile freestanding as 32-bit objects and link without unresolved symbols.
- The output is mechanically checkable as ELF32/i386 with a valid early Multiboot-v1 header.

These facts do not establish boot correctness.

## Findings

1. **High — exception handling is absent.** Only vector `0x21` is present. Any CPU exception will
   likely escalate to a triple fault. Add exception stubs and diagnostic state before wider use.
2. **High — hardware assumptions are unchecked.** The code assumes a flat selector `0x08`, legacy
   PIC and PS/2 routing, VGA at `0xb8000`, and controller setup inherited from firmware/bootloader.
3. **Medium — idle has a lost-wakeup window.** An event arriving between the empty check and `hlt`
   can remain pending until a later interrupt. The production sketch shows a single-core closure.
4. **Medium — no controller status/error handling.** IRQ1 reads one byte unconditionally and does not
   inspect parity/timeout/auxiliary-source status or negotiate scan set.
5. **Medium — interrupt assembly assumes kernel data segments.** It preserves general registers but
   does not switch/preserve segment registers for a future user-mode transition.
6. **Low — dimensions can overflow.** `width * height` is not checked before indexing. Current callers
   use `80x25`, but a reusable API should reject impossible extents.
7. **Low — Caps Lock repeat policy is primitive.** Every make toggles state; no key-down suppression
   or LED command protocol is implemented.
8. **Low — diagnostics are inaccessible.** The drop counter exists but the demo does not display or
   export it, and there is no panic/serial channel.

## Verdict

Suitable as a bounded educational reference, not production-ready. Keep `productionized: false` and
validation `PARTIAL` until an independent harness adds emulator evidence and addresses the high-risk
boot/exception findings.
