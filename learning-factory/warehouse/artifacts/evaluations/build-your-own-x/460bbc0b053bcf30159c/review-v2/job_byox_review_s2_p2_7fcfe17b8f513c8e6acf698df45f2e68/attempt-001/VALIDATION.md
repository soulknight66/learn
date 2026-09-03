# Independent validation record

Date: 2026-09-03 (America/Chicago). Commands ran from the attempt root unless another working
directory is stated. `CANDIDATE/` was treated as read-only; all compiler outputs went to temporary
`REVIEW_TMP/`. Repeated shell startup warnings about an unmapped numeric user/group ID came from the
harness and did not affect command exit statuses.

## Tool availability and versions

Relevant configured tools were available and invoked by exact path:

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
$ /arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/objdump --version
GNU objdump (GNU Binutils) 2.43

$ env LD_LIBRARY_PATH=/arm/tools/gnu/glib/2.82.1/rhe8-x86_64/lib64 \
    /arm/tools/qemu/qemu/9.1.1/linux64/bin/qemu-system-i386 --version
QEMU emulator version 9.1.1

$ /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
Python 3.11.5

$ /usr/bin/make --version
GNU Make 4.2.1
```

No relevant configured build toolchain was unavailable. Java, Arm/AArch64 cross compilers, Node, Go,
flex, and bison were unrelated to this x86/C artifact and were not exercised. `rg` and `git` were not
on PATH; neither is required by the pack, and review discovery used `find` instead.

## Integrity, structure, and provenance

The aggregate hashes each sorted `sha256sum` record, including its candidate-relative path:

```text
$ sha256sum $(find CANDIDATE -type f | sort) | sha256sum
e6c88792ecdeebca65f8411f6a095d04828c98d253093a22bafc25b15271a801  -
```

The same result was observed before and after all tests. There were 65 regular candidate files, and
the starter and reference copies of `include/cairn.h` were byte-identical (`cmp` exit 0).

```text
$ /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
    CANDIDATE/environment/verify_pack.py
required paths: 23 present regular files
forbidden paths: 21 absent
metadata: manifest and provenance match authoritative objects
archive entries: 65 generated files; regular files/directories only
credential scan: 49 UTF-8 text files; no credential-shaped values
```

That verifier embeds its expected objects, so its result is internal consistency rather than external
authentication. Independent JSON parsing and hashing observed:

```text
provenance_file_sha256=97c34501a026a5ecd3bfa254ddb45f5e3d58296c6fdf4fe86e7db9f86c4d4b41
provenance_canonical_sha256=3a63c214aa56565c201a800f6c96425588bd25768e91224a6ef7283667eadc4c
snapshot_sha256=cd887247599d1200896aeb7cfb934318c6e53932e89be8bb7fbc18785fc1643a
```

The manifest's `provenance_sha256` equals the embedded source-snapshot digest, not the byte or
canonical digest of `PROVENANCE.json`. The provenance object and verifier make that relationship
internally consistent, but the external source object was unavailable. A second byte-pattern scan of
all 65 files, including compiled artifacts, found zero common private-key or token-shaped values.

## Hosted builds and execution

Each target below was compiled from submitted source into reviewer-owned scratch space. Representative
commands (the same absolute compiler and strict flags were used for every hosted target):

```sh
/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc \
  -std=c11 -O2 -Wall -Wextra -Wpedantic -Werror \
  -ICANDIDATE/sealed/reference/include \
  CANDIDATE/public_tests/test_public.c CANDIDATE/sealed/reference/src/cairn.c \
  -o REVIEW_TMP/test_public_reference

/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc \
  -std=c11 -O2 -Wall -Wextra -Wpedantic -Werror \
  -ICANDIDATE/sealed/reference/include \
  CANDIDATE/sealed/reference_tests/test_reference.c \
  CANDIDATE/sealed/reference/src/cairn.c -o REVIEW_TMP/test_reference

/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc \
  -std=c11 -O2 -Wall -Wextra -Wpedantic -Werror \
  -ICANDIDATE/sealed/reference/include \
  CANDIDATE/sealed/reference_tests/test_adversarial.c \
  CANDIDATE/sealed/reference/src/cairn.c -o REVIEW_TMP/test_adversarial
```

All hosted compilations, including both demos, the timing probe, and the starter-linked public suite,
exited 0 with no diagnostics. Bounded executions observed:

```text
$ /usr/bin/timeout 20s ./REVIEW_TMP/test_public_reference
  PASS process round robin
  PASS mapping translation
  PASS file descriptors
  PASS exit cleanup
