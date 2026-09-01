# Sealed implementation review

## Review outcome

The reference implementation is suitable as a deterministic semantic oracle for the bounded challenge. The host tests cover core success paths, lifecycle cleanup, permission failures, cross-boundary transfers, capacity rollback, fork isolation, and independently derived invariants. It is not suitable for privileged deployment or production use.

## Strengths

- Allocation choices are deterministic and documented.
- The highest-risk operations validate or reserve before mutation.
- Process exit releases both memory and descriptors while preserving zombie evidence.
- The checker validates indices before dereferencing them and recomputes redundant counts.
- Compilation uses strict warnings, and a sanitizer target exercises the same deterministic suite.

## Known limitations

1. Public structures allow callers to corrupt internal indices. `pebble_check()` handles these safely, but every mutating API is not a recovery boundary for already-corrupt state. For example, exit and unmap assume previously valid mappings.
2. Calls are single-threaded and non-reentrant. There are no atomics, interrupt masks, or locks.
3. There is no parent relationship, wait policy, saved register context, privilege state, or signal model.
4. The memory model is byte-array simulation. It performs no hardware translation, TLB invalidation, access-flag management, cache maintenance, or exception recovery.
5. Files are volatile, flat, and bounded. There is no crash consistency, storage driver, directory hierarchy, authorization, or concurrent I/O.
6. The Pi adapter assumes firmware has already configured PL011 and is only a boot/serial probe. Board revisions and peripheral-base differences are not detected.

## Production-blocking findings

- Internal types must become opaque, with generation-tagged handles for stale references.
- Every transition needs a defined synchronization context and lock ordering.
- Arithmetic and copy APIs need threat-model review for hostile pointers and DMA interactions.
- Target code needs board detection, architectural exception vectors, MMU tables, barriers, timers, and hardware-in-the-loop tests.
- Persistent storage needs a separately specified crash model and recovery validation.

No production-readiness claim or production validation label is warranted.
