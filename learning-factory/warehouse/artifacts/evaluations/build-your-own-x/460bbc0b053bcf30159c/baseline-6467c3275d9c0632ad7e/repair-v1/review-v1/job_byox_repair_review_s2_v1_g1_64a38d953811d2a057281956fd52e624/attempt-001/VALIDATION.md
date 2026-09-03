# Independent validation evidence

Review date: 2026-09-03 (America/Chicago). Commands ran from the review workspace root. `CANDIDATE/`
was treated as immutable. Builds used `.review-scratch/candidate`, a writable copy, and the scratch
tree was removed after validation. Repeated harness warnings about unmapped numeric user/group IDs are
omitted below because they precede every shell command and do not come from the candidate.

## Tool versions

Configured tools were invoked by exact path:

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
$ /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
Python 3.11.5
$ env LD_LIBRARY_PATH=/arm/tools/gnu/glib/2.82.1/rhe8-x86_64/lib64 \
    /arm/tools/qemu/qemu/9.1.1/linux64/bin/qemu-system-i386 --version
QEMU emulator version 9.1.1
$ /usr/bin/make --version
GNU Make 4.2.1
```

Java, Arm/AArch64, Node, Go, flex, and bison were irrelevant to this C/i386 pack and were not
exercised. Git and ripgrep were unavailable on `PATH`; bounded `find`, `grep`, `cmp`, and SHA-256
commands were used instead.

## Immutability, structure, metadata, and provenance

```text
$ find CANDIDATE -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum
649c7be3cd658033f7dba5ab50dd8283ac8accbab1dca827dbc28e81b96a4017  -
```

The same aggregate was observed after all checks (see final integrity check below).

```text
$ /usr/bin/timeout 20s \
    /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
    CANDIDATE/environment/verify_pack.py
required paths: 23 present regular files
forbidden paths: 21 absent
metadata: manifest and provenance match authoritative objects
archive entries: 65 generated files; regular files/directories only
credential scan: 49 UTF-8 text files; no credential-shaped values
[exit 0]
```

An independent Python relationship check (not the candidate verifier) observed:

```text
project_match True
source_match True
commit_match True
snapshot_match True
canonical_provenance_sha256 3a63c214aa56565c201a800f6c96425588bd25768e91224a6ef7283667eadc4c
```

Independent type and bounded credential-shape scans found 65 regular files, 30 directories, no
symlink/special entry, and zero hit files among 49 non-build files. `cmp` confirmed that the starter
and reference public headers are identical. These checks establish internal consistency only; the
external source snapshot and authorship/no-copy claim were unavailable for authentication.

## Fresh builds in an isolated copy

Scratch preparation:

```text
$ test ! -e .review-scratch && mkdir .review-scratch && \
    cp -R CANDIDATE .review-scratch/candidate && \
    chmod -R u+w .review-scratch/candidate
[exit 0]
```

Strict hosted and freestanding builds:

```text
$ /usr/bin/timeout 30s /usr/bin/make \
    -C .review-scratch/candidate/starter clean all
[exit 0]
$ /usr/bin/timeout 30s /usr/bin/make \
    -C .review-scratch/candidate/sealed/reference clean all
[exit 0]
$ /usr/bin/timeout 30s /usr/bin/make \
    -C .review-scratch/candidate/sealed/reference_tests clean all
[exit 0]
```

The emitted commands used GCC 15.2.0, NASM 2.16.03, and GNU ld 2.43 at the pinned absolute paths,
with `-Wall -Wextra -Wpedantic -Werror`. Both kernel builds used the documented i386 freestanding
flags.

The public suite was freshly compiled against the reference:

```text
$ /usr/bin/timeout 30s /usr/bin/make \
    -C .review-scratch/candidate/public_tests clean all \
    BUILD=../sealed/reference_tests/build/public \
    IMPL=../sealed/reference/src/cairn.c \
    INCLUDE=../sealed/reference/include
[exit 0]
```

One earlier exploratory invocation ran that command concurrently with `reference_tests clean all`.
Both commands use `sealed/reference_tests/build`, so the clean removed the other's output directory
and the public link returned 2. The sequential command above exited 0. This was a reviewer-created
cross-command race, not a failure of the documented sequential workflow.

Hosted executions:

```text
$ /usr/bin/timeout 10s ./.review-scratch/candidate/starter/build/demo
CairnOS starter built: implementation TODOs remain.
[exit 0]
$ /usr/bin/timeout 10s ./.review-scratch/candidate/sealed/reference/build/demo
CairnOS reference demo: pid=1 file=scheduler + pages + files
[exit 0]
```

As documented, running the visible suite against the unimplemented starter compiled successfully and
then reported four failures at `cairn_spawn`; `make ... run` returned 2. That is the intended initial
learner state, not a reference failure.

## Behavioral tests

Builder-supplied drivers were independently rebuilt and invoked rather than accepted as prose:

```text
$ /usr/bin/timeout 20s \
    ./.review-scratch/candidate/sealed/reference_tests/build/test_reference
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
$ /usr/bin/timeout 20s \
    ./.review-scratch/candidate/sealed/reference_tests/build/test_adversarial