public tests: 4 passed
[exit 0]

$ /usr/bin/timeout 20s ./REVIEW_TMP/test_reference
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
[exit 0]

$ /usr/bin/timeout 20s ./REVIEW_TMP/test_adversarial
adversarial test: 25000 deterministic operations preserved invariants
[exit 0]

$ /usr/bin/timeout 20s ./REVIEW_TMP/test_public_starter
four failures at the first cairn_spawn assertion
public tests: 4 failed
[exit 1, expected negative control for the documented skeleton]

$ /usr/bin/timeout 20s ./REVIEW_TMP/benchmark
translations=1000000 final_physical=12863 elapsed_clock_ticks=4100
[exit 0]
```

The timing differs slightly from the builder's recorded 4112 ticks, as its documentation correctly
warns. One clock sample is not a benchmark result and no `BENCHMARKED` label is supported.

GCC's analyzer also accepted the reference core without diagnostics:

```sh
/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc \
  -std=c11 -O0 -Wall -Wextra -Wpedantic -Werror -fanalyzer \
  -ICANDIDATE/sealed/reference/include \
  -c CANDIDATE/sealed/reference/src/cairn.c -o REVIEW_TMP/reference_analyzer.o
```

Observed exit: 0.

## Sanitizers and arbitrary-state safety

Sanitized binaries were rebuilt with this exact compiler prefix:

```sh
/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc \
  -std=c11 -O1 -g -Wall -Wextra -Wpedantic -Werror \
  -fsanitize=address,undefined -fno-omit-frame-pointer \
  -ICANDIDATE/sealed/reference/include TEST_SOURCE \
  CANDIDATE/sealed/reference/src/cairn.c -o OUTPUT
```

For both submitted reference drivers, this bounded command exited 0 with their ordinary pass output
and no sanitizer diagnostics:

```sh
env ASAN_OPTIONS=detect_leaks=0 \
  LD_LIBRARY_PATH=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64 \
  /usr/bin/timeout 30s OUTPUT
```

A reviewer-authored deterministic driver filled the entire public kernel object with new pseudorandom
bytes before each call. Under the same ASan+UBSan command it reported:

```text
arbitrary-byte validator calls=100000 checksum=0
[exit 0; no sanitizer diagnostics]
```

This is bounded robustness evidence, not exhaustive fuzzing. Enabling leak detection independently
confirmed the documented sandbox limitation:

```text
$ env ASAN_OPTIONS=detect_leaks=1 \
    LD_LIBRARY_PATH=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64 \
    /usr/bin/timeout 30s ./REVIEW_TMP/test_reference_san
LeakSanitizer has encountered a fatal error.
HINT: LeakSanitizer does not work under ptrace (strace, gdb, etc)
[exit 1]
```

## Reviewer-authored contract boundary check

The following essential mutation was compiled with the strict hosted command above:

```c
cairn_init(&kernel);
cairn_spawn(&kernel, 0U, &pid);
baseline = cairn_validate(&kernel);
kernel.processes[0].entry = CAIRN_USER_TOP;
invalid_entry = cairn_validate(&kernel);
kernel.processes[0].entry = 0U;
kernel.processes[0].mappings[0].present = 2;
invalid_mapping = cairn_validate(&kernel);
```

Observed result:

```text
baseline=0 invalid_entry=0 invalid_mapping_flag=-9
[exit 1 because the reviewer expected both corruptions to return CAIRN_ERR_CORRUPT]
```

This reproduces the prioritized correctness finding in `REVIEW.md`.

## Freestanding build, reproducibility, and emulator

Reference objects were rebuilt with exact pinned tools and flags:

```sh
/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc \
  -std=c11 -m32 -O2 -Wall -Wextra -Wpedantic -Werror \
  -ffreestanding -fno-builtin -fno-pie -fno-stack-protector \
  -march=i386 -mno-sse -mno-sse2 -mno-mmx \
  -ICANDIDATE/sealed/reference/include \
  -c CANDIDATE/sealed/reference/src/cairn.c \
  -o REVIEW_TMP/reference_cairn_freestanding.o

/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc \
  -std=c11 -m32 -O2 -Wall -Wextra -Wpedantic -Werror \
  -ffreestanding -fno-builtin -fno-pie -fno-stack-protector \
  -march=i386 -mno-sse -mno-sse2 -mno-mmx \
  -ICANDIDATE/sealed/reference/include \
  -c CANDIDATE/sealed/reference/boot/kernel.c \
  -o REVIEW_TMP/reference_boot_kernel.o
