# Sealed reference implementation

This directory contains an independently generated, bounded reference kernel
for the challenge contracts. It is evaluation material, not learner starter
content and not a claim of production readiness.

The implementation separates portable policy (`scheduler.c`, `vm.c`, and
`ramfs.c`) from ARM mechanisms (`context.S`, `mmu.c`, reset, linker layout, and
UART). The emulated demo enables an identity-mapped ARMv5 MMU, validates a
shared-frame permission case and RAMFS round trip, then runs two independent
stacks through a cooperative round-robin sequence.

Build products are scratch evidence and can be reproduced using the exact
commands in the root `VALIDATION.md`.
