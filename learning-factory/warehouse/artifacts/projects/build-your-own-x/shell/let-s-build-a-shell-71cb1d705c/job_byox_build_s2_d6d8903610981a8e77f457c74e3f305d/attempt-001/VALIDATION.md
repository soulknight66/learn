# Generator-side validation evidence

Validation date: 2026-09-03 (America/Chicago). Working directory was the
repository root. This evidence records generator observations only; the
worker harness must independently validate every promotion label. The manifest
therefore remains exactly `GENERATED` + `PARTIAL`.

## Provenance boundary

The external tutorial URL was not fetched or inspected. It was treated only as
the inert catalog provenance recorded in `PROVENANCE.json`. All project prose,
code, and tests were independently generated in this workspace.

## Pinned tools

Exact command:

```sh
/bin/sh environment/check.sh
```

Observed exit status: 0. Exact output:

```text
gcc (GCC) 15.2.0
Python 3.11.5
environment prerequisites present
```

The binaries invoked by the script were:

- `/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc`
- `/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3`

## Warning-clean normal builds

Exact commands:

```sh
make -C starter clean all CC=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc
make -C sealed/reference clean all CC=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc
```

Observed exit status: 0 for each. Both compiled with
`-std=c11 -Wall -Wextra -Wpedantic -Werror -g`; the compiler emitted no
warnings. The starter was build-checked only: its marked execution TODO is
intentional, so a behavioral pass is not claimed for it.

## Normal reference tests

Exact commands:

```sh
MSH_BIN="$PWD/sealed/reference/msh" /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 public_tests/test_shell.py
MSH_BIN="$PWD/sealed/reference/msh" /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 sealed/reference_tests/test_reference.py
MSH_BIN="$PWD/sealed/reference/msh" /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 adversarial/test_boundaries.py
```

Observed exit status: 0 for each. Exact unittest summaries from the final
normal run:

```text
Ran 9 tests in 0.056s
OK
Ran 12 tests in 0.443s
OK
Ran 4 tests in 0.050s
OK
```

The 12-test sealed suite included a real pseudo-terminal scenario that stopped
a foreground process group with Ctrl-Z, observed it through `jobs`, resumed it
with `fg`, and interrupted it with Ctrl-C. The four adversarial cases are
bounded deterministic regressions, not a coverage-guided fuzzing claim.

## Address and undefined-behavior instrumentation

The instrumented build command was:

```sh
make -C sealed/reference clean all \
  CC=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc \
  CFLAGS='-std=c11 -Wall -Wextra -Wpedantic -Werror -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer' \
  LDFLAGS='-fsanitize=address,undefined'
```

Observed exit status: 0. The first test launch, without an explicit runtime
path, failed before `main` with exit 127 and this loader diagnostic:

```text
error while loading shared libraries: libasan.so.8: cannot open shared object file: No such file or directory
```

A search restricted to the configured GCC root found the runtime at
`/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64/libasan.so.8.0.0`. With that
directory supplied, `detect_leaks=1` failed in the environment rather than the
program. The repeated exact diagnostic was:

```text
LeakSanitizer has encountered a fatal error.
HINT: LeakSanitizer does not work under ptrace (strace, gdb, etc)
```

Leak detection is therefore unavailable and remains a documented partial
blocker. AddressSanitizer and UndefinedBehaviorSanitizer were rerun with leak
detection disabled using these exact commands:

```sh
LD_LIBRARY_PATH=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64 \
  ASAN_OPTIONS=detect_leaks=0:halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1 \
  MSH_BIN="$PWD/sealed/reference/msh" \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 public_tests/test_shell.py
LD_LIBRARY_PATH=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64 \
  ASAN_OPTIONS=detect_leaks=0:halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1 \
  MSH_BIN="$PWD/sealed/reference/msh" \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 sealed/reference_tests/test_reference.py
LD_LIBRARY_PATH=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64 \
  ASAN_OPTIONS=detect_leaks=0:halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1 \
  MSH_BIN="$PWD/sealed/reference/msh" \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 adversarial/test_boundaries.py
```

Observed exit status: 0 for each, with no sanitizer diagnostics. Exact
unittest summaries:

```text
Ran 9 tests in 0.324s
OK
Ran 12 tests in 0.603s
OK
Ran 4 tests in 0.234s
OK
```

This is not an independently awarded validation label.

## Packaging, path, and credential audit

Build products were explicitly removed before the archive audit. Exact
commands:

```sh
make -C starter clean
make -C sealed/reference clean
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 environment/audit.py
```

The audit is restricted to generated allowlisted roots and does not inspect
factory-control dotfiles. Observed final exit status: 0. Exact output:

```text
required files: 23 present
forbidden paths: 0 present
generated entries audited: 56
regular files scanned for credential patterns: 41
metadata: strict JSON; manifest object exact; provenance binding consistent
```

The scanner checks credential-like assignments, private-key PEM headers, and
embedded HTTP basic-auth URLs. It also rejects symlinks and special entries in
generated roots.

## Unclaimed work

The optional benchmark driver was not run, and no performance number is
claimed. No upstream access, portability matrix, production readiness,
coverage-guided fuzzing, or independent validation is claimed. Known reference
limitations are listed under `sealed/REVIEW.md` and
`sealed/production/PRODUCTIONIZATION.md`.
