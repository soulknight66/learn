# Sealed tradeoffs

## Semantic model versus bootable kernel

Running as a normal Rust library makes transitions deterministic and allows
ordinary unit tests. It also removes the hardest hardware concerns: trap
entry, privilege transitions, address-space activation, register save/restore,
TLB synchronization, and device I/O. The model is useful as an executable
specification, not as a substitute for those mechanisms.

## Ordered collections

`BTreeMap` and `BTreeSet` provide stable lowest-ID allocation and lexical
listing without hashing dependencies. They allocate dynamically and have
`O(log n)` operations, so they are unsuitable in interrupt paths or early boot
without a kernel allocator. A production design would often use intrusive
queues, bitmaps, radix trees, and slab-backed objects.

## Monotonic identities

Never reusing PIDs or inode numbers makes stale-handle aliasing impossible in a
short exercise. Finite machine integers eventually exhaust. Real systems
usually reuse bounded identifiers while pairing internal objects with
generations or reference-counted handles.

## Eager file-hole storage

Zero-filling a gap gives simple byte semantics and deterministic reads, but a
large offset consumes proportional memory. A block map can represent holes
sparsely, at the cost of block allocation, partial-block updates, and more
complex rollback.

## Caller-supplied frame allocator

Passing the allocator makes ownership effects visible to tests and lets maps
roll back reservations. It also lets a caller mistakenly supply a different
allocator to `unmap`. The reference preflights all reclamation before clearing
the leaf, so this misuse is a typed atomic failure. A stronger API would bind
an allocator capability to the address space for its lifetime.

## No superpages

Only level-zero 4 KiB leaves are accepted. That keeps reclamation and offset
logic focused, but does not model Sv39 2 MiB or 1 GiB leaves, alignment rules,
or splitting/coalescing.
