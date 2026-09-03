# Independent validation record

Date: 2026-09-02 (America/Chicago)

All compilation and generated artifacts were confined to a writable byte-for-byte copy at `REVIEW_SCRATCH/candidate`. `CANDIDATE/` was read only. The scratch tree was removed after recording results.

The command shell prepended UID/GID name-lookup warnings in this managed sandbox. Those harness messages were outside the tested child processes and did not affect command status or candidate stdout/stderr assertions.

## Tools

Commands and observed versions:

```bash
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
# Python 3.11.5

/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc --version
# gcc (GCC) 15.2.0

/usr/bin/make --version
# GNU Make 4.2.1

/usr/bin/python3 --version
# Python 3.6.8

/usr/bin/uname -m
# x86_64
```

The JDK, ARM/AArch64 cross-compilers, QEMU, GLib, Node, Go, NASM, standalone binutils, flex, and bison were not needed and were not exercised.

## Immutability and structure

The following relative-path aggregate was computed before and after review:

```bash
cd CANDIDATE
find . -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum
```

Both observations were:

```text
bb98aa9da367ff50487f08455dd48110f4624e5e62b516ed4a49a58aacfb942d  -
```

The same command in the writable copy produced the same value before compilation. This is a reviewer convenience digest over individual hashes plus relative paths, not a replacement for the factory artifact inventory.

A reviewer-authored Python check independently parsed the manifest/provenance, checked exact manifest keys and status, cross-file IDs and logical digest, file types, learner-root names, and high-confidence credential patterns. It exited 0 and reported:

```text
metadata: strict JSON, exact keys/status, cross-file identifiers and logical provenance digest agree
structure: 53 regular files, 0 symlinks/special files, 0 forbidden-name leaks in learner roots
credential scan: 53 files, 0 high-confidence pattern hits
byte hashes: MANIFEST.yaml and PROVENANCE.json match the submitted validation record
```

The reproduced byte hashes were:

```text
ba3e84a7d6122a40394ede353841fc4d8396eff2a7adf7d4d7962bdf45711593  MANIFEST.yaml
a923b5d3d1b9eddb2f2bc1fa7e93d5f28fe40ea8ef4727165ac9ad313ea0504d  PROVENANCE.json
```

The candidate-supplied artifact verifier was also invoked, but was not used as independent proof:

```bash
cd CANDIDATE
/usr/bin/timeout 20s /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 sealed/reference_tests/verify_artifact.py
```

It exited 0 with 23/23 required files, 53/53 expected files, no unexpected/special/forbidden paths, no credential hits, and `artifact verification: OK`, consistent with the independent check.

## Strict builds

Run from the writable candidate copy:

```bash
/usr/bin/timeout 60s /usr/bin/make -C sealed/reference clean all \
  CC=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc

/usr/bin/timeout 60s /usr/bin/make -C starter clean all \
  CC=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc
```

Both exited 0. Every translation unit used C11 plus `-Wall -Wextra -Wpedantic -Werror`.

The advertised system compiler was checked separately:

```bash
/usr/bin/timeout 60s /usr/bin/make -C sealed/reference clean all CC=/usr/bin/cc
```

It exited 0 with `/usr/bin/cc` reporting GCC 8.5.0.

## Supplied suites, independently invoked

With `REVIEW_ROOT` set to the absolute writable-copy path and `TMPDIR="$REVIEW_ROOT/validation-tmp"`:

```bash
/usr/bin/timeout 120s env TMPDIR="$TMPDIR" \
  PEBBLE_BIN="$REVIEW_ROOT/sealed/reference/pebble" \
  CC=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  sealed/reference_tests/run_tests.py

/usr/bin/timeout 90s env TMPDIR="$TMPDIR" \
  PEBBLE_BIN="$REVIEW_ROOT/sealed/reference/pebble" \
  CC=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  public_tests/run_tests.py

/usr/bin/timeout 90s env TMPDIR="$TMPDIR" \
  PEBBLE_BIN="$REVIEW_ROOT/sealed/reference/pebble" \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  adversarial/run_tests.py
```

Observed results:

- reference suite: exit 0, 13 methods, all `ok`, `OK`;
- public suite: exit 0, 6 methods, all `ok`, `OK`;
- adversarial suite: exit 0, 7 methods, all `ok`, `OK`.

The reference suite was rerun with `/usr/bin/python3` 3.6.8 and again passed 13/13. A reference built with `/usr/bin/cc` and exercised with Python 3.6.8 passed the public suite 6/6, including compile/link/native execution.

