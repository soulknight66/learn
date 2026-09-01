# MicaOS Core Lab reference

This directory contains the sealed C11 reference implementation for the lab. It is an independently generated teaching model, not a copy of the linked OS tutorial. It models three kernel-shaped subsystems in ordinary memory; it is not a bootable operating system.

The implementation has no dynamic allocation and the three core source files call no hosted C library functions. `stddef.h`, `stdint.h`, and `stdbool.h` supply language-level types through the public header. Core objects are compiled with `-ffreestanding` and archived as `build/libmicaos.a`.

## Build and test

From the challenge root:

```sh
make -C sealed/reference
make -C sealed/reference test
make -C sealed/reference clean
```

`test` first compares the sealed header with `starter/include/micaos.h`, builds every source with C11 plus `-Wall -Wextra -Werror -pedantic`, and then runs the hosted sealed test executable. The compiler, archiver, flags, and preprocessor flags can be overridden with `CC`, `AR`, `CORE_CFLAGS`, `TEST_CFLAGS`, and `CPPFLAGS`.

The locally observed run on 2026-08-31 printed `reference tests: PASS`. That is useful build evidence, but it is not independent validation and does not change the repository's `GENERATED` / `PARTIAL` labels.

## Files

- `include/micaos.h` is intentionally identical to the learner-facing API header.
- `scheduler.c` implements a fixed-record, deterministic round-robin scheduler.
- `vm.c` implements allocation and byte access over eight simulated frames.
- `ramfs.c` implements eight bounded flat files with binary contents.
- `Makefile` builds the freestanding archive and hosted reference tests.

The objects are caller-owned because the public types are concrete. Call each module initializer before use. For VM, initialize both the allocator and each fresh address space. An address space that still has mappings must be unmapped before it is initialized again; its initializer has no allocator argument with which to release frames.

## Contract highlights

Rejected calls do not change module state or output parameters. Void initializers tolerate a null pointer by doing nothing. Other required null pointers return `MICA_ERR_ARG`.

Scheduler calls select nonzero sequential PIDs, skipping resident values when the finite namespace wraps, and use stable slot order. PIDs are unique among resident records rather than forever. A scheduling call is a scheduling decision: the prior running process becomes eligible, and the scan starts after the preceding selected slot. `block` accepts READY or RUNNING; `exit` accepts any non-EXITED live process; only EXITED records can be reaped.

VM mappings take the lowest free frame and always start with 64 zero bytes. Read-only pages reject writes. Mapping an already mapped virtual page returns `MICA_ERR_EXISTS`; invalid page or address numbers return `MICA_ERR_RANGE`.

RAMFS names are exact and case-sensitive. Valid names contain 1 through 15 non-slash bytes and are neither `.` nor `..`. Positive-length writes may extend a file and zero-fill a gap. Zero-length writes at offsets 0 through 128 succeed without extension. Reads at EOF return zero bytes, while reads beyond EOF return `MICA_ERR_RANGE`.
