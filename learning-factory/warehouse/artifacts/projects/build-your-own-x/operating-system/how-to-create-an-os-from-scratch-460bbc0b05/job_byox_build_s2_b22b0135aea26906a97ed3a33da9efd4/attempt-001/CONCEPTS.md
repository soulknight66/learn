# Concepts behind CairnOS

## State machines are the kernel's spine

A process is not merely an integer. Its state constrains which transitions are legal: a ready process
may run, a running process may block or exit, and only a blocked process may wake. Centralizing those
rules prevents impossible combinations such as two running processes or a dead process retaining an
open resource.

Round-robin scheduling separates policy (which ready process is next) from mechanism (a real context
switch). CairnOS models only policy. The cursor matters even after a process blocks or exits because
fairness depends on where the prior scan stopped.

## Virtual memory is an ownership problem

Hardware page tables ultimately translate a virtual page number plus an offset into a physical frame
plus the same offset. Before dealing with control registers and TLB invalidation, this model makes the
accounting explicit. A mapping has two views: the process says which frame it maps, while the frame
table says who owns it. A kernel mutation is correct only when both views change together.

Real kernels support shared pages, copy-on-write, eviction, and multiple address spaces. CairnOS uses
exclusive frames so accidental aliasing is unambiguously an error.

## Filesystems join names, objects, and handles

A filename identifies an inode-like object. An open descriptor identifies that object plus a private
cursor. Keeping those layers separate explains why two opens of the same file can read independently,
and why unlinking an open file needs an explicit policy. Fixed capacities replace allocation failure
with deterministic table-full errors.

## Cross-subsystem cleanup

The interesting bugs live between modules. Process exit must release memory ownership and descriptor
references; otherwise later operations see frames or files as permanently busy. Cleanup should be
observable through invariants, not assumed from a function's return code.

## Hosted model versus bare metal

The host build supplies fast deterministic tests and sanitizers. The freestanding build proves that
the core does not secretly rely on libc or a host ABI. The included boot shim establishes a stack,
calls C, reports over a serial port, and stops. It does not yet configure interrupts, switch privilege
levels, program real page tables, or persist a filesystem; those are deliberate next layers rather
than hidden claims.
