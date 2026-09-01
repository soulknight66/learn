# RISC-V Kernel Model Lab

Build the deterministic core of a tiny Rust operating system: a round-robin
process scheduler, an Sv39 virtual-memory mapper, and an inode-based in-memory
filesystem. The lab runs as an ordinary host Rust crate, so you can test kernel
invariants before adding privileged instructions, a bootloader, or a board.

This is an independently written challenge inspired only by the catalog topic
of a RISC-V Rust operating-system tutorial. The linked article is provenance,
not copied course material; see `LICENSE_BOUNDARY.md`.

## The challenge

Implement every `todo!()` in `starter/src/` without changing the public API.
Your implementation must satisfy `REQUIREMENTS.md` and preserve these global
properties:

1. Exactly zero or one process is `Running`, and it agrees with `current()`.
2. A virtual page has at most one mapping; failed maps leave no page-table or
   frame-allocation residue.
3. Filesystem mutations are all-or-nothing, and every directory entry names a
   live inode.
4. Inputs that would overflow, alias ambiguously, or escape their abstraction
   are rejected with a typed error rather than a panic.

No unsafe Rust, assembly, network access, nightly feature, or third-party crate
is needed.

## Progressive route

- **Stage 0 — Contract:** read `REQUIREMENTS.md` and answer
  `DESIGN_QUESTIONS.md` before coding.
- **Stage 1 — Processes:** implement PID allocation and deterministic
  round-robin state transitions.
- **Stage 2 — Frames and Sv39:** implement frame ownership, three-level walks,
  permission checks, rollback, and reclamation.
- **Stage 3 — Filesystem:** implement absolute-path traversal and inode
  operations.
- **Stage 4 — Integration:** pass the tests in `public_tests/`, then develop
  extra boundary and state-machine tests of your own.
- **Stage 5 — Critique:** attempt the prompts in `debugging/`,
  `review_exercises/`, `adversarial/`, and `benchmarks/`.

## Run

With stable Rust 1.74 or newer:

```bash
cargo test --manifest-path public_tests/Cargo.toml
```

The public suite is deliberately incomplete. Passing it is not evidence that
all requirements hold. The sealed tree is withheld from learners by the
factory and contains the reference implementation and stronger tests.

This generated artifact is marked `PARTIAL`: the build worker did not have a
Rust toolchain or QEMU available, so it could perform structural validation but
could not truthfully claim compilation or execution. See `VALIDATION.md`.
