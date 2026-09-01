# Sealed implementation review

## Scope verdict

The reference is intentionally a deterministic teaching model. It is not
reviewed, tested, or suitable as a production kernel. `MANIFEST.yaml` correctly
keeps `productionized` false and requests independent validation.

## Strengths to preserve

- State changes update authoritative and indexed scheduler views together.
- Map validation precedes allocation; partial walks record exactly which
  frames and parent slots they created and undo them in reverse order.
- Unmap computes and preflights the full reclamation set before clearing a
  leaf, preventing wrong-allocator partial mutation.
- Filesystem mutations perform lexical and graph checks before publication.
- Ordered collections make allocator, scheduler, and directory outcomes
  reproducible.

## Review risks

- The generation host could not compile Rust. Syntax, borrow checking, API
  compatibility, and test expectations remain unverified until an independent
  toolchain run.
- `FrameAllocator::new` materializes every free frame and can consume excessive
  memory for an adversarially large range. A bounded-range policy or interval
  representation would be needed outside the exercise.
- Allocation-backed operations can abort the process on host OOM; stable
  `Vec`/`BTreeMap` APIs do not make all allocation failures recoverable here.
- Internal `expect` calls rely on invariants that safe public methods preserve.
  Fault injection or future mutable accessors would require propagating a
  corruption error instead.
- Address-space methods accept an allocator per call rather than a bound
  capability. Preflight makes unmap safe, but the interface still permits
  confusing misuse.
- The filesystem uses whole-file `Vec<u8>` storage and recursive validation;
  it has neither sparse blocks nor protection against extremely deep trees.
- None of the subsystems is synchronized. `Send`/`Sync` behavior inherited
  from collections is not a concurrency protocol.

## Required independent checks

Compile both crates on stable Rust, run public and sealed suites, run formatter
and Clippy, add randomized model-based state sequences, and execute under a
memory/error sanitizer where supported. Those actions have not been performed
by this worker and no corresponding validation label is claimed.
