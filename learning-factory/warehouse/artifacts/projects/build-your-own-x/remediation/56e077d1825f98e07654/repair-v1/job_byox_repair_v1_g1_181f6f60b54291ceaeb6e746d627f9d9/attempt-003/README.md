# TinyARM Lab: a deterministic multitasking kernel

Build the core of a small ARM-oriented kernel in C. The lab separates mechanisms that can be
checked on any POSIX host from board-specific bring-up: you will implement a fixed-capacity task
scheduler, per-process virtual address translation, and a flat in-memory filesystem, then connect
the scheduler to an ARMv7 cooperative context-switch boundary.

This is an independently authored educational challenge. It does not copy the linked upstream
project. It is deliberately not a production kernel: there is no security claim, persistent block
device, SMP support, or complete MMU/exception implementation.

## What you receive

- `starter/` contains the public C interface, compiling stubs, and ARM port scaffolding.
- `public_tests/` contains deterministic black-box checks of a small part of the contract.
- `REQUIREMENTS.md` is the authoritative behavioral contract.
- `CONCEPTS.md` explains the background without giving implementation algorithms.
- `DESIGN_QUESTIONS.md` asks the questions to answer in your own design notes.
- `environment/` records expected tools and reproducible checks.

Reference implementations, private tests, and review answers are sealed and are not learner
inputs. Passing public tests is necessary but not sufficient.

## Suggested progression

1. Make lifecycle and round-robin scheduling tests pass.
2. Add blocking, waking, bounded quanta, and resource reclamation.
3. Implement page mapping plus all-or-nothing checked copies across page boundaries.
4. Implement the flat RAM filesystem, including failure-atomic replacement.
5. Audit invalid arguments, integer overflow, stale PIDs, and capacity exhaustion.
6. With an ARM cross-toolchain and QEMU, complete and exercise the board adapter.

## First commands

Run from the repository root:

```sh
make -C starter clean all
make -C public_tests clean test
sh environment/check.sh
```

The starter is intentionally incomplete, so the public test command initially exits nonzero after
reporting an assertion failure. Use only standard C11 and fixed-capacity storage; the reference
contract forbids allocator dependence in kernel operations.

## Completion boundary

Your implementation belongs in `starter/`. Do not infer correctness from a successful compile or
from prose claims. Independent validation controls all completion labels. The supplied manifest
therefore remains `GENERATED` + `PARTIAL`.
