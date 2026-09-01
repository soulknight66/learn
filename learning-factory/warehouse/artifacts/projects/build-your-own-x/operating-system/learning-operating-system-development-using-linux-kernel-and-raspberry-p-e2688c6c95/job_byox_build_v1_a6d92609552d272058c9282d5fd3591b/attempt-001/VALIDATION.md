# Generator-side validation record

Date: 2026-08-31 (America/Chicago). Commands were run from the repository root. These observations are reproducible local evidence only; they do not grant independent validation labels. `MANIFEST.yaml` intentionally remains `GENERATED` + `PARTIAL` with `productionized: false`.

The execution wrapper prepended these unrelated identity-resolution warnings to each shell invocation:

```text
/usr/bin/id: cannot find name for user ID 532319
/usr/bin/id: cannot find name for group ID 500275
/usr/bin/id: cannot find name for user ID 532319
```

## Tool inventory

Command:

```sh
sh environment/check.sh
```

Exit status: `0`. Observed script output:

```text
Host requirements:
cc                           FOUND   cc (GCC) 8.5.0 20210514 (Red Hat 8.5.0-22)
make                         FOUND   GNU Make 4.2.1
Optional Raspberry Pi target tools:
aarch64-none-elf-gcc         MISSING
qemu-system-aarch64          MISSING
HOST_READY=yes
```

## Starter build and intentional baseline failure

Command:

```sh
make -C starter clean all
```

Exit status: `0`. The exact build actions were:

```text
rm -rf build
mkdir -p build
cc -Iinclude -std=c11 -O2 -Wall -Wextra -Wpedantic -Werror -c src/pebble.c -o build/pebble.o
ar rcs build/libpebble.a build/pebble.o
```

Command:

```sh
make -C starter public
```

Exit status: `2`, expected because the challenge scaffold is intentionally incomplete. Observed test output:

```text
line 50: first == 1
line 51: second == 2
line 78: parent > 0
line 113: pid > 0
4 public assertion(s) failed
PASS initialization
FAIL process round robin
FAIL memory and fork
FAIL filesystem round trip
make: *** [Makefile:16: public] Error 1
```

The compilation preceding that output used the same strict warning flags and completed successfully.

## Sealed reference build and tests

Command:

```sh
make -C sealed/reference clean all
```

Exit status: `0`. Exact build actions:

```text
rm -rf build
mkdir -p build
cc -Iinclude -std=c11 -O2 -Wall -Wextra -Wpedantic -Werror -c src/pebble.c -o build/pebble.o
ar rcs build/libpebble.a build/pebble.o
```

Command:

```sh
make -C sealed/reference_tests clean test
```

Exit status: `0`. Observed test result:

```text
PASS initialization and diagnostics
PASS process lifecycle and scheduler
PASS process capacity and pid overflow
PASS virtual memory boundaries
PASS copy-on-write isolation
PASS copy-on-write capacity rollback
PASS physical frame exhaustion
PASS filesystem semantics
PASS descriptor fork and truncate rollback
PASS truncate resets open cursors
PASS file capacity and process cleanup
PASS write capacity rollback
PASS file table exhaustion
PASS invariant corruption detection
all reference tests passed
```

Command:

```sh
make -C sealed/reference_tests public
```

Exit status: `0`. Observed test result:

```text
PASS initialization
PASS process round robin
PASS memory and fork
PASS filesystem round trip
all public tests passed
```

Command:

```sh
make -C sealed/reference_tests clean test CFLAGS='-std=c11 -O0 -g -Wall -Wextra -Wpedantic -Werror'
```

Exit status: `0`. It emitted the same 14 `PASS` lines and `all reference tests passed` shown above.

An earlier strict reference build failed with `error: 'new_frame' may be used uninitialized [-Werror=maybe-uninitialized]`. The local variable and impossible-branch check were made explicit; the final strict builds above then passed. The failed diagnostic was retained here rather than reported as a pass.

## Informative blocked checks

Command:

```sh
make -C sealed/reference_tests sanitize
```

Exit status: `2`. Compilation reached the link step, which reported exactly:

```text
/usr/bin/ld: cannot find /usr/lib64/libasan.so.5.0.0
/usr/bin/ld: cannot find /usr/lib64/libubsan.so.1.0.0
collect2: error: ld returned 1 exit status
make: *** [Makefile:34: build/reference_tests_sanitize] Error 1
```

This is an unavailable host runtime dependency, not a sanitizer pass. No `TESTED` or sanitizer-derived label is claimed.

Command:

```sh
make -C sealed/reference/pi3 clean all
```

Exit status: `2`. The first target compile reported:

```text
aarch64-none-elf-gcc -std=c11 -O2 -Wall -Wextra -Wpedantic -Werror -ffreestanding -fno-stack-protector -fno-pie -mcpu=cortex-a53 -c boot.S -o build/boot.o
make: aarch64-none-elf-gcc: Command not found
make: *** [Makefile:20: build/boot.o] Error 127
```

The adapter C translation unit received a host front-end-only check:

```sh
cc -std=c11 -Wall -Wextra -Wpedantic -Werror -ffreestanding -fsyntax-only sealed/reference/pi3/kernel.c
```

Exit status: `0`, with no compiler output. This does not assemble AArch64 code, link an image, emulate a board, or prove a hardware boot.

No network or upstream access was attempted. No fuzz run, benchmark, profiler run, Raspberry Pi boot, production review by an independent party, or transfer verification was performed.

## Cleanup

After validation, scratch build directories were removed with:

```sh
make -C starter clean
make -C sealed/reference clean
make -C sealed/reference_tests clean
make -C sealed/reference/pi3 clean
```

All four cleanup targets exited `0`.

## Structure, immutable data, and credential hygiene

Commands:

```sh
python3 sealed/validation/verify_pack.py
python3 sealed/validation/scan_credentials.py
```

Both exited `0`. The final observed output was:

```text
required_regular_files=PASS
forbidden_paths_absent=PASS
manifest_exact_object=PASS
provenance_exact_object=PASS
only_regular_files_and_directories=PASS
status_generated=PASS
labels_generated_partial_only=PASS
productionized_false=PASS
public_header_matches_reference=PASS
required_count=23
missing=[]
present_forbidden=[]
non_regular=[]
credential_scan_files=43
credential_pattern_hits=[]
```

The metadata verifier treats the tagged JSON in the allocated `JOB.md` as inert expected data and performs semantic equality, including rejection of extra fields. The credential scan excludes only the job input and factory marker/control directories; it scans all generated regular UTF-8 files for private-key headers, common provider token forms, bearer credentials, and credential assignments. A no-hit pattern scan is hygiene evidence, not a security certification.
