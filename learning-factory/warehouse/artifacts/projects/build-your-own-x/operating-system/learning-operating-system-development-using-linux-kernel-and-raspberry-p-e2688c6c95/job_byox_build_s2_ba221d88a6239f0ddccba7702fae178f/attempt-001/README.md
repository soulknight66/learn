# MiniOS: processes, address spaces, and a RAM filesystem

MiniOS is an independently written C challenge about three mechanisms that sit
behind a small operating-system kernel. You will complete a bounded process
table with round-robin scheduling, a software model of page translation, and a
flat in-memory filesystem. The same interfaces are suitable for hosted unit
tests and for a freestanding AArch64 integration build.

This is a model kernel, not a Linux port and not a Raspberry Pi board-support
package. The fixed-size data structures make state visible and tests
deterministic; no allocator, host filesystem call, or C library container is
needed.

## Suggested reveal order

1. Read `REQUIREMENTS.md` and `CONCEPTS.md`.
2. Run `make -C starter compile` to confirm the scaffold is warning-clean.
3. Implement `starter/src/process.c`, then run the public process checks.
4. Implement `starter/src/vm.c`, paying particular attention to address
   alignment, overflow-safe bounds, and permission masks.
5. Implement `starter/src/ramfs.c`. Mutating operations must either complete
   or leave the prior state unchanged when the request cannot fit.
6. Run `make -C starter test` and answer `DESIGN_QUESTIONS.md` in your own
   notes.

The starter intentionally compiles before it is complete. Public tests are
expected to report failures until the TODOs are implemented.

## Quick start

```bash
make -C starter compile
make -C starter test
```

The default compiler is the provisioned GCC recorded in
`environment/README.md`. Override `CC` with another C11 compiler if needed.
All public checks are deterministic and require no network, root privilege, or
Raspberry Pi hardware.

## Completion target

A solution is complete when it obeys every API rule in `REQUIREMENTS.md`,
passes the public checks, remains warning-clean under the documented flags,
and preserves subsystem invariants on rejected operations. Independent
validation may exercise longer state sequences and boundary values that the
public suite does not enumerate.

The supplied artifact remains `GENERATED` and `PARTIAL`: local build evidence
is informative, but only the external harness may promote validation labels.