The starter was explicitly checked and not mistaken for a solution:

```bash
/usr/bin/timeout 60s env TMPDIR="$TMPDIR" \
  PEBBLE_BIN="$REVIEW_ROOT/starter/pebble" \
  CC=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 public_tests/run_tests.py

/usr/bin/timeout 60s env TMPDIR="$TMPDIR" \
  CC=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 public_tests/run_lexer_tests.py
```

The first exited 1 with 6/6 expected failures carrying the documented starter-incomplete diagnostic. The lexer check exited 1 with `token 0 mismatch: kind=0 text='' location=1:1 integer=0`. These observations agree with the declared `PARTIAL` state.

## Reviewer-authored black-box checks

An ephemeral deterministic Python driver (seed `20260902`) used argv-only subprocesses, per-command timeouts, new sessions, captured streams, and process-group cleanup. It implemented an independent signed-64-bit oracle, then invoked the rebuilt CLI in interpreter and compile/link/native modes:

```bash
/usr/bin/timeout 150s \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  REVIEW_SCRATCH/independent_checks.py
```

Observed exit status: 0.

```text
independent arithmetic oracle: 80 eval/compile/link/native cases passed
independent exact-boundary checks: 11 passed
independent process-runner hostile cases: 2 passed
```

The arithmetic cases included each operator, signed division/remainder, zero division, `INT64_MIN / -1`, unary negation overflow, and other overflow boundaries. Exact checks covered the 128/129 parenthesis, AST, and block boundaries; 256/257 variables; duplicate-before-invalid-initializer resolution; and exact fuel exhaustion. Runner checks independently stressed both streams above 150 KiB and a TERM-ignoring, pipe-holding descendant; capture stopped at 65,536 bytes per stream and the escape marker was not created.

## Sanitizers

```bash
/usr/bin/timeout 60s /usr/bin/make -C sealed/reference clean all \
  CC=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc \
  CFLAGS='-std=c11 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer'

/usr/bin/timeout 150s env TMPDIR="$TMPDIR" \
  PEBBLE_BIN="$REVIEW_ROOT/sealed/reference/pebble" \
  CC=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc \
  LD_LIBRARY_PATH=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64 \
  ASAN_OPTIONS=detect_leaks=0:halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1 \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  sealed/reference_tests/run_tests.py
```

Build and suite exited 0; all 13 methods passed with no ASan/UBSan diagnostic. The reviewer-authored 80 oracle and 11 boundary cases were also repeated under these sanitizer settings and passed without diagnostics.

Leak checking was attempted separately:

```bash
/usr/bin/timeout 30s env \
  LD_LIBRARY_PATH=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64 \
  ASAN_OPTIONS=detect_leaks=1:halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1 \
  sealed/reference/pebble eval starter/examples/count.pb
```

It printed `15`, then exited 1 because LeakSanitizer reported that it does not work under ptrace. Leak freedom is not claimed.

## Deterministic output and benchmark smoke

```bash
sealed/reference/pebble compile starter/examples/count.pb -o validation-tmp/count-a.s
sealed/reference/pebble compile starter/examples/count.pb -o validation-tmp/count-b.s
cmp validation-tmp/count-a.s validation-tmp/count-b.s
sha256sum validation-tmp/count-a.s validation-tmp/count-b.s
```

Both compiles and `cmp` exited 0. Both assembly files had SHA-256:

```text
e3b715942409fc384005fecd7bb9e77c9f0af05f6474441b4a4f7cc6e09ea4cf
```

The optional benchmark harness was smoke-run with 100 loop iterations and one repetition. It exited 0 after validating outputs and reported one interpreter sample of `0.0027354280464351177` seconds and one compiled sample of `0.0024267970584332943` seconds. This environment-dependent single sample establishes only harness operation, not `BENCHMARKED` status.

## Limitations and label discipline

- No network or immutable upstream snapshot was available; upstream provenance/license/no-copy claims are internally consistent but externally inconclusive.
- The external factory payload inventory and actual learner-view export were unavailable, so `TRANSFER_VERIFIED` and delivery-time sealed isolation are not established.
- No fuzzing, profiling, performance threshold, cross-architecture execution, or production hardening was performed.
- Generated material has no public redistribution license, as explicitly documented.
- The manifest was not edited. This advisory PASS does not itself publish `BUILDS`, `TESTED`, `FUZZED`, `BENCHMARKED`, `REVIEWED`, `TRANSFER_VERIFIED`, or `PRODUCTIONIZED`.