```

To preserve NASM's source-file symbol and exactly reproduce the Makefile invocation, this ran from
`CANDIDATE/sealed/reference`:

```sh
/arm/tools/nasm/nasm/2.16.03/rhe8-x86_64/bin/nasm \
  -f elf32 boot/boot.asm -o ../../../REVIEW_TMP/reference_boot_makepath.o
/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/ld \
  -m elf_i386 -T boot/linker.ld \
  -o ../../../REVIEW_TMP/reference_cairnos_makepath.elf \
  ../../../REVIEW_TMP/reference_boot_makepath.o \
  ../../../REVIEW_TMP/reference_boot_kernel.o \
  ../../../REVIEW_TMP/reference_cairn_freestanding.o
```

All commands exited 0 without diagnostics. Pairwise submitted/rebuilt SHA-256 values were identical:

```text
reference demo                 2d0f6ae4b5139cfc842963882369412906a8d57e434362534548d1ad530017d8
reference boot.o               1aaec5b07e72a5f16fa50321cd00c7d97c02f2d36ffa960cf412679315876393
reference boot_kernel.o        4b26b7d3d694c24e3274968ec1d19378c14bd3015da79c41ccb7557d385ad524
reference cairn_freestanding.o c0126bb94aa7e04e7ceea6a5bb6849eb69c4e33cf9a7d329281ee725d182b6b1
reference cairnos.elf          5bbbc5660c02e6f39eaf83fc7031f248f3d1f7c29f0fce18f51ab5293f6dee1e
starter demo                   497c26f1ba72f2815d8f3b91789192d3690bfe4de09cd77d1d2ad67ba8ed1f03
starter boot.o                 b5b57ed4fdab667e6c90c85ff6eac60fe2355305925d99e7a4c05f37f66e417f
starter boot_kernel.o          469041809fd40d243440964774d545a747a269a7a1f0bd2c45ed8e1a53ecce7b
starter cairn_freestanding.o   3afb2ed6f23f623e739a863c8c538d5071ce07179a26234bddd4059fcaa006d1
starter cairnos.elf            6869765d0e9f41d41e3386bb32fa76cf9791db36e4454a22bdd3bfdb303a956f
```

Independent inspection observed no undefined symbol in the rebuilt core object, no SSE/MMX matches
in its disassembly, and this ELF identity:

```text
Class:                             ELF32
Type:                              EXEC (Executable file)
Machine:                           Intel 80386
Entry point address:               0x101000
```

Bounded emulator commands and results:

```text
$ env LD_LIBRARY_PATH=/arm/tools/gnu/glib/2.82.1/rhe8-x86_64/lib64 \
    /usr/bin/timeout 15s \
    /arm/tools/qemu/qemu/9.1.1/linux64/bin/qemu-system-i386 \
    -kernel REVIEW_TMP/reference_cairnos_makepath.elf \
    -display none -monitor none -serial stdio -no-reboot \
    -device isa-debug-exit,iobase=0xf4,iosize=0x04
CAIRNOS: PASS
[exit 33, documented guest-success encoding]

$ env LD_LIBRARY_PATH=/arm/tools/gnu/glib/2.82.1/rhe8-x86_64/lib64 \
    /usr/bin/timeout 15s \
    /arm/tools/qemu/qemu/9.1.1/linux64/bin/qemu-system-i386 \
    -kernel REVIEW_TMP/starter_cairnos.elf \
    -display none -monitor none -serial stdio -no-reboot \
    -device isa-debug-exit,iobase=0xf4,iosize=0x04
CAIRNOS STARTER: CORE INCOMPLETE
[exit 35, expected negative control]
```

The exact `-nographic -monitor none -serial stdio` command printed in
`CANDIDATE/environment/README.md` was also run against the submitted reference ELF; it printed
`CAIRNOS: PASS` and exited 33.

## Interpretation limits

These observations independently support reproducible compilation, the finite test results, and the
emulator smoke claim. They do not justify `FUZZED`, `BENCHMARKED`, `TRANSFER_VERIFIED`,
`PRODUCTIONIZED`, or publication of `REVIEWED`. No real-hardware, concurrency, persistent-media,
coverage, security, deployment, or transfer matrix was available. The candidate manifest was not
edited. Reviewer-owned `REVIEW_TMP/` build products and test sources were removed after the evidence
above was recorded; only the requested review artifacts remain at workspace root.
