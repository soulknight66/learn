# Repair validation record

Date: 2026-09-02 (America/Chicago)

Scope: local repair-builder evidence only. The upstream URL was not accessed;
no checkout, network request, or dependency download was attempted. These
observations do not replace the independent validation required by
`MANIFEST.yaml`, and they do not promote a validation label.

The pack remains `GENERATED` + `PARTIAL`, with `productionized: false`.

## Toolchains actually invoked

Configured read-only tools were invoked by absolute path without adding their
roots to `PATH`:

```bash
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc --version
/usr/bin/make --version | head -n 1
/usr/bin/python3 --version
```

Observed first lines, respectively:

```text
Python 3.11.5
gcc (GCC) 15.2.0
GNU Make 4.2.1
Python 3.6.8
```

The non-mutating environment probe also ran successfully:

```bash
/usr/bin/timeout 20s /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 environment/check_toolchain.py
```

Observed exit status: 0. It reported `/usr/bin/cc` as GCC 8.5.0,
`/usr/bin/make` as GNU Make 4.2.1, `/usr/bin/python3` as Python 3.6.8, and the
machine as `x86_64`.

## Workspace-specific temporary-directory observation

The first sealed-suite attempt used the configured Python without `TMPDIR`:

```bash
/usr/bin/timeout 90s env PEBBLE_BIN="$PWD/sealed/reference/pebble" CC=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 sealed/reference_tests/run_tests.py
```

Observed exit status: 1. `unittest` ran 13 test methods and reported 23 errors;
each test needing `TemporaryDirectory` failed with `FileNotFoundError: No
usable temporary directory found` because `/tmp`, `/var/tmp`, `/usr/tmp`, and
the workspace root were not test-writable in this sandbox. This was a harness
environment failure, not a Pebble result.

For subsequent runs, `environment/validation-tmp` was created explicitly and
commands used `TMPDIR="$PWD/environment/validation-tmp"`. The directory was
empty after each suite and was removed during final cleanup.

## Ordinary strict builds

Commands:

```bash
/usr/bin/timeout 60s /usr/bin/make -C sealed/reference clean all CC=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc
/usr/bin/timeout 60s /usr/bin/make -C starter clean all CC=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc
```

Observed exit status: 0 for both. The reference compiled two translation units
and the starter compiled three. Both used
`-std=c11 -O2 -g -Wall -Wextra -Wpedantic -Werror`; reference compilation also
used `_POSIX_C_SOURCE=200809L`.

## Deterministic suites

Final sealed reference run:

```bash
/usr/bin/timeout 90s env TMPDIR="$PWD/environment/validation-tmp" PEBBLE_BIN="$PWD/sealed/reference/pebble" CC=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 sealed/reference_tests/run_tests.py
```

Observed exit status: 0. Thirteen test methods ran in 2.781 seconds; all were
`ok`, and `unittest` reported `OK`. Repair-specific assertions established:

- interpreter and linked-native writes to `/dev/full` returned 66 with exactly
  `I/O error: cannot write standard output` on standard error;
- both backends also returned 66 for a broken pipe rather than dying from
  `SIGPIPE`;
- `let x = 1; let x = missing;` diagnosed the duplicate `x` first;
- a 131,072-byte child stream retained exactly 65,536 bytes and set the
  truncation indicator; and
- timeout cleanup killed a TERM-ignoring descendant that retained the captured
  pipes, so its delayed escape marker was never created.

The same 13-test suite was separately run under the advertised system Python:

```bash
/usr/bin/timeout 90s env TMPDIR="$PWD/environment/validation-tmp" PEBBLE_BIN="$PWD/sealed/reference/pebble" CC=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc /usr/bin/python3 sealed/reference_tests/run_tests.py
```

Observed exit status: 0 under Python 3.6.8. All 13 methods were `ok` and the
suite reported `OK` after 2.881 seconds.

Final public and adversarial runs against the sealed reference:

```bash
/usr/bin/timeout 60s env TMPDIR="$PWD/environment/validation-tmp" PEBBLE_BIN="$PWD/sealed/reference/pebble" CC=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 public_tests/run_tests.py
/usr/bin/timeout 60s env TMPDIR="$PWD/environment/validation-tmp" PEBBLE_BIN="$PWD/sealed/reference/pebble" /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 adversarial/run_tests.py
```

Observed exit status: 0 for both. Public tests passed 6/6 in 0.150 seconds,
including compile/link/native execution. Adversarial tests passed 7/7 in 0.124
seconds.

The intentionally incomplete starter was also observed, not treated as a
passing implementation:

