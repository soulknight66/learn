# Tradeoffs

The reference optimizes for deterministic teaching behavior and auditability, not kernel throughput or compatibility.

## Fixed arrays versus dynamic structures

Embedding every resource makes exhaustion testable and removes allocator failure, lifetime ambiguity, and hidden state. It also imposes hard limits and exposes relatively large objects to callers. A production kernel would usually allocate process metadata, page tables, and file storage from separate managed pools.

## Cyclic scan versus an explicit run queue

Scanning eight stable slots makes round-robin order obvious, preserves a blocked process's place, and needs no queue links to repair during exit. Its cost is proportional to the record limit even when only one process is runnable. An intrusive ready queue would make selection `O(1)` but would add ordering edge cases for block, wake, and deletion.

## Monotonic PIDs versus slot identities

Using `next_pid` prevents immediate stale-handle aliasing when a slot is reaped and reused. The implementation also skips currently live values after wrap. A finite 32-bit namespace cannot remember every historical PID forever; production designs commonly combine a wider counter with generation-tagged handles and carefully define reuse.

## Concrete types versus opaque handles

Concrete structs avoid allocation and let learners see the model. They also let callers forge states, duplicate mappings by copying structs, or mutate file metadata. The reference detects several impossible states, but it cannot establish full ownership because the API has no private metadata. Opaque objects and accessor functions would enforce a stronger boundary.

## Lowest-free scan versus a free list or bitmap primitive

Lowest-index allocation is deterministic and takes at most eight probes. A larger allocator should use a bitmap hierarchy, free list, or buddy allocator and would need synchronization. Those designs trade code and metadata complexity for scalable allocation.

## Clearing on both release and allocation

VM frames are zeroed on unmap and again on map. Clearing twice is redundant for ordinary reuse, but release clearing limits residual-data lifetime while allocation clearing locally guarantees the published contract even if future release paths change. A production implementation might use lazy zero pages or hardware-assisted clearing while retaining the same security property.

RAMFS unlink similarly clears the whole record. This is inexpensive at 128 bytes but does not constitute certified media erasure; the filesystem is only volatile object storage.

## Staged file writes versus direct copy

A 128-byte local staging buffer ensures no file mutation precedes a complete bounds/metadata check and makes overlapping input deterministic. It consumes stack space on every write. An API with non-aliasing guarantees could copy directly; a larger filesystem would use chunked transactional updates, copy-on-write, or a journal rather than a file-sized stack buffer.

## One status enum versus richer diagnostics

Eight stable values are easy to test and usable without libc. They deliberately omit the failing index, requested size, corruption cause, and recovery advice. Production diagnostics should add structured context while preserving a small, reliable kernel-facing error code.
