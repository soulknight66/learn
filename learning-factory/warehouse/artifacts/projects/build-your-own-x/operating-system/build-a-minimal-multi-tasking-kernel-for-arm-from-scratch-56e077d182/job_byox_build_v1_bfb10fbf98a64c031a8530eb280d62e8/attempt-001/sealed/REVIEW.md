# Sealed implementation review

## Review outcome

The reference C model follows the stated deterministic policies and is backed by strict-warning,
public, and sealed test runs recorded in `VALIDATION.md`. Sanitizer linking was attempted but its host
runtimes were unavailable. This is educational evidence, not an independent validation label.

## Strengths

- Mutations validate capacity and ranges before publishing state.
- Scheduler choices and all resource allocations have deterministic ordering.
- Frame teardown occurs on exit/kill, independently of later zombie reaping.
- VM cross-page writes and filesystem replacements use validate-then-commit shapes.
- The ARM adapter is isolated from the portable policy model and makes its cooperative scope explicit.

## Material limitations

- Public structures can be corrupted directly; there is no opaque handle or invariant checker.
- The callback interface permits reentrant calls and assumes single-threaded execution.
- VM copying does not promise snapshot behavior when its source aliases physical frame storage.
- There are no locks, interrupt exclusion rules, hardware page tables, exception vectors, userspace,
  device persistence, or crash recovery.
- The ARM code was authored for QEMU `virt` but cannot be claimed built or booted on a host lacking
  both cross compiler and emulator.

## Production verdict

Not productionized. The manifest correctly remains `productionized: false`, status `GENERATED`, with
labels `GENERATED` and `PARTIAL`. External validation must decide any stronger label.
