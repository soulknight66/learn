# Sealed alternatives

These are design alternatives, not additional validated implementations.

## Exception-frame tasks

An IRQ/SVC entry path could save all user-visible registers into a trap frame and
return with `subs pc, lr, #4`. That supports preemption and user mode, but requires
vector placement, banked-stack setup, interrupt acknowledgement, nesting rules,
and substantially stronger tests.

## Stackless task state machines

Tasks could return a status on each step instead of preserving stacks. This is
extremely portable and avoids assembly, but it no longer demonstrates suspended
C call chains or a genuine context switch.

## Hardware small pages

Each software mapping could materialize as an ARM coarse L2 entry, with a unique
TTBR per process and TLB invalidation on switch. It provides real isolation but
introduces page-table frame ownership, kernel-global mappings, ASID limitations
on older cores, and fault recovery.

## Bitmap-only frame ownership

A bitmap is smaller than 16-bit reference counts when sharing is forbidden.
Copy-on-write or shared mappings then need an additional ownership scheme. The
reference uses counts because its boot demo intentionally shares one frame.

## Log-structured RAM filesystem

Appending immutable records would make crash reasoning and snapshots clearer.
Without persistent media, it spends scarce RAM and needs garbage collection, so
inline fixed records are a better fit for this bounded exercise.