adversarial test: 25000 deterministic operations preserved invariants
[exit 0]
$ /usr/bin/timeout 20s \
    ./.review-scratch/candidate/sealed/reference_tests/build/public/test_public
  PASS process round robin
  PASS mapping translation
  PASS file descriptors
  PASS exit cleanup
public tests: 4 passed
[exit 0]
```

The deterministic mixed-operation result is not treated as fuzzing evidence.

## Reviewer-authored repair regression

The reviewer created `.review-scratch/reviewer_entry_boundary.c` outside `CANDIDATE/`. It checks the
maximum valid entry, byte-for-byte/output transactional rejection by `cairn_spawn` at
`CAIRN_USER_TOP`, and validator rejection at that boundary for ready, running, blocked, and exited
processes.

```text
$ /usr/bin/timeout 30s \
    /arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc \
    -std=c11 -O2 -Wall -Wextra -Wpedantic -Werror \
    -I.review-scratch/candidate/sealed/reference/include \
    .review-scratch/reviewer_entry_boundary.c \
    .review-scratch/candidate/sealed/reference/src/cairn.c \
    -o .review-scratch/reviewer_entry_boundary
[exit 0]
$ /usr/bin/timeout 10s ./.review-scratch/reviewer_entry_boundary
review boundary: PASS (spawn transaction plus four lifecycle states)
[exit 0]
```

The same test was compiled with `-fsanitize=address,undefined -fno-omit-frame-pointer` and run with
the pinned GCC runtime and `ASAN_OPTIONS=detect_leaks=0`; it produced the same PASS line, exited 0,
and emitted no sanitizer diagnostic.

## Sanitizers and static analysis

```text
$ /usr/bin/timeout 45s /usr/bin/make \
    -C .review-scratch/candidate/sealed/reference_tests sanitized
[focused suite: 10 passed]
[adversarial driver: 25000 deterministic operations preserved invariants]
[exit 0; no ASan/UBSan diagnostic]
$ cd .review-scratch
$ /usr/bin/timeout 30s \
    /arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc \
    -std=c11 -O0 -Wall -Wextra -Wpedantic -Werror -fanalyzer \
    -Icandidate/sealed/reference/include \
    -c candidate/sealed/reference/src/cairn.c -o reference_analyzer.o
[exit 0; no diagnostics]
```

LeakSanitizer remained disabled because the sandbox withholds its required process inspection. The
core performs no allocation.

## Artifact reproducibility and freestanding execution

An independent SHA-256 comparison covered starter/reference host programs, boot/core objects and
kernels, focused/adversarial/public test binaries, and the timing probe. Every result was `MATCH`:

```text
starter/build/{demo,boot.o,boot_kernel.o,cairn_freestanding.o,cairnos.elf}: 5 MATCH
sealed/reference/build/{demo,boot.o,boot_kernel.o,cairn_freestanding.o,cairnos.elf}: 5 MATCH
sealed/reference_tests/build/{test_reference,test_adversarial,public/test_public,benchmark}: 4 MATCH
```

The comparison was between `CANDIDATE/<path>` and the freshly built scratch copy using SHA-256 of file
bytes. Sanitized binaries contain debug-path metadata and were executed fresh rather than claimed as
byte-reproducible.

```text
$ /arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/nm \
    -u .review-scratch/candidate/sealed/reference/build/cairn_freestanding.o
[exit 0; no output]
$ /arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/readelf \
    -h .review-scratch/candidate/sealed/reference/build/cairnos.elf
Class:                             ELF32
Type:                              EXEC (Executable file)
Machine:                           Intel 80386
Entry point address:               0x101000
[exit 0]
$ env LD_LIBRARY_PATH=/arm/tools/gnu/glib/2.82.1/rhe8-x86_64/lib64 \
    /usr/bin/timeout 15s \
    /arm/tools/qemu/qemu/9.1.1/linux64/bin/qemu-system-i386 \
    -kernel .review-scratch/candidate/sealed/reference/build/cairnos.elf \
    -display none -monitor none -serial stdio -no-reboot \
    -device isa-debug-exit,iobase=0xf4,iosize=0x04
CAIRNOS: PASS
[exit 33; expected encoding of guest value 0x10]
```

This establishes a bounded emulator smoke result, not real-hardware correctness.

## Timing probe and claim review

```text
$ /usr/bin/timeout 30s /usr/bin/make \
    -C .review-scratch/candidate/sealed/reference_tests benchmark
translations=1000000 final_physical=12863 elapsed_clock_ticks=4002
[exit 0]
```

The local tick count differs from the builder's recorded 4133, as expected for an unsampled host-load
measurement. The candidate accurately declines to call this a benchmark or claim `BENCHMARKED`.

## Final integrity check and limitations

After deleting only the validated `.review-scratch` directory, the candidate aggregate was recomputed:

```text
$ find CANDIDATE -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum
649c7be3cd658033f7dba5ab50dd8283ac8accbab1dca827dbc28e81b96a4017  -
```

External source authentication, real hardware, factory learner-view filtering, security review,
transfer verification, and production deployment were unavailable. No such label is inferred. The
advisory PASS can only be published as `REVIEWED` by the orchestrator-controlled acceptance validator.
