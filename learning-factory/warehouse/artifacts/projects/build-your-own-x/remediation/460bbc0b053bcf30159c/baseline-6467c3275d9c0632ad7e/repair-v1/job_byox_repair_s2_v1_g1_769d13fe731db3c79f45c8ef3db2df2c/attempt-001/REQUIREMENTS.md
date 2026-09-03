# CairnOS behavioral contract

Implement every function declared by `starter/include/cairn.h` in `starter/src/cairn.c`. Do not
change public constants, layouts, function names, or status values. The implementation must compile
both as hosted C11 and as freestanding 32-bit C without libc, heap allocation, floating point,
threads, or global mutable state.

Unless a function explicitly says otherwise:

- a null required pointer, invalid boolean (anything other than 0 or 1), malformed name, out-of-range
  index/address, or arithmetic overflow returns `CAIRN_ERR_INVALID`;
- error returns must not modify the kernel or any output parameter;
- lookup failures return `CAIRN_ERR_NOT_FOUND`;
- fixed tables are scanned from index zero and the first available slot is used;
- all mutations must leave `cairn_validate` returning `CAIRN_OK`.

## Initialization and process lifecycle

`cairn_init(kernel)` resets the complete object when `kernel` is non-null. PIDs begin at 1,
`current_slot` is -1, every process and inode slot is unused, and every frame owner is -1. Passing
null is a no-op.

`cairn_spawn(kernel, entry, pid_out)` requires `entry < CAIRN_USER_TOP`. It uses the first `EMPTY` or
`EXITED` process slot, resets that slot, assigns the next monotonically increasing positive PID, sets
the state to `READY`, records the entry address, and returns the PID. A full table returns
`CAIRN_ERR_NO_SPACE`.

`cairn_schedule(kernel, pid_out)` implements cyclic round-robin selection:

1. If the cursor (`current_slot`) names a `RUNNING` process, demote it to `READY`.
2. Scan cyclically beginning immediately after the cursor. With cursor -1, begin at slot zero.
3. Mark the first `READY` process `RUNNING`, set the cursor to its slot, and return its PID.

If no process is ready, return `CAIRN_ERR_NO_RUNNABLE` without changing state. Re-selecting the only
runnable process is valid. There may never be more than one `RUNNING` process.

`cairn_block_current` changes the cursor's `RUNNING` process to `BLOCKED` but preserves the cursor for
the next cyclic scan. `cairn_wake(kernel, pid)` changes exactly a `BLOCKED` process to `READY`.
`cairn_exit_current(kernel, code)` changes the running process to `EXITED`, records `code`, closes all
of its descriptors, and releases all of its frames. Lifecycle calls made from the wrong state return
`CAIRN_ERR_BAD_STATE`. `cairn_process_state` reports the state of an existing PID.

## Virtual mappings

The model has `CAIRN_MAX_FRAMES` exclusive physical frames and up to `CAIRN_MAX_MAPPINGS` mappings per
non-exited process. It models policy and translation; it does not program a hardware MMU.

`cairn_map(kernel, pid, virtual_address, frame, writable)` requires:

- an existing process in `READY`, `RUNNING`, or `BLOCKED` state;
- a page-aligned virtual address below `CAIRN_USER_TOP`;
- a frame index below `CAIRN_MAX_FRAMES`; and
- `writable` equal to 0 or 1.

A virtual page already mapped by that process returns `CAIRN_ERR_EXISTS`. A frame owned by any mapping
returns `CAIRN_ERR_BUSY`. If neither condition holds but the process mapping table is full, return
`CAIRN_ERR_NO_SPACE`. On success, install the mapping and record the PID as frame owner.

`cairn_unmap` requires an aligned in-range virtual address. It removes that process's mapping and
releases its frame. `cairn_translate(kernel, pid, virtual_address, write, physical_out)` accepts any
byte address below `CAIRN_USER_TOP`; it combines the mapped frame base with the page offset. A missing
page returns `CAIRN_ERR_NOT_FOUND`, and a write through a read-only mapping returns
`CAIRN_ERR_PERMISSION`.

## In-memory filesystem and descriptors

The root contains at most `CAIRN_MAX_FILES` regular files. A valid name is a non-empty NUL-terminated
byte string shorter than `CAIRN_NAME_CAP` with no `/` byte. There are no directories, links, devices,
or persistence. Each file holds at most `CAIRN_FILE_CAP` bytes.

`cairn_create` rejects an existing name with `CAIRN_ERR_EXISTS`. `cairn_unlink` rejects an open file
with `CAIRN_ERR_BUSY`; otherwise it clears that inode. `cairn_open` associates the named inode with
the first free descriptor of an existing non-exited process, sets its cursor to zero, and returns the
descriptor index. A full descriptor table returns `CAIRN_ERR_NO_SPACE`.

`cairn_close` clears a valid open descriptor. `cairn_seek` accepts positions from zero through the
current file size; sparse seeks are invalid. `cairn_write` copies the complete requested byte range at
the descriptor cursor, advances the cursor, grows size when needed, and reports the copied count.
Writes are all-or-nothing: a range beyond capacity or an addition overflow returns
`CAIRN_ERR_NO_SPACE`. `cairn_read` copies up to the requested count or EOF, advances the cursor, and
reports the actual count; reading at EOF succeeds with count zero. A null data buffer is valid only
when the requested count is zero.

Descriptors belong to processes but may be used while their owner is ready, running, or blocked.
Multiple descriptors may refer to one inode and have independent cursors.

## Invariant checker

`cairn_validate(kernel)` is read-only. It returns `CAIRN_OK` only when all structural facts hold,
including:

- cursor and enum values are in range, PIDs are positive and unique, every non-empty process entry
  is below `CAIRN_USER_TOP`, and at most one process runs;
- every running process agrees with the cursor, and exited processes own no mappings/descriptors;
- virtual pages are unique within a process;
- each present mapping has exactly one matching frame-owner entry and each owned frame has exactly one
  mapping;
- inodes have valid unique names and bounded sizes; and
- every open descriptor names a live inode and has a cursor no greater than its size.

Any violation, or a null pointer, returns `CAIRN_ERR_CORRUPT`. The checker must terminate safely even
when public fields contain arbitrary bytes; never use an unchecked field as an array index.

## Completion criteria

A submission is complete when it builds warning-free with the provided strict flags, passes the
public tests, adds meaningful learner-authored tests, links as the freestanding kernel target, and
does not use libc symbols in `cairn.c`. Passing visible tests alone is insufficient.
