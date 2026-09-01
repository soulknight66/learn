# PebbleOS behavioral contract

Implement `starter/src/pebble.c` against the declarations in `starter/include/pebble.h`. The words **must**, **must not**, and **unchanged** are testable requirements.

## Global rules

- All state lives in one caller-owned `pebble_kernel_t`; separate instances must never affect one another.
- Functions must tolerate every value representable by their parameter types. A nonzero length requires a non-null buffer.
- Zero-length reads and writes succeed with `0` and may receive a null buffer, but process identity and descriptor/address bounds must still be valid. Filesystem descriptor access mode is still checked. A zero-length virtual-memory range touches no page and may start exactly one byte past the final page (the address-space limit).
- Negative results are `pebble_status_t` values. Functions returning a PID, descriptor, or byte count return a nonnegative/positive success value as documented.
- Unless stated otherwise, any failing operation leaves the entire kernel byte-for-byte unchanged. Diagnostic text written by `pebble_check()` is outside the kernel and is the sole exception.
- No API may read or write beyond the fixed arrays, overflow an arithmetic expression, invoke undefined behavior, or depend on host endianness.

## Milestone 1: initialization and processes

`pebble_init()` resets the complete object. All process slots are `PEBBLE_PROC_UNUSED`, all frame reference counts are zero, all files and descriptors are unused, `current_slot` is `-1`, `schedule_cursor` and `ticks` are zero, and the first successful PID is `1`.

`pebble_process_create()` uses the lowest-numbered unused process slot, assigns the next monotonically increasing positive PID, sets the process to `READY`, and returns that PID. It returns `PEBBLE_ERR_NO_SPACE` if the table is full and `PEBBLE_ERR_OVERFLOW` rather than wrapping the PID sequence. PIDs are not reused during a kernel instance's lifetime.

State transitions are:

```text
READY or RUNNING --block--> BLOCKED --wake--> READY
READY, RUNNING, or BLOCKED --exit--> ZOMBIE --reap--> UNUSED
```

Calls outside those edges return `PEBBLE_ERR_STATE`. Exiting stores the supplied status, releases every mapping, closes every descriptor, and clears `current_slot` if necessary. Reaping optionally copies the status when its output pointer is non-null. A zombie retains its PID and exit status until reaped. Unknown, unused, and reaped PIDs return `PEBBLE_ERR_NOT_FOUND`.

## Milestone 2: deterministic scheduling

`pebble_schedule()` is the only operation that increments `ticks`, once per call including an idle call. It first changes the current `RUNNING` process back to `READY`, then scans from `schedule_cursor`, wrapping once through all slots. It selects the first `READY` process, marks it `RUNNING`, records its slot, advances the cursor to the following slot, and returns its PID.

If no process is ready, it sets `current_slot` to `-1` and returns `PEBBLE_ERR_NOT_FOUND`. Blocked and zombie processes are never selected. There can be at most one running process.

## Milestone 3: virtual memory

The virtual address space has `PEBBLE_VIRTUAL_PAGES` pages of `PEBBLE_PAGE_SIZE` bytes. `pebble_vm_map()` accepts a virtual page index and a nonempty subset of `PEBBLE_PAGE_READ | PEBBLE_PAGE_WRITE`. It allocates the lowest-numbered free frame, zero-fills it, and installs one present mapping. Mapping an existing page returns `PEBBLE_ERR_STATE`; an invalid page or flag set returns `PEBBLE_ERR_INVALID`; exhaustion returns `PEBBLE_ERR_NO_SPACE`.

`pebble_vm_unmap()` releases a present mapping and zeroes a frame when its last reference disappears. An absent page returns `PEBBLE_ERR_NOT_FOUND`.

`pebble_vm_read()` and `pebble_vm_write()` may span pages. The half-open range `[address, address + length)` must fit in the virtual address space, every touched page must be present, and each must grant the requested permission. Invalid ranges return `PEBBLE_ERR_INVALID`, absent pages return `PEBBLE_ERR_NOT_FOUND`, and protection failures return `PEBBLE_ERR_PERMISSION`.

Validate a complete transfer before copying any byte. A failed write must not alter bytes, mappings, flags, reference counts, or the source buffer. Successful reads and writes return the requested byte count as `int32_t`.

