# Core Concepts

MicaOS Core Lab isolates a few operating-system ideas in ordinary, deterministic C. The simplification is deliberate: it lets you reason about contracts without also debugging a bootloader or physical machine.

## Bounded state machines

Each module is a state machine with a fixed amount of storage. An operation is valid only in particular states, and success moves the object to another documented state. Capacity is part of the state: an exited-but-unreaped process still occupies a scheduler record, while an unlinked file does not occupy a filesystem record.

The important distinction is between *representation* and *behavior*. Tests may observe which process is selected or whether a page is writable, but the private layout used to represent those facts is an implementation choice unless a public type exposes it.

## Determinism and round-robin fairness

A deterministic scheduler produces the same selection sequence for the same history. Round-robin additionally gives each eligible resident process a turn in cyclic order. Blocking changes eligibility; waking restores it. Neither action should introduce dependence on timing or randomness.

Fairness here is a property of an operation sequence, not real-time execution. The model has no timer interrupt, CPU preemption, or simultaneous processes.

## Virtual pages and physical frames

A virtual address names a byte in a virtual page. A mapping connects that page to one bounded storage frame and associates protection with the mapping. The concrete teaching structs expose the selected frame, and the contract makes lowest-free selection deterministic; a production interface would normally hide that allocator detail.

Zero-on-allocation is both a determinism rule and an isolation rule. A page mapped after a frame is reused must not reveal the earlier owner's bytes. Writable protection is checked before a store becomes observable.

This model resembles a tiny page manager, but it is not an MMU configuration. It has no hardware page tables, translation lookaside buffer, faults, privilege levels, or executable permissions.

## A flat, binary-safe filesystem

The RAM filesystem is a finite name-to-byte-sequence mapping. “Flat” means names identify files directly; there are no directories or path traversal. Contents are binary, so their length—not a terminating zero—defines the file.

Create and unlink control file lifetime. Offset-based writes may extend contents and make any skipped gap read as zero; offset-based reads may return a prefix of the remaining bytes. RAM storage makes the service ephemeral: initialization and program termination provide no persistence guarantee.

## Atomic rejection

An operation is atomic at this model's scale when observers see either the full successful result or the complete old state. For example, an oversized replacement must not first truncate a file, and a map that finds no frame must not leave a half-created mapping.

Atomicity in this lab does not imply threads, locks, transactions, or crash recovery. Calls are synchronous. The requirement concerns validating before any failed request becomes partially visible.

## Model core versus production OS

Production kernels must address concurrency, privilege, hostile inputs, hardware ordering, interrupts, persistence, recovery, and many architecture-specific details. MicaOS intentionally omits those systems. Completing the lab demonstrates careful bounded-state programming; it does not produce a kernel image or a deployable security boundary.
