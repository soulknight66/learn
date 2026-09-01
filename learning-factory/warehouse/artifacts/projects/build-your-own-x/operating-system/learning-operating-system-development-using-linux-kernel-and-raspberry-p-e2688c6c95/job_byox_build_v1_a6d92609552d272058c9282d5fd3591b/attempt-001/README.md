# PebbleOS kernel-mechanisms lab

PebbleOS is a standalone C challenge about the deterministic parts of a small operating-system kernel: process state, round-robin scheduling, page mappings with copy-on-write forks, and a bounded in-memory filesystem. The core runs as an ordinary host process, so you can use sanitizers and repeatable tests before attempting a Raspberry Pi port.

This repository is independently generated from catalog metadata. It does not copy the linked tutorial. The upstream link is provenance only, its license is recorded as `NOASSERTION`, and no linked content was accessed or reproduced for this challenge.

## What you build

Implement the API declared in `starter/include/pebble.h`. The model deliberately uses fixed-size tables and caller-owned storage: there is no allocator, background thread, wall clock, or hidden I/O. That makes every state transition inspectable and every test reproducible.

Work through the stages in order:

1. Read `CONCEPTS.md`, then answer the questions in `DESIGN_QUESTIONS.md` without coding.
2. Establish initialization, process creation, and lifecycle transitions.
3. Add deterministic round-robin scheduling.
4. Add mapped pages, permission checks, and cross-page copies.
5. Implement fork using copy-on-write frame sharing.
6. Add the flat filesystem and per-process descriptors.
7. Make `pebble_check()` reject every corrupt state described by the contract.

The complete behavioral contract and milestone gates are in `REQUIREMENTS.md`. Start with `starter/README.md`.

## Local workflow

```sh
sh environment/check.sh
make -C starter
make -C starter public
```

The starter compiles but intentionally returns `PEB_ERR_NOT_IMPLEMENTED` from most operations, so the public test command is expected to report failures until you implement the milestones. Passing public tests is necessary, not sufficient: boundary conditions and transactional behavior are independently validated.

## Raspberry Pi boundary

The portable model teaches mechanisms that can later sit behind exception handlers and a board support package. A real Pi build also needs an AArch64 cross-toolchain, startup assembly, a linker script, exception vectors, MMU register programming, a timer, and a UART or other console. Those target-dependent pieces are not asserted to run here. The supplied environment check reports whether the relevant tools are present.

## Repository visibility

Learners receive this file, `AGENTS.md`, `MANIFEST.yaml`, `REQUIREMENTS.md`, `CONCEPTS.md`, `DESIGN_QUESTIONS.md`, and the `starter/`, `public_tests/`, and `environment/` trees. Evaluation evidence and reference material are kept outside the learner view. Independent validation, not a prose claim or a successful generator exit, decides completion.
