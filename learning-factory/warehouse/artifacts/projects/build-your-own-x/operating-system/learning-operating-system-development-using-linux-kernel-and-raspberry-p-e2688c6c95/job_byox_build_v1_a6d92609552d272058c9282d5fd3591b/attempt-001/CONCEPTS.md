# Concepts behind the lab

## A kernel is a state machine

An operating system coordinates resources whose lifetimes overlap. The useful abstraction for this lab is not “a collection of helper functions,” but a state machine. A process can only traverse legal lifecycle edges; a frame's reference count must agree with mappings; an open count must agree with descriptors. Bugs appear when one field changes without all related fields changing.

Real kernels need synchronization because interrupts and cores can interleave transitions. PebbleOS removes that nondeterminism: one API call is one transition. This makes transaction boundaries visible before locks are introduced.

## Processes and scheduling

A process record combines identity, lifecycle state, an address space, and resources such as descriptors. Identity must outlive a table position: slots can be recycled, while stale PIDs must not suddenly name a different process.

Round-robin scheduling separates policy from mechanism. The policy chooses the next ready slot cyclically. The mechanism changes states and records the active slot. Even this small scheduler has important edge cases: an idle system, a blocked current process, wraparound, and reusing a slot without biasing the cursor.

On a Raspberry Pi, a timer interrupt could invoke equivalent scheduling policy, while exception-return assembly would perform the context switch. This lab models the policy and its durable bookkeeping, not register saving.

## Virtual memory and copy-on-write

A virtual address is split into a virtual-page number and an offset. A page-table entry associates that virtual page with a physical frame and permission bits. Two processes may map the same frame while observing different virtual addresses and permissions.

Fork can avoid eagerly copying every frame. Parent and child initially share frames with write permission suppressed. The first writer creates a private copy, then resumes with a writable mapping. Correctness depends on two coupled facts: page-table flags and frame reference counts. A capacity failure must be discovered before a multi-page operation splits only some mappings.

Hardware page tables encode similar ideas, but architecture-specific descriptor formats, TLB invalidation, exception syndromes, cache attributes, and memory barriers are outside this portable model.

## Files, descriptors, and cursors

A file record is persistent namespace state. A descriptor is process-local access state that points at a file and carries a cursor and mode. Confusing these layers produces classic bugs: deleting open storage, sharing a cursor unintentionally, leaking an open count, or truncating before discovering that no descriptor is available.

PebbleOS uses a flat, bounded filesystem so allocation and rollback are observable. A production filesystem additionally needs persistent media, crash-consistent metadata, directories, permissions, caching, and concurrent access rules.

## Invariants as executable design

An invariant checker recomputes redundant facts instead of trusting them. For example, it counts all mappings and compares that result with each frame's stored reference count. This is stronger than checking only that a count is nonzero. It turns corruption into a local, deterministic failure and gives fuzzers a useful oracle.

The checker is not a substitute for validation at API boundaries. It is a second line of defense and a compact executable statement of the data model.

## Host model versus a Raspberry Pi kernel

Host compilation provides fast tests for pure mechanisms. Moving to a Pi changes the environment: code starts without a C runtime; the linker controls physical placement; devices are memory-mapped; exceptions select privileged paths; an MMU and TLB enforce translations; and debugging often begins over a serial link. Keep portable policy free of board addresses and privileged instructions so target adapters remain small and auditable.
