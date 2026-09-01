# Behavioral Requirements

This document specifies externally observable behavior. The public starter headers specify function signatures, object types, result types, and the spelling of status values. Use the closest declared status category named by the headers; do not invent a replacement API.

## 1. Common contract

1. All modules are in-memory and bounded. They must not allocate extra capacity dynamically or persist state in host services.
2. Initialization produces a deterministic empty state and may be called on storage whose prior bytes are arbitrary.
3. The void initializer declarations accept a null destination as a no-op. For status-returning calls, a null required pointer, out-of-range numeric value, unknown object identity, invalid state transition, duplicate object, or exhausted capacity is rejected with the corresponding public error category.
4. A rejected mutating operation leaves all observable module state unchanged. Output parameters are also left unchanged unless the public header explicitly documents an error result written to them.
5. Results must depend only on initialized module state and call arguments, not on addresses, wall-clock time, randomness, or prior contents of released storage.
6. Reinitializing a complete module discards its prior logical objects and restores its initial capacity. For virtual memory, the frame allocator and each address space have separate initializers: reset them together to discard a complete VM configuration. Calling the address-space initializer alone while that space still owns mapped frames is outside the supported lifecycle because it cannot return those frames to the separately owned allocator.
7. Tests and callers should supply one invalid condition at a time when asserting a particular error category. If a call has multiple simultaneous faults, which applicable error is returned is unspecified, but it must still be deterministic for a fixed state and arguments and must not mutate state or outputs.
8. Distinct pointer arguments in one call must designate non-overlapping storage and must not overlap the module objects passed to that call, unless an operation explicitly allows overlap below. In particular, output buffers and metadata outputs do not alias scheduler, VM, address-space, or RAMFS objects. The RAMFS write source is the one exception documented below.

## 2. Scheduler

### 2.1 Capacity and states

- The scheduler holds at most 8 live or unreaped process records.
- An initialized scheduler contains no processes and has no running process. Every record has PID 0, state `MICA_PROCESS_UNUSED`, and exit code 0; `next_pid` is 1 and `cursor` is `MICA_MAX_PROCESSES - 1` so the first cyclic scan begins at record 0.
- A process is observably in one lifecycle state: runnable, running, blocked, or exited-awaiting-reap. Free records are not processes.
- At most one process is running at a time.

### 2.2 Operations

**Spawn** creates one process with an identity distinct from every currently occupied record and places it in the runnable state. It succeeds while a record is available and fails when all 8 records are occupied, including records for exited processes that have not been reaped. A failed spawn consumes neither an identity nor a scheduling turn.

**Schedule** selects a runnable process using deterministic round-robin order. Resident records have a stable cyclic order. Selection begins strictly after the record selected by the preceding successful scheduling decision and wraps at the end. A process that was running when scheduling is requested becomes runnable for this decision; thus one runnable process may be selected repeatedly. If no process is runnable, scheduling reports the public no-runnable-process result and leaves no process running.

Observable examples, with processes spawned in the names shown and no intervening changes:

- `A, B, C` schedule as `A, B, C, A, ...`.
- If `B` is blocked, the eligible sequence is `A, C, A, C, ...`.
- Waking `B` makes it eligible at its existing place in the cyclic order; it does not receive an extra immediate turn.

**Block** changes the identified runnable or running process to blocked. Blocking the running process leaves no process running until a later scheduling operation. Blocking an already blocked or exited process is rejected.

**Wake** changes the identified blocked process to runnable. Waking a runnable, running, exited, or unknown process is rejected.

**Exit** changes an identified live process to exited-awaiting-reap and retains any exit information represented by the public API. If it was running, no process is running afterward. Exiting an already exited or unknown process is rejected.

**Reap** succeeds only for a process in exited-awaiting-reap, returns any exit information represented by the API, invalidates that process identity, and releases its record for later spawns. Reaping any other state or an unknown identity is rejected.

**Inspect/Get** copies the identified process's public information without changing scheduler state. The two declared spellings have identical behavior. An unknown or invalid identity and an invalid output pointer are rejected without changing the output.

PIDs are 32-bit values. Selection advances through nonzero values and skips every identity currently resident; numeric wrap is therefore defined and does not prevent spawn while a slot is free. The model guarantees uniqueness only among resident records. After a successful reap, callers must discard that PID; after an entire numeric wrap, the same value may identify a later process. Generation-stable handles are intentionally outside this bounded lab.

## 3. Virtual memory model

### 3.1 Address space and capacity

