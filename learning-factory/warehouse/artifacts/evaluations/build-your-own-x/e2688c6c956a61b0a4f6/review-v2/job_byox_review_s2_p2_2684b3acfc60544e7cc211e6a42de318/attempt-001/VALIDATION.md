# Independent validation evidence

Review date: 2026-09-03 (America/Chicago). `CANDIDATE/` was not modified. Builds
ran under explicit outer timeouts in `.review-scratch/CANDIDATE`, a writable
47-file copy. The copy initially retained the submitted read-only directory
modes, so it was made owner-writable before compilation; that setup-only
permission failure was not attributed to the candidate.

## Tool identities

All configured tools below were invoked by exact path.

```text
$ /arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc --version
gcc (GCC) 15.2.0
exit 0

$ /arm/tools/arm/arm-gnu-toolchain-aarch64-none-elf/15.2.rel1/linux64/bin/aarch64-none-elf-gcc --version
aarch64-none-elf-gcc (Arm GNU Toolchain 15.2.Rel1 (Build arm-15.86)) 15.2.1 20251203
exit 0

$ /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
Python 3.11.5
exit 0

$ /arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/ld --version
GNU ld (GNU Binutils) 2.43
exit 0

$ /usr/bin/make --version
GNU Make 4.2.1
exit 0
```

The submitted QEMU runtime observation reproduced:

```text
$ /usr/bin/timeout 10s /arm/tools/qemu/qemu/9.1.1/linux64/bin/qemu-system-aarch64 --version
...undefined symbol: g_date_time_format_iso8601
exit 127

$ env LD_LIBRARY_PATH=/arm/tools/gnu/glib/2.82.1/rhe8-x86_64/lib64 /usr/bin/timeout 10s /arm/tools/qemu/qemu/9.1.1/linux64/bin/qemu-system-aarch64 --version
QEMU emulator version 9.1.1
exit 0
```

## Candidate integrity, metadata, and archive boundary

```text
$ find CANDIDATE -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum
f1ac86abff490ab1d3fc20ed45bf5478d61ec536ab398417f3f989e01b79f3d5  -
exit 0

$ /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 CANDIDATE/environment/validate_structure.py
structure: PASS (23 required files, no forbidden paths)
archive types: PASS (regular files and directories only)
credential patterns: PASS
metadata status: PASS (GENERATED + PARTIAL)
exit 0

$ cmp -s CANDIDATE/starter/include/minios.h CANDIDATE/sealed/reference/include/minios.h
exit 0
```

A separate reviewer-authored Python check did not rely on the submitted
scanner. It enumerated all objects, rejected symlinks/special objects, repeated
the credential-signature scan, parsed both metadata objects, checked all linked
IDs and labels, classified answer-bearing paths, and constrained learner-visible
C sources. Observed result:

```text
independent archive check: PASS (47 files, 27 non-sealed, 18 answer-bearing files all sealed)
exit 0
```

The aggregate digest was recomputed after all checks and was identical.

## Submitted build claims, independently rerun

The normal workspace login shell exports the standard `/usr/bin` path used by
GNU Make and the host GCC driver's linker lookup.

```text
$ /usr/bin/timeout --foreground 60s /usr/bin/make -C .review-scratch/CANDIDATE/starter clean compile
[three GCC 15.2.0 C11 compilations with -Wall -Wextra -Werror -pedantic]
exit 0

$ /usr/bin/timeout --foreground 60s /usr/bin/make -C .review-scratch/CANDIDATE/starter test
[PASS] initializers
[FAIL] process round robin
[FAIL] process rejections
[FAIL] virtual memory
[FAIL] RAM filesystem
1/5 public checks passed
exit 2
```

The exit 2 is the documented baseline for TODO stubs, not a reference failure.

```text
$ /usr/bin/timeout --foreground 90s /usr/bin/make -C .review-scratch/CANDIDATE/sealed/reference clean all
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

The captured QEMU UART log was:

```text
MiniOS freestanding boot
processes: ok
virtual-memory: ok
ramfs: ok
MINIOS: PASS
```

An exact-path `aarch64-none-elf-nm -u` check on the resulting ELF printed no
undefined symbols and exited 0.

## Reviewer-authored semantic and sanitizer checks

The independent C harness was compiled directly with the three reference
sources and strict C11 warnings. It covered process error priority and state
transitions, round-robin behavior, VM alignment/ranges/permission subsets/full
capacity, maximum RAMFS names, sparse writes, overflow-sized offsets,
zero-length I/O, output clearing, and rejected-operation byte stability.

```text
$ /usr/bin/timeout --foreground 30s /arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc -std=c11 -O2 -Wall -Wextra -Werror -pedantic [reference sources] independent_contract.c -o independent_contract
exit 0

$ /usr/bin/timeout --foreground 10s ./independent_contract
independent semantic checks: process=PASS vm=PASS filesystem=PASS
exit 0
```

The same harness was rebuilt with
`-fsanitize=address,undefined -fno-omit-frame-pointer`. The GCC runtime had to
be selected explicitly. LeakSanitizer itself cannot operate under the
workspace's ptrace restrictions, so only leak detection was disabled:

```text
$ env LD_LIBRARY_PATH=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64 ASAN_OPTIONS=detect_leaks=0 /usr/bin/timeout --foreground 15s ./independent_contract_sanitized
independent semantic checks: process=PASS vm=PASS filesystem=PASS
exit 0
```

No ASan or UBSan diagnostic was emitted.

## Deterministic-initialization failure

A distinct reviewer harness filled one `ramfs_t` with `0xa5` and another with
`0x5a`, called the reference `fs_init` on each, and compared all bytes. It was
compiled with the same strict host flags:

```text
$ /usr/bin/timeout --foreground 30s /arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc -std=c11 -O2 -Wall -Wextra -Werror -pedantic -I[reference include] [reference ramfs.c] check_determinism.c -o check_determinism
exit 0

$ /usr/bin/timeout --foreground 10s ./check_determinism
sizeof(fs_file_t)=304 offsetof(size)=296 sizeof(ramfs_t)=2432
independent initializer representation check: FAIL at byte 289 (0xa5 != 0x5a)
exit 1
```

This is an observed violation of the published full deterministic-state
initializer rule, not a promotion-label claim.

## Hosted linker dependency probe

The absolute GCC driver does not pin its linker. A normal `-Wl,--version` link
reported the actual selection:

```text
/usr/bin/ld ... --version
GNU ld version 2.30-123.el8
exit 0
```

That binary/version is not recorded in the candidate toolchain metadata.
Controlled probes established the dependency:

```text
$ env -u PATH /usr/bin/timeout --foreground 30s /arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc [independent harness and reference sources]
collect2: fatal error: cannot find 'ld'
exit 1

$ env PATH=/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin /usr/bin/timeout --foreground 30s /arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc [same inputs]
exit 0
```

## Inconclusive or unavailable validation

- The upstream catalog snapshot/content was not present and network access was
  unavailable. Internal provenance links passed; external non-copying and
  license assertions remain unverified.
- The review workspace exposes sealed evaluator files to the reviewer. No
  generated learner view was supplied, so transfer isolation remains
  inconclusive despite correct path organization.
- No physical Raspberry Pi was available. No board, fuzzing, benchmark,
  production, or transfer claim was made or inferred.
- This report is advisory. Only an orchestrator-captured acceptance validator
  can publish `REVIEWED` or another promoted validation label.