```bash
/usr/bin/timeout 60s env TMPDIR="$PWD/environment/validation-tmp" PEBBLE_BIN="$PWD/starter/pebble" CC=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 public_tests/run_tests.py
/usr/bin/timeout 30s env TMPDIR="$PWD/environment/validation-tmp" CC=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 public_tests/run_lexer_tests.py
```

Observed exit status: 1 for each. The end-to-end suite failed 6/6 with the
documented starter-incomplete diagnostics. The new incremental lexer milestone
reported `token 0 mismatch: kind=0 text='' location=1:1 integer=0`, which is the
expected first TODO rather than a claimed pass.

## Sanitizer attempt and limitation

The configured GCC located its sanitizer runtimes and built the reference:

```bash
/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc -print-file-name=libasan.so
/usr/bin/timeout 60s /usr/bin/make -C sealed/reference clean all CC=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc CFLAGS='-std=c11 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer'
```

Observed exit status: 0. Running without an explicit runtime path then failed
with status 127 because the loader could not find `libasan.so.8`. With
`LD_LIBRARY_PATH=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64`, execution began,
but `ASAN_OPTIONS=detect_leaks=1` ended with `LeakSanitizer has encountered a
fatal error` and the reported explanation that LeakSanitizer does not work
under ptrace.

The bounded ASan/UBSan run that this sandbox supports was:

```bash
/usr/bin/timeout 120s env TMPDIR="$PWD/environment/validation-tmp" PEBBLE_BIN="$PWD/sealed/reference/pebble" CC=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc LD_LIBRARY_PATH=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64 ASAN_OPTIONS=detect_leaks=0:halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1 /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 sealed/reference_tests/run_tests.py
```

Observed exit status: 0. All 13 methods passed in 3.482 seconds with no emitted
ASan or UBSan diagnostic. Leak checking is not claimed. The ordinary build was
restored afterward. No fuzzing, profiling, or cross-architecture execution was
performed.

## Benchmark-harness smoke only

Command:

```bash
/usr/bin/timeout 60s env TMPDIR="$PWD/environment/validation-tmp" /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 benchmarks/run_benchmark.py --binary sealed/reference/pebble --cc /arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc --iterations 100 --repetitions 1
```

Observed exit status: 0. It validated both outputs and reported one
interpreter sample of 0.002999524585902691 seconds and one compiled sample of
0.002115407958626747 seconds. This single smoke run is environment-dependent,
asserts no threshold, and does not justify a `BENCHMARKED` label.

## Process-containment audit

```bash
grep -R -n 'subprocess\.run' public_tests adversarial sealed/reference_tests benchmarks environment
grep -R -nE 'start_new_session|killpg|SIGTERM|SIGKILL|CAPTURE_LIMIT' public_tests adversarial sealed/reference_tests benchmarks environment --exclude='*.pyc'
```

The first command exited 1 with no matches. The second exited 0 and located the
central 65,536-byte capture constant, `start_new_session=True`, group signaling
with `killpg`, the TERM/KILL escalation, and the sealed regressions. All five
runner areas import that central argv-only implementation.

## Final structure, metadata, and hygiene

Scratch executables, objects, bytecode caches, and the temporary-directory root
were removed. Then these commands ran from the pack root:

```bash
/usr/bin/timeout 20s /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 sealed/reference_tests/verify_artifact.py
sha256sum MANIFEST.yaml PROVENANCE.json
find starter public_tests environment -type d \( -name sealed -o -name reference -o -name reference_tests -o -name hidden_tests -o -name solution -o -name solutions -o -name answers \) -print
```

Observed hashes:

```text
ba3e84a7d6122a40394ede353841fc4d8396eff2a7adf7d4d7962bdf45711593  MANIFEST.yaml
a923b5d3d1b9eddb2f2bc1fa7e93d5f28fe40ea8ef4727165ac9ad313ea0504d  PROVENANCE.json
```

The learner-path `find` printed nothing. The verifier exited 0 and printed:

```text
required regular files: 23/23
forbidden paths present: 0
symlinks or special files: 0
expected pack files: 53/53; unexpected: 0
credential scan: 53 text files, 0 high-confidence hits
metadata: strict JSON, exact manifest, immutable metadata hashes verified
provenance digest target: logical snapshot identifier, not file bytes
payload inventory: delegated to factory content-addressed artifact inventory
artifact verification: OK
```

The manifest's `provenance_sha256` is intentionally the immutable logical
snapshot identifier equal to `PROVENANCE.json.snapshot_sha256`, not the byte
hash printed above. In accordance with the factory contract, no local artifact
inventory root was created; the orchestrator supplies the content-addressed
payload inventory independently.
