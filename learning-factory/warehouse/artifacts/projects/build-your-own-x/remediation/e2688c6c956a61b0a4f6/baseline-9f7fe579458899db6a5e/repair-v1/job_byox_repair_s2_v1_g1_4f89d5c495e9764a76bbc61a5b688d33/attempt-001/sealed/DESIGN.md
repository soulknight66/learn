# Reference design answers

## Processes

The central invariant is the equivalence between `current_slot >= 0` and
exactly one `PROC_RUNNING` entry at that index. Every library transition is
single-threaded, so the reference scheduler first identifies a candidate
without mutation, then changes the old process to ready, the candidate to
running, and finally publishes the index. Rejections occur before those
writes.

Exit retains PID, parent, entry point, and exit code in a zombie. Reap is the
only transition that clears identity and makes capacity reusable. This lets a
parent observe termination and avoids confusing “not running” with “never
existed.” PIDs are monotonic and are not recycled even when a slot is.

The compact ABI has only a current-slot cursor. Blocking or exiting clears it,
so the next schedule begins at slot zero. That is deterministic but can favor
low slots after frequent sleeps. A stronger design would retain a separate
`last_scheduled_slot` cursor; changing that now would change the exercise ABI.

## Virtual memory

Virtual and physical alignment are independent because the two addresses are
members of different namespaces. Translation divides the virtual address into
an aligned base and an offset, looks up the base, verifies that all requested
permission bits are present, then adds the unchanged offset to the frame base.

Physical aliases are intentionally allowed. They can model shared libraries,
shared memory, and copy-on-write setup, but a real kernel must coordinate cache
attributes, ownership, writable aliases, and unmapping lifetime. Duplicate
virtual pages are rejected because translation would otherwise be ambiguous.

A permission mask is valid when it is nonzero and contains only known bits. It
is satisfied when `(mapping & request) == request`. These are separate checks:
an execute request is well-formed even when a particular mapping denies it.

## Filesystem

Names are validated with a bounded scan of at most 32 bytes. All operations
validate the name before lookup so malformed requests have a stable
`OS_ERR_INVALID` result. Create scans the complete table before mutation,
giving duplicate-name detection priority over full capacity.

Write checks `offset > capacity || count > capacity - offset`, avoiding an
overflow-prone addition. A zero-length write at an offset through capacity is
a successful no-op and never extends the file. A nonempty write beyond the old
end zero-fills the gap before copying, after the full request has been shown to
fit. Unlink clears metadata and data to make slot reuse deterministic and to
avoid stale-byte disclosure.

With concurrent callers, process transitions need a process-table lock,
mappings need an address-space lock plus hardware TLB coordination, and RAMFS
needs namespace serialization followed by per-file I/O locking. Lock ordering
would become part of the contract.
