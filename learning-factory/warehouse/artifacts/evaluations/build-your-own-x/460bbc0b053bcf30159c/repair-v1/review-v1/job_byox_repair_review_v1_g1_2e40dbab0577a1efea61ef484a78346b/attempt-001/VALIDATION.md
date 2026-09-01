# Independent validation record

Date: 2026-08-31 (America/Chicago)

All builds and executions used a writable review scratch copy. `CANDIDATE/` was inspected read-only and was not repaired or otherwise modified.

## Candidate integrity and isolation

Before inspection and again after all checks:

```sh
find CANDIDATE -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum
```

Both runs exited `0` and printed:

```text
a763045c67b1b4c7c0d90d94ff644a30f6459c37dbca7da38c9d4819bcefb95c  -
```

The candidate contained 42 regular files, no symlink or special entry, and no `build/` directory after review. Its directories were read-only (`CANDIDATE` mode `2555`; `CANDIDATE/starter` mode `0555`). The test copy was prepared as follows:

```sh
mkdir review-scratch-001
cp -a CANDIDATE review-scratch-001/candidate
chmod -R u+w review-scratch-001/candidate
```

An initial build attempt before the `chmod` failed to create `build/` because `cp -a` preserved those read-only modes. That was a scratch-permission failure, not a candidate compilation result. Every result below is from the writable copy.

## Available toolchain

```sh
python3 --version
cc --version | sed -n '1p'
make --version | sed -n '1p'
ar --version | sed -n '1p'
for tool in ar ld nm objcopy clang valgrind cppcheck clang-tidy scan-build \
  splint qemu-system-i386 qemu-system-x86_64 nasm timeout; do
    command -v "$tool" 2>/dev/null || printf '%s UNAVAILABLE\n' "$tool"
done
```

Observed:

```text
Python 3.6.8
cc (GCC) 8.5.0 20210514 (Red Hat 8.5.0-22)
GNU Make 4.2.1
GNU ar version 2.30-123.el8
ar, ld, nm, objcopy, and timeout available under /usr/bin
clang, valgrind, cppcheck, clang-tidy, scan-build, splint,
qemu-system-i386, qemu-system-x86_64, and nasm unavailable
```

Each login shell also printed three diagnostics stating that the numeric user/group IDs have no local names. These preceded command output and did not alter exit codes.

## Starter baseline

From `review-scratch-001/candidate`:

```sh
timeout 30s make -C starter clean build
timeout 30s make -C starter test
```

The build exited `0`. All three sources compiled with:

```text
-std=c11 -Wall -Wextra -Werror -pedantic -ffreestanding
```

The test target exited `2`, as documented for the deliberately incomplete starter:

```text
[PASS] initializers and constants
[PASS] scheduler validation
[PASS] VM validation
[PASS] RAMFS validation
[FAIL] scheduler lifecycle
[FAIL] VM lifecycle
[FAIL] RAMFS lifecycle

4 passed, 3 failed
```

Failures occurred at the first functional TODO in scheduler spawn, VM map, and RAMFS create. This is baseline evidence, not a `TESTED` promotion claim.

## Reference and public suites

```sh
timeout 30s make -C sealed/reference clean test
```

Exit code `0`:

```text
reference tests: PASS
```

The target byte-compared the starter/reference headers, built the three core objects with strict C11 freestanding flags, linked the 796-line hosted reference suite, and ran it.

The public suite was independently linked to that archive:

```sh
cc -Isealed/reference/include -std=c11 -Wall -Wextra -Werror -pedantic \
  public_tests/test_public.c sealed/reference/build/libmicaos.a \
  -o sealed/reference/build/test_public_independent
timeout 30s sealed/reference/build/test_public_independent
nm -u sealed/reference/build/libmicaos.a
```

All commands exited `0`. The executable printed:

```text
[PASS] initializers and constants
[PASS] scheduler validation
[PASS] VM validation
[PASS] RAMFS validation
[PASS] scheduler lifecycle
[PASS] VM lifecycle
[PASS] RAMFS lifecycle

7 passed, 0 failed
```

`nm -u` printed only the `scheduler.o`, `vm.o`, and `ramfs.o` headings; none had an undefined symbol.

