# Sealed design rationale

This document contains reference answers and is not learner-visible.

## Core state invariants

At most one task is `RUNNING`. `current_slot == -1` exactly when no task is running; otherwise it
indexes that running task. Only a running task may have nonzero `quantum_left`. `last_slot` remembers
selection history even after exit so circular fairness is independent of slot lifecycle.

A PTE is published only after its physical frame is zeroed and marked used. Every present PTE owns
exactly one used frame; frames are never shared in this model. Exit converts the task to a zombie only
after its PTEs and frames are cleared. Reaping then discards the remaining identity and exit evidence.

Every used filesystem block belongs to exactly one used inode direct pointer. The number of
meaningful pointers is `ceil(size / block_size)`. Unused pointer entries are `-1`, free blocks are
zeroed, and inode names are unique.

## Scheduler answer

PID allocation is monotonic while slots are recyclable, so a stale PID cannot silently name a new
occupant of the same slot. Waking occurs before selection and idle ticks advance `now`, allowing a
blocked-only system to make progress. A selected task keeps the CPU across `CONTINUE` results until
its counter reaches zero. Circular scanning begins after the most recently selected slot; this yields
`A,A,B,B,A,B` for two three-step tasks at quantum two.

The callback is a host testing seam rather than an emulated instruction. A callback may block or exit
through the kernel API; the post-callback transition is applied only if the same slot remains running.

## Virtual memory answer

Translation divides an address by `MK_PAGE_SIZE` for the virtual page and takes the remainder for the
offset. Multi-page operations first prove the entire numeric range, all PTE presence, frame ownership,
and permission. Only a second pass copies chunks bounded by the end of each page. That two-pass shape
is what prevents a write to page N before discovering page N+1 is invalid.

Task termination is the ownership boundary for reclamation; a zombie retains exit evidence but no
address-space resources. Zeroing on both release and allocation gives deterministic reuse and avoids
data remnants in the educational model.

## Filesystem answer

Replacement stages all input bytes before touching blocks, which handles source pointers into the
file being replaced. It prepares a candidate block vector without mutating allocation state: retain
the old prefix, then choose the lowest free blocks for growth. Failure during this preparation leaves
the inode and bytes untouched. Once capacity is known, commit cannot fail: zero and populate candidate
blocks, release the unused old suffix, then publish pointers and size.

This is operation-level failure atomicity, not crash consistency. RAM can disappear and there is no
write-ahead log or device barrier.

## ARM answer

At a cooperative AAPCS call boundary, `r4-r11`, `sp`, and the resume address in `lr` are sufficient
for integer-only tasks; caller-saved registers are already allowed to be clobbered. A preempting IRQ
can arrive between arbitrary instructions and therefore needs the exception return state plus all
interrupted general registers, status register, and any enabled floating-point/SIMD context.

The sealed adapter manufactures an initial saved frame whose `lr` points at a non-returning bootstrap.
The first restore therefore enters the task on its own aligned stack. Subsequent yields save back into
that same frame shape. This does not constitute an exception or privilege boundary.
