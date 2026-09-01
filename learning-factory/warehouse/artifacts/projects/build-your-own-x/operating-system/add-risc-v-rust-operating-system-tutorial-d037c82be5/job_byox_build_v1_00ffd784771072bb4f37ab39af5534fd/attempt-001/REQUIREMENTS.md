# Requirements

The crate name and public API supplied in `starter/src/` are part of the
contract. You may add private helpers and tests, but public signatures and error
variants must remain compatible.

## R1 — General behavior

- **R1.1** Use safe, stable Rust and the standard library only.
- **R1.2** Operations are deterministic for identical call sequences.
- **R1.3** Expected invalid input returns the documented typed error and never
  mutates observable state.
- **R1.4** Arithmetic derived from caller input is checked before use.

## R2 — Process table

- **R2.1** PIDs begin at 1, increase monotonically, and are never reused.
  Exhaustion returns `ProcessError::PidExhausted` without mutation.
- **R2.2** `spawn` creates a `Ready` process at the back of the ready queue.
- **R2.3** `schedule` demotes the current running process to `Ready`, appends it
  to the queue, then runs the oldest ready process. It returns `None` only when
  no process can run.
- **R2.4** `block_current` moves the running process to `Blocked`; calling it
  while idle returns `NoCurrent`.
- **R2.5** `wake` accepts only a `Blocked` process, makes it `Ready`, and enqueues
  it exactly once. Missing or incorrectly-state processes return a typed error.
- **R2.6** `exit_current` records the signed exit code in `Exited`, does not
  enqueue that process, and leaves the CPU idle.
- **R2.7** `validate` rejects duplicate/stale queue entries, a current/state
  mismatch, multiple running processes, or runnable processes omitted from the
  queue.

## R3 — Frame allocator

- **R3.1** `FrameAllocator::new(first, count)` owns precisely the half-open
  frame-number interval `[first, first + count)`. Overflow is rejected.
- **R3.2** Allocation returns the lowest available frame. Deallocation accepts
  only a currently allocated owned frame; foreign and double frees are errors.
- **R3.3** `free_count` and `allocated_count` are exact after success or failure.

## R4 — Sv39 page table

- **R4.1** Construction allocates one zeroed root frame. Failure returns
  `OutOfFrames` without fabricating a root.
- **R4.2** Map only 4 KiB-aligned, canonical Sv39 virtual addresses to 4
  KiB-aligned physical addresses. Leaf flags must include `VALID` plus at least
  one of `READ`, `WRITE`, or `EXECUTE`; `WRITE` without `READ` is invalid.
- **R4.3** Walk exactly three 9-bit VPN levels. Intermediate entries may contain
  only `VALID` and point to table frames owned by this page table.
- **R4.4** Mapping an already-mapped page returns `AlreadyMapped`. Any failed
  map—including partial intermediate allocation—restores both the page table
  and allocator to their pre-call state.
- **R4.5** Translation preserves the 12-bit page offset and enforces requested
  read/write/execute permission plus `USER` when `user == true`.
- **R4.6** Unmapping returns the physical frame number and leaf flags, clears the
  leaf, and frees now-empty non-root page-table frames bottom-up. It never frees
  the mapped data frame.
- **R4.7** Noncanonical addresses, malformed entries, absent mappings, and
  permission failures have distinct typed outcomes as exposed by the API.

## R5 — In-memory filesystem

- **R5.1** Inode 1 is an empty root directory. Inode numbers increase
  monotonically and are not reused.
- **R5.2** Paths are absolute UTF-8 strings. `/` is the sole empty-component
  path. Reject empty input, relative paths, repeated or trailing separators,
  `.` and `..`, NUL, and components over 255 bytes.
- **R5.3** `mkdir` and `create_file` require an existing directory parent and a
  missing final name. They return the created inode.
- **R5.4** `write` applies only to files, may extend with zero-filled holes, and
  rejects `offset + data.len()` overflow or a configured size-limit breach
  without mutation.
- **R5.5** `read` applies only to files, returns at most the requested length,
  returns an empty vector at/past EOF, and rejects range overflow.
- **R5.6** `list` returns immediate `(name, inode, kind)` entries in bytewise
  lexical name order.
- **R5.7** `remove` rejects `/`, nonempty directories, and missing paths. A
  successful removal deletes both the directory entry and inode atomically.
- **R5.8** `validate` proves root identity, directory-entry validity, unique
  reachability, kind consistency, no cycles, and absence of orphan inodes.

## R6 — Scope

This is a semantic kernel model, not a bootable kernel. Interrupt entry,
privileged CSR access, context-switch assembly, TLB shootdown, persistence,
crash recovery, concurrency, device drivers, and security hardening are outside
the implementation contract. `sealed/production/PRODUCTIONIZATION.md` records
the gap; completing this lab must not be represented as productionization.