The two public headers were also hashed directly:

```sh
sha256sum CANDIDATE/starter/include/micaos.h \
  CANDIDATE/sealed/reference/include/micaos.h
```

Both hashes were:

```text
765796d7628c14a857b5c23ff2218cfac7a707ea7e0e0eca1fd1e09bec829fcf
```

## Optimized and additional-warning builds

```sh
timeout 30s make -C sealed/reference clean test \
  CORE_CFLAGS='-O2 -std=c11 -Wall -Wextra -Werror -pedantic -ffreestanding' \
  TEST_CFLAGS='-O2 -std=c11 -Wall -Wextra -Werror -pedantic'
```

Exit code `0`; observed `reference tests: PASS`.

Each reference source was also compiled with the normal strict flags plus:

```text
-O2 -Wconversion -Wshadow -Wstrict-prototypes -Wmissing-prototypes
-Wcast-qual -Wwrite-strings
```

All warnings remained promoted to errors. The three compilations exited `0` with no diagnostic.

## Independent edge-case probe

A reviewer-authored C probe (SHA-256 `4e1f350a3c540ef650e7f9e43b967c59c7b56ef051e864bcc8add99d2d671c1a`) was placed only in review scratch. It checked:

- PID allocation at `UINT32_MAX`, wrap to PID 1, exit/reap, slot reuse, cursor persistence, and unchanged state/output when no process is runnable;
- frame exhaustion across two spaces, unchanged failed map state, lowest-frame reuse, all 64 reused bytes being zero, and a read-only write preserving the VM;
- an unterminated 16-byte name, a valid 15-byte name, a complete 128-byte file, aliased right-shift writes with snapshot semantics, oversized-write atomicity, zero-length boundary writes, and clearing on unlink.

It was compiled directly with the three reference sources:

```sh
cc -Icandidate/sealed/reference/include \
  -std=c11 -Wall -Wextra -Werror -pedantic \
  independent_probe.c \
  candidate/sealed/reference/scheduler.c \
  candidate/sealed/reference/vm.c \
  candidate/sealed/reference/ramfs.c \
  -o independent_probe
timeout 30s ./independent_probe
```

Compile and run both exited `0`:

```text
independent probe: PASS
```

This probe supplements rather than promotes the builder's evidence.

## Sanitizer attempt

```sh
ASAN_OPTIONS=detect_leaks=0:halt_on_error=1 \
UBSAN_OPTIONS=halt_on_error=1 \
timeout 30s make -C sealed/reference clean test \
  CORE_CFLAGS='-std=c11 -Wall -Wextra -Werror -pedantic -ffreestanding -fsanitize=address,undefined -fno-omit-frame-pointer' \
  TEST_CFLAGS='-std=c11 -Wall -Wextra -Werror -pedantic -fsanitize=address,undefined -fno-omit-frame-pointer'
```

The instrumented objects compiled, but the test link exited `2`:

```text
/usr/bin/ld: cannot find /usr/lib64/libasan.so.5.0.0
/usr/bin/ld: cannot find /usr/lib64/libubsan.so.1.0.0
collect2: error: ld returned 1 exit status
```

The ordinary reference build was restored afterward. Sanitizer checking is unavailable and no sanitizer pass is claimed.

## Metadata, entry-type, and credential audit

A strict Python JSON load rejected duplicate keys and non-finite constants, then asserted:

```text
MANIFEST schema_version == 1
PROVENANCE schema_version == 1
manifest/project project_id equality
manifest/source source_id equality
manifest source_commit == provenance source commit_hash
manifest provenance_sha256 == provenance snapshot_sha256
status == GENERATED
validation_labels == [GENERATED, PARTIAL]
independent_validation == REQUIRED
productionized == false
catalog_license == CC0-1.0
linked_resource_license == NOASSERTION
linked_content_copied == false
```

The same audit walked `CANDIDATE` with `os.lstat`, required 42 regular files, and rejected non-directory/non-regular entries. It exited `0`:

```text
strict metadata audit: PASS
regular files: 42; symlinks/special entries: 0
IDs, commit, snapshot digest, labels, and license fields: consistent
```

