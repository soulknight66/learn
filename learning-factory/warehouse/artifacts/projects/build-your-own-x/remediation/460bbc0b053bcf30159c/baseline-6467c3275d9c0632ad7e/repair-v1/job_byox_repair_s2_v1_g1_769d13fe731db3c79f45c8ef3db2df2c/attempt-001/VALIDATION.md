# Repair validation evidence

Status remains **GENERATED + PARTIAL**. These are bounded local construction observations from
2026-09-03 (America/Chicago), not independent validation and not promotion to any validation label.
All commands below ran from the pack root unless a different working directory is stated. Repeated
harness messages about an unmapped numeric user/group ID are unrelated to the commands and are
omitted from the excerpts.

## Repair scope

The archived independent review reported that `cairn_validate` accepted `entry == CAIRN_USER_TOP`
for a non-empty process. The repaired checker rejects every non-empty process whose entry is not
strictly below that boundary. A sealed focused regression starts at the valid maximum and then checks
the forbidden boundary in `READY`, `RUNNING`, `BLOCKED`, and `EXITED`; it also checks an all-bits-set
entry. The learner-visible contract now states this invariant explicitly.

## Pinned tools observed

The relevant configured tools were invoked by exact path:

```text
$ /arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc --version
gcc (GCC) 15.2.0

$ /arm/tools/nasm/nasm/2.16.03/rhe8-x86_64/bin/nasm --version
NASM version 2.16.03 compiled on Apr 11 2025

$ /arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/ld --version
GNU ld (GNU Binutils) 2.43
$ /arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/readelf --version
GNU readelf (GNU Binutils) 2.43
$ /arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/nm --version
GNU nm (GNU Binutils) 2.43

$ env LD_LIBRARY_PATH=/arm/tools/gnu/glib/2.82.1/rhe8-x86_64/lib64 \
    /arm/tools/qemu/qemu/9.1.1/linux64/bin/qemu-system-i386 --version
QEMU emulator version 9.1.1

$ /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
Python 3.11.5
$ /usr/bin/make --version
GNU Make 4.2.1
```

Invoking QEMU without the configured GLib path failed at loader startup with
`undefined symbol: g_tree_insert_node`; the pinned environment above succeeded. The unrelated Java,
Arm/AArch64, Node, Go, flex, and bison toolchains were not used.

## Strict builds and hosted execution

Both copied source trees were freshly rebuilt; the Makefiles invoke GCC, NASM, and ld through the
absolute paths shown above:

```text
$ /usr/bin/timeout 30s /usr/bin/make -C starter clean all
[exit 0; strict hosted demo and ELF32 kernel built]
$ /usr/bin/timeout 10s ./starter/build/demo
CairnOS starter built: implementation TODOs remain.
[exit 0]

$ /usr/bin/timeout 30s /usr/bin/make -C sealed/reference clean all
[exit 0; strict hosted demo and ELF32 kernel built]
$ /usr/bin/timeout 10s ./sealed/reference/build/demo
CairnOS reference demo: pid=1 file=scheduler + pages + files
[exit 0]
```

The repaired implementation and focused/adversarial drivers were compiled with
`-std=c11 -O2 -Wall -Wextra -Wpedantic -Werror`:

```text
$ /usr/bin/timeout 30s /usr/bin/make -C sealed/reference_tests clean all
[exit 0]
$ /usr/bin/timeout 20s ./sealed/reference_tests/build/test_reference
  PASS initialization and transactional errors
  PASS process capacity and reuse
  PASS scheduler no-runnable transaction
  PASS mapping boundaries and precedence
  PASS inode capacity and names
  PASS descriptor independence and capacity
  PASS file capacity atomicity
  PASS cross-subsystem exit cleanup
  PASS validator corruption rejection
  PASS validator process entry boundaries
reference tests: 10 passed
[exit 0]
$ /usr/bin/timeout 20s ./sealed/reference_tests/build/test_adversarial
adversarial test: 25000 deterministic operations preserved invariants
[exit 0]
```

The existing public suite was linked only into the sealed build tree against the repaired reference:

```text
$ /usr/bin/timeout 30s /usr/bin/make -C public_tests clean all \
    BUILD=../sealed/reference_tests/build/public \
    IMPL=../sealed/reference/src/cairn.c INCLUDE=../sealed/reference/include
[exit 0]
$ /usr/bin/timeout 20s ./sealed/reference_tests/build/public/test_public
  PASS process round robin
  PASS mapping translation
  PASS file descriptors
  PASS exit cleanup
public tests: 4 passed
[exit 0]
```

