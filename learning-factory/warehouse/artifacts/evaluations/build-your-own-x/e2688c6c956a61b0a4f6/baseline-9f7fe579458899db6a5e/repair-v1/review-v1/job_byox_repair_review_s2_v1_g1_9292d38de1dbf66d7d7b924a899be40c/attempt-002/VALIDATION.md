# Independent validation evidence

Review date: 2026-09-03 (America/Chicago). `CANDIDATE/` was kept immutable. Builds and executions used a writable `.review-scratch-002` copy, which was deleted after testing.

The shell emitted harmless `id: cannot find name for user/group ID` messages because the sandbox UID/GID has no name-service entry. They did not change any recorded exit status.

## Tool identities

Each useful configured binary was invoked by exact path.

```text
$ /arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc --version
gcc (GCC) 15.2.0
exit 0

$ /arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/as --version
GNU assembler (GNU Binutils) 2.43
exit 0

$ /arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/ld --version
GNU ld (GNU Binutils) 2.43
exit 0

$ /arm/tools/arm/arm-gnu-toolchain-aarch64-none-elf/15.2.rel1/linux64/bin/aarch64-none-elf-gcc --version
aarch64-none-elf-gcc (Arm GNU Toolchain 15.2.Rel1 (Build arm-15.86)) 15.2.1 20251203
exit 0

$ /arm/tools/arm/arm-gnu-toolchain-aarch64-none-elf/15.2.rel1/linux64/bin/aarch64-none-elf-nm --version
GNU nm (Arm GNU Toolchain 15.2.Rel1 (Build arm-15.86)) 2.45.1.20251203
exit 0

$ /usr/bin/env LD_LIBRARY_PATH=/arm/tools/gnu/glib/2.82.1/rhe8-x86_64/lib64 /arm/tools/qemu/qemu/9.1.1/linux64/bin/qemu-system-aarch64 --version
QEMU emulator version 9.1.1
exit 0

$ /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
Python 3.11.5
exit 0

$ /usr/bin/make --version
GNU Make 4.2.1
exit 0
```

Java, Node.js, Go, ARM32, NASM, Flex, and Bison were irrelevant to this C/AArch64 candidate and were not exercised. All toolchains needed by the submitted build were available.

GCC program resolution was independently checked:

```text
$ /arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc -B/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/ -print-prog-name=as
/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/as
exit 0

$ /arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc -B/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/ -print-prog-name=ld
/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/ld
exit 0
```

## Immutable input and scratch setup

The initial and final candidate digest used this command:

```text
$ find CANDIDATE -type f -exec /usr/bin/sha256sum {} + | LC_ALL=C sort -k2 | /usr/bin/sha256sum
6945becdad7e283412fe7721ea0bde83980eb04f8ac16a94447ca6f3b587eeef  -
exit 0
```

No `CANDIDATE/**/build` directory existed before or after review. A copied tree compared equal before it was made writable:

```text
$ mkdir .review-scratch-002
$ cp -a CANDIDATE/. .review-scratch-002/
$ /usr/bin/diff -qr CANDIDATE .review-scratch-002
[no differences]
exit 0
```

The first scratch compile exited 2 at `mkdir build: Permission denied` because `cp -a` preserved the submission's read-only directory modes. This was an isolation setup result, not a candidate compile result. Only the copied tree was changed with `chmod -R u+w .review-scratch-002`. One subsequent invocation was mistakenly issued from the workspace root and reported `make: *** starter: No such file or directory` (exit 2); it did not inspect or build the candidate. All results below use the stated scratch working directory.

`rg` was unavailable (`bash: rg: command not found`), so file discovery used `find`.

## Structure and metadata

From `.review-scratch-002`:

```text
$ /usr/bin/timeout --foreground --kill-after=5s 30s /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 environment/validate_structure.py
structure: PASS (23 required files, no forbidden paths)
archive types: PASS (regular files and directories only)
credential patterns: PASS
metadata status: PASS (GENERATED + PARTIAL)
exit 0
```

An independent strict-JSON/cross-link check found `project_id`, `source_id`, `source_commit`, snapshot digest, and conservative labels mutually consistent. `cmp -s` confirmed that starter and reference headers are byte-identical. An extended scan for private-key headers, AWS access IDs, GitHub tokens, and common OpenAI key forms found zero matching files; a filesystem walk found no symlink or special object. Pattern scans cannot establish that no conceivable secret exists.

## Learner scaffold

From `.review-scratch-002`:

```text
$ /usr/bin/timeout --foreground --kill-after=5s 60s /usr/bin/make -C starter clean compile
[three GCC 15.2.0 C11 compilations with pinned Binutils and -Wall -Wextra -Werror -pedantic]
exit 0

$ /usr/bin/timeout --foreground --kill-after=5s 60s /usr/bin/make -C starter test
[PASS] initializers
[FAIL] process round robin
[FAIL] process rejections
[FAIL] virtual memory
[FAIL] RAM filesystem
1/5 public checks passed
make: *** [Makefile:33: test] Error 1
exit 2
```

This exactly matches the documented incomplete-starter baseline. The failing groups reach explicit TODO stubs and are not treated as a reference failure.

## Submitted reference checks

