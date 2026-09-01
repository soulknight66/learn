# Productionization gap

Status: **not productionized**. This file is a review checklist, not evidence
that any item has been completed.

A bootable RISC-V system would additionally need:

- a specified machine/board, linker script, reset path, stack setup, SBI or
  firmware contract, panic path, and reproducible cross-compilation toolchain;
- trap-vector assembly, complete register contexts, privilege checks, timer and
  external interrupts, preemption rules, and SMP-safe scheduler synchronization;
- architectural PTE writes, ASIDs, `satp`, `sfence.vma`, access/dirty-bit policy,
  superpage rules, copy-on-write, shootdowns, and physical-memory discovery;
- a syscall ABI, user-pointer validation, resource limits, capabilities or
  credentials, isolation tests, and a threat model;
- block/device drivers, buffer cache, persistent on-disk format, journaling or
  copy-on-write transactions, fsck/recovery, partial-I/O handling, and power-cut
  fault injection;
- bounded allocation, stack-depth audits, structured telemetry, watchdogs,
  reproducible images, update/rollback strategy, and vulnerability response;
- hardware/emulator matrices, long-running stress, fuzzing, benchmarks with
  recorded methodology, independent review, and provenance for every binary.

The host model may serve as an oracle for some state-machine tests, but code
would need substantial redesign rather than direct deployment. No QEMU, target
compiler, boot test, fuzz run, benchmark, security audit, or hardware run was
available during generation.
