# Behavioral requirements

Do not change `starter/include/tinykernel.h`. Every operation is deterministic, uses fixed storage,
and returns `0` on success and `-1` on failure unless stated otherwise. Failed mutating operations
must leave all observable state unchanged.

## Stage 1: physical frames

- `tk_frames_init(a, n)` resets `a`. Values `1..TK_MAX_FRAMES` create exactly `n` free frames; any
  other value creates an empty allocator.
- `tk_frame_alloc(a)` returns and marks used the lowest-numbered free frame, or `-1` if none exists.
- `tk_frame_free(a, frame)` frees an allocated in-range frame. Reject out-of-range frames and double
  frees.
- `tk_frame_available(a)` returns the current free count. A null pointer returns zero.

## Stage 2: processes and scheduling

- `tk_scheduler_init(s)` empties the table. PIDs begin at 1.
- `tk_process_spawn(s)` occupies the lowest reusable slot in state `TK_READY` and returns a unique,
  increasing positive PID. Return `-1` when all slots are live.
- `tk_schedule(s)` changes a current `TK_RUNNING` process back to `TK_READY`, then scans cyclically
  after the most recently selected slot. It selects the first `TK_READY` process, marks it
  `TK_RUNNING`, increments its `quanta`, and returns its PID. Return `-1` if none is ready.
- `tk_process_block`, `tk_process_wake`, and `tk_process_exit` accept a live PID only in respectively
  `RUNNING`, `BLOCKED`, or any non-exited live state as appropriate: block accepts `READY` or
  `RUNNING`; wake accepts only `BLOCKED`; exit accepts `READY`, `RUNNING`, or `BLOCKED`.
- Blocking or exiting the running process clears `current_slot` but does not reset round-robin
  history. Exited slots may be reused, but old PIDs never become valid again.
- `tk_process_state` returns `TK_UNUSED` for an unknown PID. `tk_current_pid` returns `-1` when no
  process is running.

## Stage 3: virtual mappings

- Page size is `TK_PAGE_SIZE`; mapping and unmapping addresses must be page-aligned.
- `tk_vm_init(space, frames)` removes all mappings and records the allocator. A null allocator makes
  future map operations fail.
- `tk_vm_map(space, virtual_address, flags)` accepts only known flag bits, requires `TK_VM_READ`,
  rejects duplicate virtual pages, and needs both a free mapping slot and a free physical frame.
  It uses `tk_frame_alloc`; an operation that fails before allocation must not consume a frame.
- `tk_vm_translate(space, virtual_address, required_flags, physical_out)` accepts only known
  required bits. It succeeds only when the page is present and contains every required permission.
  The result is `frame * TK_PAGE_SIZE + offset`. A failure must not write `physical_out`.
- `tk_vm_unmap` frees the backing frame exactly once and removes the mapping. Reject unaligned or
  unmapped addresses.
- `tk_vm_mapping_count` returns the number of present mappings; null returns zero.

## Stage 4: bounded RAM filesystem

- `tk_fs_init(fs)` removes every file.
- A valid name has 1 through `TK_NAME_CAPACITY - 1` non-null bytes followed by `\0`.
- `tk_fs_create` creates an empty file in the lowest free slot. Reject invalid names, duplicates,
  and a full table.
- `tk_fs_write` replaces an existing file's complete contents. Length may be zero and must not
  exceed `TK_FILE_CAPACITY`; `data` may be null only for a zero-length write.
- `tk_fs_read` returns the complete file length as a nonnegative `int`. It fails if the output
  capacity is too small; `out` may be null only for an empty file. On failure it must not alter the
  output buffer.
- `tk_fs_size` returns a file's byte length or `-1`; `tk_fs_unlink` removes an existing file;
  `tk_fs_file_count` reports live files and returns zero for null.

## Freestanding constraints

Subsystem source files must compile as ISO C11 with `-Wall -Wextra -Werror -pedantic` and must not
call the host C library. The x86 image must be ELF32 for machine `EM_386`, contain the Multiboot v1
magic in its first 8192 bytes, and define a nonzero entry point. Emulator execution is not part of
the public scored contract.