```text
$ /usr/bin/timeout --foreground --kill-after=5s 120s /usr/bin/make -C sealed/reference clean all
[PASS] process initialization and errors
[PASS] process lifecycle
[PASS] process capacity and PID exhaustion
[PASS] VM boundaries and permissions
[PASS] VM capacity and aliasing
[PASS] filesystem names and capacity
[PASS] filesystem I/O and atomicity
reference contract tests: 7/7 passed
[PASS] 4000 deterministic process operations
[PASS] 4000 deterministic VM operations
[PASS] 4000 deterministic filesystem operations
MINIOS: PASS
exit 0
```

The fresh captured UART log was:

```text
MiniOS freestanding boot
processes: ok
virtual-memory: ok
ramfs: ok
MINIOS: PASS
```

ELF inspection reported `ELF64`, little-endian, `EXEC`, `AArch64`, and entry point `0x40080000`. The following produced no symbols and exited 0:

```text
$ /arm/tools/arm/arm-gnu-toolchain-aarch64-none-elf/15.2.rel1/linux64/bin/aarch64-none-elf-nm -u sealed/reference/build/aarch64/minios.elf
[no output]
exit 0
```

These suites are builder-authored and are corroborating evidence, not independent proof.

## Reviewer-authored checks

A temporary C harness was written outside `CANDIDATE`; its SHA-256 was `675162c98b9f34509debe3ef276b85dc1d6968e4005dd91b3eacd1c39f1e3589`. It independently checked:

- deterministic complete-object initialization from two different prefill bytes;
- null outputs and byte-identical state on rejection;
- process slot 7, full wraparound, all-unrunnable scheduling, reap clearing, zombie-parent precedence, absent-parent precedence, and exhausted PID state;
- empty/unknown VM masks, invalid/duplicate/full precedence, combined permissions, last page offset, and complete unmap clearing;
- maximum and excessive names, allowed punctuation, sparse/overlapping file writes, nonshrinking size, `SIZE_MAX` offsets, zero-length capacity boundaries, and complete unlink clearing.

It was compiled and run as follows:

```text
$ /usr/bin/timeout --foreground --kill-after=5s 45s /arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc -B/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/ -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic -fsanitize=address,undefined -fno-omit-frame-pointer -Isealed/reference/include sealed/reference/src/process.c sealed/reference/src/vm.c sealed/reference/src/ramfs.c reviewer_tests.c -o reviewer_tests
exit 0

$ /usr/bin/env LD_LIBRARY_PATH=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64 ASAN_OPTIONS=detect_leaks=0 /usr/bin/timeout --foreground --kill-after=5s 30s ./reviewer_tests
[PASS] reviewer process boundaries
[PASS] reviewer VM boundaries
[PASS] reviewer filesystem boundaries
exit 0
```

No ASan or UBSan diagnostic was emitted. Leak detection was disabled for the host constraint documented by the candidate. A separate ASan/UBSan build of `test_reference.c` also passed 7/7 with no sanitizer diagnostic.

Each reference source was separately compiled with GCC 15.2.0 `-fanalyzer -Wall -Wextra -Werror -pedantic`; all three commands exited 0 without analyzer output.

## PATH independence and deterministic rebuild

The hosted suite compiled with no `PATH`:

```text
$ /usr/bin/env -u PATH /usr/bin/timeout --foreground --kill-after=5s 45s /arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc -B/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/ -std=c11 -O2 -Wall -Wextra -Werror -pedantic -Isealed/reference/include sealed/reference/src/process.c sealed/reference/src/vm.c sealed/reference/src/ramfs.c sealed/reference_tests/test_reference.c -o reference_no_path
exit 0

$ /usr/bin/timeout --foreground --kill-after=5s 30s ./reference_no_path
[all seven groups PASS]
reference contract tests: 7/7 passed
exit 0
```

The two hosted test executables and AArch64 ELF were hashed, rebuilt via another bounded `make clean all`, and hashed again:

```text
first=47dac797483349bdce20dfb995c78e3f7a405d6cc298fe9efe99fcd21680de73
second=47dac797483349bdce20dfb995c78e3f7a405d6cc298fe9efe99fcd21680de73
comparison exit 0
```

This establishes repeatability for those outputs on this configured host, not universal reproducibility across unspecified toolchains.

## Limitations and cleanup

No physical Raspberry Pi, upstream snapshot, network, independent fuzzer, benchmark environment, production deployment, or completed learner cohort was available. An actual student-view exporter was also unavailable; review verified path-based sealing by inspection but cannot issue `TRANSFER_VERIFIED`.

The `PRIOR_BUILD` paths named in the builder's repair history are absent from the submitted candidate, so that historical preservation comparison was inconclusive here. The generated material also has no standard redistribution license grant beyond its stated personal educational-use boundary.

All executions were externally timeout-bounded. The submitted `qemu-test` recipe itself lacks an internal timeout, which is retained as a P3 hardening finding.

The validated scratch target was removed with `find .review-scratch-002 -xdev -depth -delete` (exit 0). It contained only a reproducible candidate copy, review harness, and build products; none are recoverable from that scratch path, but all candidate inputs remain intact. The final candidate digest equals the initial digest shown above, and no build directory was added to `CANDIDATE/`.
