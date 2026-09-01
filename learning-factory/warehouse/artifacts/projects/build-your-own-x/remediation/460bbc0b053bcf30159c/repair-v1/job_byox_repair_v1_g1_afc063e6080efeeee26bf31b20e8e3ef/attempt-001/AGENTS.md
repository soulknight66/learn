# Learner Agent Guide

These instructions apply to work on the MicaOS Core Lab starter.

## Source of truth

- Preserve the public API declared by the starter headers.
- Implement the observable contract in `REQUIREMENTS.md`.
- Treat constants as hard limits, not suggested defaults.
- Do not alter tests, expected results, or build targets to conceal a failure.
- Do not add or seek sealed validators or reference implementation material. They are not part of the learner workspace.

When wording and an API detail appear to conflict, stop and inspect the public declaration and its comments. Keep the declaration intact and apply the documented semantics to that shape.

## Implementation boundaries

- Write portable C11 suitable for a small freestanding-style core.
- Keep module state in the supplied bounded data structures. Do not use heap allocation to evade a capacity.
- Do not introduce host filesystem, process, thread, network, or clock dependencies into a core module.
- Avoid undefined behavior, unchecked size arithmetic, reads beyond a supplied range, and writes through null pointers.
- Keep scheduler, VM, and RAM-filesystem state independent unless the public API explicitly connects them.
- Preserve state on rejected operations. Validate an operation before committing its observable effects.

This exercise models kernel mechanisms; it does not ask for boot code, assembly startup, CPU page tables, an interrupt controller, a device driver, or a production security boundary.

## Evidence before completion

From the repository root, run:

```bash
make -C starter build
make -C starter test
```

A completion claim should be supported by successful command output and a review against all documented limits. Public tests do not replace that review. Keep compiler warnings visible and fix warnings attributable to your changes.

## Review checklist

- Initial state is deterministic and empty.
- Every successful state transition is legal.
- Invalid inputs and invalid transitions return the appropriate public error category.
- Capacity is usable exactly up to the stated limit and rejected immediately beyond it.
- A failed mutating operation leaves the module observably unchanged.
- No read exposes uninitialized, stale, or out-of-range bytes.
- Reuse after reap, unmap, or unlink follows the same contract as first use.
