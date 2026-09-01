# Concepts

## Processes as an explicit state machine

A scheduler is easier to reason about when the process table is authoritative
and the ready queue is only an index over it. A transition updates both views
as one operation. Round-robin fairness is then a FIFO property: on a scheduling
point, the old runner goes behind every process that was already ready.

The model deliberately separates `Blocked` from `Exited`. A blocked process may
be made runnable by an event; an exited process is durable history and can
never re-enter the queue. Monotonic PIDs avoid accidental aliasing between old
handles and new processes.

## Sv39 virtual memory

Sv39 divides a canonical 64-bit virtual address into a 12-bit page offset and
three 9-bit virtual-page indices. Each page-table page has 512 64-bit entries.
An intermediate valid entry points to the next table; a leaf entry has at least
one of read, write, or execute permission and identifies a physical page.

Canonicality matters: legal addresses sign-extend virtual-address bit 38
through bits 63..39. Merely masking high bits would make distinct invalid
addresses alias. Likewise, write-without-read is a reserved Sv39 encoding in
this model and is rejected.

Mapping is a small transaction. A walk may allocate two intermediate frames
before discovering an error. Correct failure handling must undo newly linked
entries and return those frames, while never disturbing tables that existed
before the call. Unmapping performs the dual bottom-up reclamation.

Translation combines the mapped physical page number with the original offset
only after checking leaf validity and access permissions. Page-table ownership
is distinct from ownership of the mapped data frame: unmapping frees empty
table pages, not user data.

## Filesystems as graphs with a tree policy

An inode stores object identity and type; a directory maps names to inode
numbers. The path resolver walks directory edges from inode 1. This lab forbids
hard links, so the reachable graph must be a tree: every non-root inode has one
parent and every allocated inode is reachable exactly once.

Path syntax is validated before traversal. That prevents `a//b`, `.` and `..`
from creating multiple spellings of an object and makes mutation rollback
tractable. Ordered maps give deterministic directory listings and reproducible
tests.

Writing beyond EOF creates a sparse-looking logical hole, represented here by
explicit zero bytes. Real filesystems would map logical blocks to storage and
must handle partial I/O and crash consistency; those mechanisms are outside
this in-memory model.

## Cross-cutting lesson: failure atomicity

Kernel code often changes several structures for one logical operation. The
safe pattern is validate first, reserve resources second, publish last, and
roll back reservations in reverse order if publication cannot complete. Tests
should snapshot counts and visible state around every injected or natural
failure—not just check the returned error.
