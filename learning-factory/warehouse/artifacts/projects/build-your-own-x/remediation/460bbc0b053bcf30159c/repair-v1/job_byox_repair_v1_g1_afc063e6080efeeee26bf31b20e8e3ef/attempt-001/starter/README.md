# MicaOS Core Lab starter

This directory contains the incomplete C11 implementation for three small OS
subsystems: a process scheduler, a virtual-memory model, and an in-memory
filesystem. The public interface is in `include/micaos.h`; complete the marked
`TODO` sites in `src/` without changing the interface.

The core is freestanding-compatible. Do not call hosted-library functions from
the three source modules. Loops and direct byte copies are sufficient. Build
with:

```sh
make -C starter build
```

Run the hosted public checks with:

```sh
make -C starter test
```

The unmodified starter intentionally fails the functional checks.

## Contract summary

- Scheduler PIDs are nonzero and advance sequentially, wrapping past zero and
  skipping identities that are still resident. Spawned processes are
  `READY`. Each scheduling decision advances deterministic round-robin order,
  preempting a current `RUNNING` process when needed. No more than one process
  may be `RUNNING`. A `READY` or `RUNNING` process can be blocked, only a
  blocked process can be woken, and exited records remain until reaped.
- Each address space has 16 virtual pages. Mapping consumes the lowest-numbered
  free physical frame and clears all 64 bytes. Unmapping releases it. Reads and
  writes translate virtual byte addresses through the page table; writes to a
  read-only mapping return `MICA_ERR_PERM`.
- RAMFS names contain 1 through 15 characters, contain no slash, and cannot be
  `.` or `..`. Create rejects duplicates. Writes are random-access and atomic:
  a write that would exceed 128 bytes returns `MICA_ERR_RANGE` without changing
  the file. A positive-length sparse write zero-fills its gap and sets the size
  to the greater of the old size and the end of the write. A zero-length write
  succeeds without extending the file. The source may overlap a RAMFS file data
  array and behaves as a pre-write snapshot. Read copies the smaller of the supplied
  capacity and the bytes remaining from its offset. An offset equal to the file
  size reads zero bytes; a larger offset returns `MICA_ERR_RANGE`.

Functions reject null required pointers with `MICA_ERR_ARG`. Unless a function
documents an optional pointer, outputs and subsystem state remain unchanged on
error. Initializer functions accept null as a no-op. PIDs are unique among
resident records; callers must discard a PID after reaping it because the
finite namespace may eventually wrap and reuse its numeric value.

The fixed limits and all status values are declared in the public header. Do
not add dynamic allocation or global subsystem state.