- There are exactly 16 virtual pages numbered 0 through 15.
- There are exactly 8 physical frames.
- Every page and frame contains exactly 64 bytes.
- If the public API accepts a linear virtual address, valid addresses are 0 through 1023 inclusive. Each valid address names one virtual page and one byte position within that page.
- Each mapped virtual page owns one frame. A page is either unmapped or mapped with a stored writable/read-only protection value.
- Allocator initialization marks all 8 frames available and clears every frame byte to zero. Address-space initialization marks every virtual page unmapped and read-only and stores frame index 0 in each inactive entry.

### 3.2 Operations

**Map** maps one currently unmapped valid virtual page to the lowest-numbered available frame. The newly allocated page reads as zero in all 64 byte positions, even when its frame was previously used by another mapping. Its protection is exactly the writable/read-only value requested by the call. Mapping an already mapped page, an invalid page, or mapping with no free frame is rejected without changing mappings, frame availability, or data.

**Unmap** removes an existing mapping and returns its frame to the available pool. The page becomes inaccessible immediately. Unmapping an invalid or already unmapped page is rejected. Data from an unmapped page must never become observable through a later mapping; the later successful map is zero-filled.

**Read** of a valid address in a mapped page returns the byte last successfully written there, or zero if no successful write has occurred since that mapping was created. Reading an invalid address or an unmapped page is rejected and does not modify the caller's destination.

**Write** of a valid address in a mapped writable page stores exactly the requested byte. Writing an invalid address, an unmapped page, or a read-only mapping is rejected without changing any byte. A failed write cannot alter protection or frame accounting.

Writes to one mapped page must not affect another mapped page. Unmapping one page must not invalidate any other mapping.

## 4. Flat RAM filesystem

### 4.1 Capacity and names

- The filesystem holds at most 8 files.
- Each file has an independent maximum logical length of 128 bytes, including exactly 128 as a valid length.
- A filename is 1 through 15 bytes long, excluding its terminating null byte.
- A valid filename is null-terminated within that limit, contains no `/` byte, and is neither `.` nor `..`. A null pointer, empty name, unterminated or overlength name, or path-like name is invalid. Because the C API has no buffer-length argument, a caller testing an unterminated name must provide at least `MICA_NAME_MAX + 1` readable bytes; passing a pointer whose readable object ends sooner is outside the C memory-safety precondition.
- Names are compared exactly and case-sensitively. No directory traversal, normalization, aliases, or implicit extensions exist.
- Initialization produces an empty filesystem: every record is unused, every stored name and data byte is zero, and every logical size is zero.

### 4.2 Operations

**Create** adds one empty file with the exact valid name supplied. It rejects an existing name, an invalid name, or an attempt to exceed 8 files. A failed create does not consume a file record.

**Write** stores a byte sequence beginning at the supplied offset. An offset from 0 through 128 with length zero succeeds without changing the file and does not require a data byte. For a positive length, the complete interval must fit: the offset must be at most 128 and the length must be at most `128 - offset`. The data pointer must provide the complete sequence. It may overlap a data array inside the same RAMFS object; behavior is as though all source bytes were captured before any file byte changed. If the offset is beyond the old logical end, the gap becomes zero bytes. A successful write sets the length to the greater of the old length and `offset + length`; it does not truncate an existing suffix. An invalid interval, data argument, name, or missing file is rejected atomically: the old length and every old byte remain observable afterward.

**Read** begins at the supplied offset and copies the smaller of the destination capacity and the bytes remaining in the file. It reports the exact number copied; partial reads are valid. An offset equal to the file length succeeds and reports zero, while an offset beyond the file length is rejected. A zero-capacity read copies nothing and does not require a data destination, but it still requires the result-count output declared by the API. Bytes are binary and may include zero. Invalid names, missing files, invalid offsets, and invalid output arguments leave the destination and result count unchanged.

**Unlink** removes an existing file with the exact supplied name and releases its record. Later creation may reuse the capacity, but no byte from the removed file may be observable in the new file. Invalid names and missing files are rejected without changing any other file.

**Stat** reports the current logical byte length of an existing file without changing it. Invalid names, missing files, and invalid output pointers are rejected without changing the output.

Operations on one file do not reorder, rename, truncate, or modify another file. File contents exist only for the lifetime of the initialized in-memory filesystem object.

## 5. Build and validation

The starter must compile as C11 with the supplied build rules:

```bash
make -C starter build
make -C starter test
```

Success requires both commands to pass and all behavior above to hold, including cases not enumerated by the public examples. Compiler-specific extensions, undefined behavior, and reliance on zero-initialized caller storage do not satisfy the contract.
