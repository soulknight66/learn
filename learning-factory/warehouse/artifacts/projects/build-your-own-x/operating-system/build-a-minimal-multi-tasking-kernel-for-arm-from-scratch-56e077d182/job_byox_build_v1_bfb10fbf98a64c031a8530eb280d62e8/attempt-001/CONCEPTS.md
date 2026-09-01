# Concepts

## Processes are state plus owned resources

A process is more than a function pointer. Even this small model needs an identity, a lifecycle
state, scheduling metadata, and an address space. Keeping lifecycle transitions explicit prevents a
blocked task from running or a dead task from retaining physical frames. A zombie deliberately keeps
only exit evidence until a parent-like observer reaps it.

## Scheduling separates policy from context switching

Round-robin selection is policy: it decides which runnable task goes next. An ARM context switch is
mechanism: it saves the old register set and restores another. Host callbacks let you test the policy
without depending on assembly. The ARM milestone then replaces callback stepping with independent
stacks while preserving the same state-machine ideas.

A quantum is meaningful only at a defined boundary. Here one callback invocation is one interval;
real preemption instead uses an interrupt boundary and must save a larger exception context.

## Virtual addresses need checked translation

Virtual memory introduces a level of indirection: split an address into virtual page number and page
offset, look up a mapping, check permissions, then combine a physical frame with the offset. Real ARM
MMUs cache translations and enforce privilege. This lab's software model has neither property, but it
exposes mapping ownership, bounds, permissions, and teardown in a deterministic form.

Cross-page copying is a small transaction. Validating as bytes are copied can expose a partial write
when a later page is missing. Separating validation from mutation creates an all-or-nothing contract.

## A filesystem is allocation plus namespace plus data

Even one flat directory needs names, metadata, block ownership, and EOF semantics. Replacement is
subtle because the new contents may need more blocks, fewer blocks, or may alias the old storage.
Failure atomicity means callers either observe the old file or the complete replacement, never an
accidental hybrid.

## Fixed capacity can simplify reasoning

Fixed arrays are restrictive, but they make exhaustion testable and avoid allocator recursion inside
a kernel. Deterministic lowest-index allocation also makes state reproducible. Production systems
would need concurrency control, scalable data structures, persistence protocols, and crash recovery.

## Bare-metal evidence differs from a host test

A host compiler can validate most C state transitions but cannot prove ARM instruction encodings,
link addresses, exception behavior, or QEMU boot. Tool availability and observed commands must be
recorded separately so a missing cross-toolchain is not disguised as a successful board build.
