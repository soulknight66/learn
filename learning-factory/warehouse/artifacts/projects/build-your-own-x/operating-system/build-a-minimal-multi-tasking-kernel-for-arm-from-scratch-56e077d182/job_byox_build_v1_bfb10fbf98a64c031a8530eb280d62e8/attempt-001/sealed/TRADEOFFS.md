# Sealed tradeoffs and alternatives

## Fixed arrays versus allocation

Fixed arrays cap realism but make every exhaustion path deterministic and keep allocator concerns out
of the lesson. A next step would use slab caches for tasks and metadata while retaining explicit
ownership rules.

## Callback steps versus CPU emulation

Callbacks make scheduling policy portable and sanitizer-friendly. They cannot expose arbitrary
instruction preemption, register corruption, or privilege faults. Full CPU emulation would be much
heavier and would blur the C invariants this challenge targets.

## Durable zombies versus immediate slot reuse

Zombies reduce capacity until reaped, but they preserve exit evidence and make stale identities
visible. Immediate reuse is smaller yet loses parent-observable status unless status is stored in a
separate queue.

## Eager frame zeroing

Zeroing twice (free and allocation) is redundant for confidentiality but provides deterministic
defense in depth. A production allocator may defer or batch zeroing, provided no less-privileged
address space observes stale bytes.

## Full-file replacement versus offset writes

Replacement keeps atomicity teachable with four direct blocks. Offset writes introduce sparse regions,
partial-block read-modify-write, metadata ordering, and a more nuanced error contract.

## Cooperative versus preemptive ARM switching

Cooperation needs only an AAPCS call-frame switch and is suitable for a first bring-up. It cannot stop
a non-yielding task. Timer preemption requires vectors, interrupt-controller setup, exception frames,
critical sections, and a defined kernel/user privilege model.