## Milestone 4: fork and copy-on-write

`pebble_process_fork()` accepts a live parent in `READY`, `RUNNING`, or `BLOCKED` state. It creates a `READY` child in the lowest free slot with a fresh PID. Each present page is initially shared with the parent and increments exactly one frame reference count.

Read-only mappings remain read-only. A writable parent mapping becomes non-writable and copy-on-write in both parent and child. Existing copy-on-write mappings remain copy-on-write. The child receives copies of the parent's open descriptor records, including cursor positions; these cursors subsequently move independently. Each copied descriptor increments the file's open count. Scheduler state and the parent's lifecycle state do not otherwise change.

Writing a copy-on-write page allocates the lowest free frame, copies the complete old page, changes only the writer's mapping to writable/non-copy-on-write, and decrements the old reference. If that mapping is already the sole reference, the write may restore write permission in place. A cross-page write must reserve enough free frames for all required splits before changing anything; otherwise it returns `PEBBLE_ERR_NO_SPACE` transactionally.

Fork table exhaustion or PID overflow is transactional. No dynamic allocation is permitted.

## Milestone 5: bounded filesystem

The filesystem is a flat namespace of at most `PEBBLE_MAX_FILES` regular files. A valid name has 1 through `PEBBLE_MAX_NAME` bytes, contains no `/`, and is neither `.` nor `..`. Names are exact, case-sensitive byte strings.

`pebble_fs_open()` requires a live process and at least one of `PEBBLE_OPEN_READ` or `PEBBLE_OPEN_WRITE`. Unknown flag bits are invalid. `CREATE` and `TRUNCATE` require write permission. `CREATE` makes a missing file in the lowest free file slot; without it, a missing name returns `PEBBLE_ERR_NOT_FOUND`. `TRUNCATE` clears an existing file only after all validations and resource checks pass. The lowest free process descriptor is returned with cursor zero.

If either the process descriptor table or file table is full, open returns `PEBBLE_ERR_NO_SPACE` without creating or truncating anything. Opening increments `open_count`; closing decrements it and clears the descriptor. Forked descriptor copies count as distinct opens.

Successful truncation also resets to zero every existing descriptor cursor that names the truncated file. This differs from POSIX, but preserves this model's invariant that no cursor lies beyond end-of-file.

`pebble_fs_read()` and `pebble_fs_write()` enforce descriptor access flags. Reads stop at end-of-file and advance by bytes returned. Writes begin at the cursor, may overwrite existing bytes, extend the file, and advance by bytes written. A write whose ending position exceeds `PEBBLE_MAX_FILE_BYTES` fails entirely with `PEBBLE_ERR_NO_SPACE`. Seeking is allowed from zero through the current file size; sparse seeks are invalid. `pebble_fs_size()` reports the current size without moving the cursor.

`pebble_fs_unlink()` removes a named file only when its `open_count` is zero; otherwise it returns `PEBBLE_ERR_BUSY`. Removed storage is cleared. There are no directories, devices, links, permissions, or host-backed files.

## Milestone 6: invariant checking

`pebble_check(kernel, why, capacity)` returns `PEBBLE_OK` for a valid model and `PEBBLE_ERR_CORRUPT` for a detected invariant violation. It must safely handle a null kernel. When `why` is non-null and capacity is nonzero, it writes a nul-terminated, deterministic short reason; on success it writes an empty string. It never mutates the kernel.

At minimum it checks:

- process states and positive uniqueness of every non-unused PID;
- exactly zero or one running process and agreement with `current_slot`;
- valid schedule cursor and monotonic-PID bookkeeping;
- present page flags, frame indices, and exact derived frame reference counts;
- zero data in every unreferenced frame;
- descriptor validity and exact derived file open counts;
- file name validity and uniqueness, size bounds, cleared unused records, and descriptor cursor bounds.

## Completion gates

```sh
make -C starter clean all
make -C starter public
```

Both commands must exit zero with the prescribed warnings enabled. Independent tests may build with optimizations disabled and with host sanitizers. A host pass does not establish Raspberry Pi bootability, concurrency safety, security, real MMU correctness, or production readiness.
