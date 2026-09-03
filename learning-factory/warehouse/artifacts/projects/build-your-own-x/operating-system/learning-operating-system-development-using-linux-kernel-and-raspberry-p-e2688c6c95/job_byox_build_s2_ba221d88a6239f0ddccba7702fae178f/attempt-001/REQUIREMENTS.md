# MiniOS behavioral contract

Implement the declarations in `starter/include/minios.h`. Numeric enum values
and structure layouts are part of the test ABI and must not change.

## General rules

- Every status-returning function returns one of the declared `os_status_t`
  values. A null pointer passed to a void initializer is a harmless no-op.
- A null required pointer returns `OS_ERR_INVALID`. An output pointer is
  required unless a parameter is explicitly described as optional.
- On any error, an operation leaves subsystem state unchanged. Output scalars
  are set to a harmless value (`0` or `NULL`) when their pointer is valid.
- Storage is bounded by the header constants; no dynamic allocation is used.
- Initializers fully establish deterministic state even if the input object
  previously contained arbitrary bytes.

## Process table

`proc_table_init` creates eight unused slots, sets the next PID to 1, and sets
`current_slot` to `-1`.

`proc_spawn(table, parent_pid, entry_point, out_pid)` occupies the lowest-index
unused slot in `PROC_READY` state and assigns the next monotonically increasing
nonzero PID. `parent_pid == 0` denotes the kernel. A nonzero parent must name a
non-zombie process: an absent parent returns `OS_ERR_NOT_FOUND`, while a zombie
parent returns `OS_ERR_STATE`. `entry_point` is opaque and may be zero. Full capacity
returns `OS_ERR_FULL`. PID exhaustion (the next value has wrapped to zero) also
returns `OS_ERR_FULL`. Validation order is required pointers, parent, PID
exhaustion, then slot capacity.

`proc_schedule` performs one preemptive round-robin decision. A current
`PROC_RUNNING` process first becomes `PROC_READY`. Search starts immediately
after the previously current slot and wraps once; the first ready process
becomes running. With no ready process, return `OS_ERR_NOT_FOUND`, output PID
zero, and set `current_slot` to `-1`. Exactly one process may be running.

`proc_block` accepts only the running process and changes it to
`PROC_BLOCKED`, clearing `current_slot`. `proc_wake` accepts only a blocked
process and makes it ready. `proc_exit` accepts a ready, running, or blocked
process, records the supplied exit code, and makes it a zombie; exiting the
current process also clears `current_slot`. `proc_reap` accepts only a zombie,
returns its exit code, and resets that slot to unused. Looking up PID zero or
an absent PID returns `OS_ERR_NOT_FOUND`.

## Virtual memory model

The model contains 16 virtual pages of 4096 bytes, 32 physical frames, and room
for eight simultaneous mappings. A mapping relates one virtual page to one
physical frame and carries a nonempty subset of
`VM_READ | VM_WRITE | VM_EXEC | VM_USER`.

`vm_space_init` clears all mappings. `vm_map` requires aligned virtual and
physical base addresses within their respective modeled ranges. Duplicate
virtual pages return `OS_ERR_EXISTS`; a full mapping table returns
`OS_ERR_FULL`; unknown or empty permission bits return `OS_ERR_INVALID`.
Input validation precedes duplicate detection, which precedes the capacity
result.

`vm_translate(space, virtual_address, required_permissions, out_physical)`
accepts any byte address within the virtual range. The requested permission
mask must be nonempty and contain only known bits. Translation preserves the
page offset. An absent page returns `OS_ERR_NOT_FOUND`; insufficient mapping
permissions return `OS_ERR_PERM`.

`vm_unmap` requires an aligned in-range virtual page base. It removes an
existing mapping or returns `OS_ERR_NOT_FOUND`.

## RAM filesystem

The filesystem holds eight regular files. A valid name begins with `/`, has
1–30 following characters, and contains no other `/`. Allowed name characters
are ASCII letters, digits, `.`, `_`, and `-`. The root name `/` is invalid.

`fs_init` removes all files. `fs_create` uses the lowest-index free slot and
creates an empty file; duplicate names return `OS_ERR_EXISTS` and full
capacity returns `OS_ERR_FULL`. Name validation precedes duplicate detection,
which precedes the capacity result. `fs_stat` returns the current byte length.

Each file has a 256-byte capacity. `fs_write` accepts offsets from zero through
256. The entire `[offset, offset + count)` range must fit; check this without
overflow. A write that starts beyond the old end zero-fills the gap. A
zero-length write is valid and never changes file length. Any rejected write
leaves bytes and length unchanged.

`fs_read` returns up to `count` bytes from the offset, stopping at end of file.
An offset at or beyond end of file succeeds with zero bytes read. A null data
buffer is permitted only when `count == 0`. `fs_unlink` removes the named file
and clears its slot; subsequent lookup returns `OS_ERR_NOT_FOUND`.
