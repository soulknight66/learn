# Concepts

## A scheduler is a state machine

A context switch saves registers; it does not decide who is allowed to run.
Keeping policy separate from the ARM save/restore boundary makes the harder
invariant visible: exactly one table entry can be running. Round-robin fairness
comes from beginning the search after the old slot rather than always at slot
zero. `BLOCKED` means an external event is required; `ZOMBIE` means execution is
finished but identity and exit evidence have not yet been reclaimed.

Cooperative scheduling avoids asynchronous stack frames while retaining real
independent stacks and suspended call chains. It also exposes a limitation: a
task that never yields owns the CPU forever.

A logical selection and a physically executing stack are related but not
identical facts. Policy code can change the selected table entry before the ARM
save/restore boundary runs. A slot index is reusable storage, so after reap and
reuse it no longer identifies the frame that was executing there. Context
ownership therefore needs an incarnation identity (for example, a non-reused
PID together with its slot), and every save, yield, and exit must prove that
identity before mutating task or register state.

## An address is not a byte

The page allocator owns physical frames. An address space separately associates
virtual pages with frames and permissions. Translation first identifies a page,
then checks requested access, then combines its physical base with the original
offset. These steps should be explicit so a wraparound or permission error
cannot accidentally become an address.

ARMv5 short-descriptor translation begins at a 16 KiB L1 table selected by TTBR.
A section descriptor maps 1 MiB; a coarse descriptor can lead to smaller pages.
The starter's board bring-up needs only safe identity-mapped sections before the
MMU bit is enabled. The portable mapping table models per-process 4 KiB policy;
turning those mappings into hardware L2 tables is an extension.

## A filesystem is a set of invariants

Even a flat RAM filesystem has namespace uniqueness, capacity, length, and
lifetime rules. The key discipline is failure atomicity. Perform every check
before changing a slot, and scrub data before publishing a deleted slot as free.
A fixed-size representation is useful in a tiny kernel: it makes exhaustion and
worst-case work explicit.

## Freestanding C changes the ground rules

There is no implicit process startup, initialized terminal, dynamic loader, or
standard library. Reset code establishes the stack and C's zero-initialized
storage promise. MMIO registers require volatile access. Compiler optimization
still applies, so the boundary around coprocessor and device instructions needs
appropriate compiler barriers.

## Evidence has layers

Host tests cheaply exercise edge cases and memory safety in deterministic C.
Cross-compilation verifies ABI and linker assumptions. Emulation checks reset,
MMIO, CP15 configuration, and context switching. Each layer can pass while
another fails, which is why the completion contract requires all three.
