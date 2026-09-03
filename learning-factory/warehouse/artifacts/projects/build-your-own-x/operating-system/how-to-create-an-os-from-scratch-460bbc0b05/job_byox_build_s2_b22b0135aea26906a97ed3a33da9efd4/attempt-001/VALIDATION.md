# Validation evidence

Status remains **GENERATED + PARTIAL**. These are local construction observations from 2026-09-03
(America/Chicago), not independent validation and not promotion to any validation label.

## Pinned tools observed

Commands and first output lines:

```text
$ /arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc --version
gcc (GCC) 15.2.0
$ /arm/tools/nasm/nasm/2.16.03/rhe8-x86_64/bin/nasm --version
NASM version 2.16.03 compiled on Apr 11 2025
$ /arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/ld --version
GNU ld (GNU Binutils) 2.43
$ /arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/readelf --version
GNU readelf (GNU Binutils) 2.43
$ LD_LIBRARY_PATH=/arm/tools/gnu/glib/2.82.1/rhe8-x86_64/lib64 /arm/tools/qemu/qemu/9.1.1/linux64/bin/qemu-system-i386 --version
QEMU emulator version 9.1.1
$ /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
Python 3.11.5
```

## Builds and hosted execution

```text
$ make -C starter clean all
[exit 0] built build/demo and ELF32 build/cairnos.elf with strict warnings as errors
$ ./starter/build/demo
CairnOS starter built: implementation TODOs remain.

$ make -C sealed/reference clean all
[exit 0] built build/demo and ELF32 build/cairnos.elf with strict warnings as errors
$ ./sealed/reference/build/demo
CairnOS reference demo: pid=1 file=scheduler + pages + files

$ make -C public_tests clean run BUILD=../sealed/reference_tests/build/public IMPL=../sealed/reference/src/cairn.c INCLUDE=../sealed/reference/include
  PASS process round robin
  PASS mapping translation
  PASS file descriptors
  PASS exit cleanup
public tests: 4 passed

$ make -C sealed/reference_tests clean run
  PASS initialization and transactional errors
  PASS process capacity and reuse
  PASS scheduler no-runnable transaction
  PASS mapping boundaries and precedence
  PASS inode capacity and names
  PASS descriptor independence and capacity
  PASS file capacity atomicity
  PASS cross-subsystem exit cleanup
  PASS validator corruption rejection
reference tests: 9 passed
adversarial test: 25000 deterministic operations preserved invariants
```

The public suite was compiled against the sealed implementation only for this check. Its output binary
was directed into `sealed/reference_tests/build/public`; no solution-linked binary is retained under
`public_tests/`.

## Sanitizers

```text
$ make -C sealed/reference_tests sanitized
ASAN_OPTIONS=detect_leaks=0 LD_LIBRARY_PATH=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64 ./build/test_reference_san
reference tests: 9 passed
ASAN_OPTIONS=detect_leaks=0 LD_LIBRARY_PATH=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64 ./build/test_adversarial_san
adversarial test: 25000 deterministic operations preserved invariants
```

An informative first attempt without the pinned GCC runtime failed at loader startup with
`libasan.so.8: cannot open shared object file`. With that path supplied, LeakSanitizer then reported
that it cannot run under the sandbox's process-inspection policy. The recorded target therefore sets
`detect_leaks=0`; AddressSanitizer and UndefinedBehaviorSanitizer remain active and reported no
diagnostics in the observed runs. No allocation is used by the kernel core.

## Freestanding and emulator checks

```text
$ /arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/nm -u sealed/reference/build/cairn_freestanding.o
[exit 0, no output: no undefined symbols]

$ /arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/readelf -h sealed/reference/build/cairnos.elf
Class:                             ELF32
Type:                              EXEC (Executable file)
Machine:                           Intel 80386
Entry point address:               0x101000

$ LD_LIBRARY_PATH=/arm/tools/gnu/glib/2.82.1/rhe8-x86_64/lib64 timeout 15s /arm/tools/qemu/qemu/9.1.1/linux64/bin/qemu-system-i386 -kernel sealed/reference/build/cairnos.elf -display none -monitor none -serial stdio -no-reboot -device isa-debug-exit,iobase=0xf4,iosize=0x04
CAIRNOS: PASS
[host exit 33, the documented encoding of guest success value 0x10]
```

QEMU without the configured GLib path failed before launch with
`undefined symbol: g_tree_insert_node`; pinning the supplied library directory resolved it.

An earlier kernel build reached `cairn_init` but raised invalid opcode on an emitted `pxor` before SSE
was enabled, then triple-faulted. The freestanding flags now use `-march=i386 -mno-sse -mno-sse2
-mno-mmx`. Rebuild plus the successful QEMU run above verified the correction.

## Timing probe (not a validation label)

```text
$ make -C sealed/reference_tests benchmark
translations=1000000 final_physical=12863 elapsed_clock_ticks=4112
```

This is one observed host `clock()` result only. It is not portable, was not statistically sampled,
and does not justify `BENCHMARKED`.

## Structure, metadata, and credential scan

```text
$ /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 environment/verify_pack.py
required paths: 23 present regular files
forbidden paths: 21 absent
metadata: manifest and provenance match authoritative objects
archive entries: 65 generated files; regular files/directories only
credential scan: 49 UTF-8 text files; no credential-shaped values
```

The verifier excludes harness-owned workspace metadata from archive-entry enumeration and skips
compiled binaries for text-pattern scanning. It checks every generated entry type, both authoritative
JSON objects, every required/forbidden path, and common private-key/token/credential shapes in all
generated UTF-8 source and documentation.

## Why PARTIAL remains accurate

No independent validator has run. There is no real-hardware matrix, privilege separation, hardware
page table, interrupt-driven context switch, persistent filesystem, coverage claim, security audit,
transfer verification, or production deployment. LeakSanitizer is unavailable under sandbox policy.
The manifest therefore remains exactly `GENERATED` with labels `GENERATED` and `PARTIAL`.
