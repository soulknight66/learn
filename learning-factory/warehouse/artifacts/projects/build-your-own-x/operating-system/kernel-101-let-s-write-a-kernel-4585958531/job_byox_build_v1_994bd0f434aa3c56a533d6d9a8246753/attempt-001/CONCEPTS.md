# Concepts, revealed by stage

## 1. Frames are ownership records

Physical memory management begins with an ownership question: which fixed-size chunks are free?
This lab represents that fact directly with one byte per frame. Real kernels often use bitmaps,
buddy trees, or free lists, but the essential invariants are the same: allocation transfers one
free frame to one owner, and freeing transfers it back exactly once.

The lowest-free rule is not a performance prescription. It makes behavior reproducible and makes
leaks easy to diagnose.

## 2. A scheduler is a state machine

A process is not merely a function pointer. It moves through controlled states. `READY` means it
may be selected, `RUNNING` means it currently owns the simulated CPU, and `BLOCKED` means it is
waiting for an event. Round-robin fairness depends on retaining a cursor even when the current
process blocks or exits.

Separate identity from storage: table slots can be reused, but PIDs must not silently identify a
different process later.

## 3. Virtual memory composes policies

A page mapping binds a virtual page to a physical frame and a permission set. Translation keeps the
in-page offset while changing the page number. A robust mapping operation has two resources to
consider—the mapping table and frame allocator—so failure ordering matters. Validate everything
that can fail before acquiring a frame.

Permissions are a set inclusion check: a mapping satisfies a request only if it contains every
requested bit.

## 4. A filesystem is a namespace plus bytes

This RAM filesystem avoids disks and directories but still exposes core filesystem ideas: unique
names, bounded metadata slots, byte-preserving reads/writes, and unlinking. Names and file contents
have different limits. Empty content is valid; an empty name is not.

Returning an error before copying prevents callers from observing partial reads and gives each
operation a simple transactional boundary.

## 5. Kernel code has two execution environments

The subsystem code is compiled both into a host test process and a freestanding ELF. The host gives
fast diagnostics; the freestanding build catches accidental library and ABI dependencies. Neither
alone proves that a kernel boots correctly on hardware.