No reference-linked output was placed under `public_tests/` or another learner-visible directory.
The 25,000-operation run is a deterministic bounded test, not fuzzing.

## Sanitizers and static analysis

```text
$ /usr/bin/timeout 30s /usr/bin/make -C sealed/reference_tests \
    build/test_reference_san build/test_adversarial_san
[exit 0]
$ env ASAN_OPTIONS=detect_leaks=0 \
    LD_LIBRARY_PATH=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64 \
    /usr/bin/timeout 30s ./sealed/reference_tests/build/test_reference_san
[same 10 PASS lines as the unsanitized focused suite; exit 0; no sanitizer diagnostics]
$ env ASAN_OPTIONS=detect_leaks=0 \
    LD_LIBRARY_PATH=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64 \
    /usr/bin/timeout 30s ./sealed/reference_tests/build/test_adversarial_san
adversarial test: 25000 deterministic operations preserved invariants
[exit 0; no sanitizer diagnostics]
```

AddressSanitizer and UndefinedBehaviorSanitizer were active. Leak detection remains disabled because
the sandbox blocks LeakSanitizer's required process inspection; the core performs no allocation.

The first analyzer invocation from the pack root aborted before analysis with
`Cannot create temporary file in ./: Permission denied`, because that harness-owned root directory is
not writable for new scratch files. It was retried from the existing writable sealed build directory:

```text
$ cd sealed/reference_tests/build
$ /arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc \
    -std=c11 -O0 -Wall -Wextra -Wpedantic -Werror -fanalyzer \
    -I../../reference/include -c ../../reference/src/cairn.c \
    -o reference_analyzer.o
[exit 0; no diagnostics]
```

The analyzer object was then removed as reproducible scratch; it is not part of the delivered pack.

## Freestanding and emulator checks

The reference rebuild used `-m32 -ffreestanding -fno-builtin -fno-pie -fno-stack-protector
-march=i386 -mno-sse -mno-sse2 -mno-mmx`. Inspection of the rebuilt outputs observed:

```text
$ /arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/nm \
    -u sealed/reference/build/cairn_freestanding.o
[exit 0; no output]

$ /arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/readelf \
    -h sealed/reference/build/cairnos.elf
Class:                             ELF32
Type:                              EXEC (Executable file)
Machine:                           Intel 80386
Entry point address:               0x101000
[exit 0]
```

The freshly rebuilt reference kernel was then booted under the configured emulator:

```text
$ env LD_LIBRARY_PATH=/arm/tools/gnu/glib/2.82.1/rhe8-x86_64/lib64 \
    /usr/bin/timeout 15s \
    /arm/tools/qemu/qemu/9.1.1/linux64/bin/qemu-system-i386 \
    -kernel sealed/reference/build/cairnos.elf \
    -display none -monitor none -serial stdio -no-reboot \
    -device isa-debug-exit,iobase=0xf4,iosize=0x04
CAIRNOS: PASS
[host exit 33, the documented debug-exit encoding of guest value 0x10]
```

## Timing probe (not a benchmark claim)

```text
$ /usr/bin/timeout 30s /usr/bin/make -C sealed/reference_tests build/benchmark
[exit 0]
$ /usr/bin/timeout 20s ./sealed/reference_tests/build/benchmark
translations=1000000 final_physical=12863 elapsed_clock_ticks=4133
[exit 0]
```

This single `clock()` observation is neither statistically sampled nor portable and does not justify
the `BENCHMARKED` label.

## Structure, metadata, and credential scan

The final structural command and its observed output are recorded after all generated-file edits:

```text
$ /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 environment/verify_pack.py
required paths: 23 present regular files
forbidden paths: 21 absent
metadata: manifest and provenance match authoritative objects
archive entries: 65 generated files; regular files/directories only
credential scan: 49 UTF-8 text files; no credential-shaped values
```

The verifier checks the authoritative manifest and provenance objects, all required and forbidden
paths, regular-file/directory archive types, and common private-key/token/credential shapes in every
generated UTF-8 source and documentation file outside build directories. It does not authenticate an
external source snapshot or prove that no possible secret format exists.

## Why PARTIAL remains accurate

This repair has not received fresh independent validation. There is no real-hardware matrix,
privilege separation, hardware page table, interrupt-driven context switch, persistent filesystem,
coverage claim, security audit, transfer verification, or production deployment. The manifest
therefore remains exactly `GENERATED`, with only `GENERATED` and `PARTIAL` labels.