The following common credential-pattern scan returned grep exit `1`, meaning no match:

```sh
grep -RIE 'AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{36,}|sk-[A-Za-z0-9]{20,}|BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY' CANDIDATE
```

Searching upstream identifiers found them only in the provenance record. This does not independently prove the non-copying assertion because upstream content was unavailable.

## Label-honesty review

```sh
grep -RInE 'BUILDS|TESTED|FUZZED|BENCHMARKED|REVIEWED|TRANSFER_VERIFIED|PRODUCTIONIZED' \
  CANDIDATE/MANIFEST.yaml CANDIDATE/VALIDATION.md \
  CANDIDATE/sealed/REVIEW.md \
  CANDIDATE/sealed/production/PRODUCTIONIZATION.md
```

The only matches were the explicit disclaimer in `CANDIDATE/VALIDATION.md`. The manifest has no promoted label. Other candidate prose consistently describes local evidence and unperformed work without presenting it as independent validation.

## Archive reproducibility check

From the writable candidate copy, two clean reference archives were built two seconds apart. The first archive and its members were copied to review scratch before the second build:

```sh
timeout 30s make -C sealed/reference clean all >/dev/null
cp sealed/reference/build/libmicaos.a ../repro-first.a
cp sealed/reference/build/scheduler.o ../repro-first-scheduler.o
cp sealed/reference/build/vm.o ../repro-first-vm.o
cp sealed/reference/build/ramfs.o ../repro-first-ramfs.o
sleep 2
timeout 30s make -C sealed/reference clean all >/dev/null
sha256sum ../repro-first.a sealed/reference/build/libmicaos.a \
  ../repro-first-scheduler.o sealed/reference/build/scheduler.o \
  ../repro-first-vm.o sealed/reference/build/vm.o \
  ../repro-first-ramfs.o sealed/reference/build/ramfs.o
```

Both builds exited `0`. Observed:

```text
3775eb5c008591438074647fbe3e82a7548fbd14f824697c16e71dc9754561f5  ../repro-first.a
37f2305b3a554542e3a8c491088946ea799c055ac54e35435289c4b0906d6f91  sealed/reference/build/libmicaos.a
9ffb5f1cc4326c7e672388a6d1a97e3c474f3bb7e6dd0c4558fa6b593ab24e23  scheduler object (both builds)
7b1a1346a37ca83179cfc6ba66123f6d1640c77a74da6625dcc68e95d47b94f0  VM object (both builds)
21e98d980bf8271f9f162041dc01aa85a45009bd06989571f0dd611890c9cb19  RAMFS object (both builds)
```

Thus source compilation was byte-stable in this check, while the archive wrapper was not. `ar tv` exposed retained owner/group and build-time member metadata. The Makefile uses `ar rcs`, so a bit-reproducible archive is not established. Functional tests passed on the same toolchain and no candidate text claims byte identity.

## Progressive disclosure, usefulness, and license review

The main README links only to existing public documents. Learner-facing Makefiles and tests do not read `sealed/`. Milestones progress from initialization through lifecycle behavior and hardening; public tests are explicitly examples rather than the complete contract. Debugging and review directories expose prompts, while answer-bearing material is grouped under `sealed/`.

No exported learner filesystem was available, so actual exclusion of `sealed/` remains a worker-harness responsibility. The manifest correctly lacks `TRANSFER_VERIFIED`.

The license documents consistently distinguish CC0 catalog metadata from the `NOASSERTION` linked tutorial and state that linked text/code was not copied. The source repository and linked tutorial could not be read from this workspace, so that textual-provenance assertion is inconclusive rather than independently proven.

## Overall result and limitations

The reviewed candidate merits an advisory `PASS`: no blocking defect was found, and its current local evidence was independently reproduced. This does not mutate the candidate manifest or confer `REVIEWED`.

Unavailable or unperformed checks include a second C toolchain, sanitizers, Valgrind, named static analyzers, coverage-guided fuzzing, coverage measurement, benchmarking, cross-target or emulator execution, hardware tests, concurrency tests, production validation, upstream text comparison, historical `PRIOR_BUILD`/`PRIOR_REVIEW` comparison, and worker-harness student-view transfer validation.
