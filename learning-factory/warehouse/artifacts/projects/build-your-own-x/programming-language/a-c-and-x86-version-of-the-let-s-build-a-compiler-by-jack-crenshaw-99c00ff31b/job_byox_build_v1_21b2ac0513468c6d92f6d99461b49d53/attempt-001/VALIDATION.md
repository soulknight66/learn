# Validation record

Validation date: 2026-08-31 (America/Chicago). Commands were run from the
artifact root unless a command itself uses `make -C`. Results below are observed
on this host, not inferred. Independent validation remains mandatory.

## Environment

Command:

```bash
python3 environment/check_environment.py
```

Observed status 0:

```text
cc: cc (GCC) 8.5.0 20210514 (Red Hat 8.5.0-22)
make: GNU Make 4.2.1
python3: Python 3.6.8
machine: x86_64
```

The host has no `/tmp`; an initial bare `mktemp -d` reported `No such file or
directory`. The successful native smoke check and both Python suites therefore
use explicit workspace-local scratch directories. Two disposable files created
by that first smoke attempt (`/fib` and `/fib.s`) were explicitly unlinked; they
are not artifact inputs and were not retained.

## Starter build and intentionally incomplete baseline

Commands:

```bash
make -C starter clean all
python3 public_tests/test_public.py
```

The build returned 0 with this compilation line and no diagnostic:

```text
cc -Iinclude -std=c11 -O2 -g -Wall -Wextra -Wpedantic -Werror -o mica src/mica.c
```

The public suite returned 1: 7 tests ran, 2 lexer tests passed, and 5 tests for
unfinished parser/backend behavior failed. Each stage failure exposed the
starter's explicit message:

```text
mica: implementation error: parser and backend stages are not implemented
```

This is the expected learner starting point and is one reason the artifact
retains the `PARTIAL` label.

## Reference build

Command:

```bash
make -C sealed/reference clean all
```

Observed status 0 with the same C11 warning-as-error flags. No compiler or linker
diagnostic was emitted.

## Public suite against the reference

Command:

```bash
MICA_BIN=sealed/reference/mica python3 public_tests/test_public.py
```

Observed status 0:

```text
Ran 7 tests in 0.163s

OK
```

The suite assembled and linked generated x86-64 output with `cc -no-pie` as part
of its differential test.

## Sealed reference suite

Command:

```bash
MICA_BIN=sealed/reference/mica python3 sealed/reference_tests/test_reference.py
```

Observed status 0:

```text
Ran 14 tests in 0.740s

OK
```

Covered cases include all operator classes, malformed bytes, source/variable/
depth/step limits, deterministic emission, native error exits, skipped
declarations, the exceptional signed-division pair, and 80 fixed-seed generated
expression trees compared across interpreter and native output.

The Makefile wrapper was also checked:

```bash
make -C sealed/reference check
```

Observed status 0; the same 14 tests passed in 0.737s.

## Standalone native smoke check

Commands:

```bash
mkdir -p environment/.validation-tmp
sealed/reference/mica compile sealed/reference/examples/fibonacci.mica -o environment/.validation-tmp/fib.s
cc -no-pie environment/.validation-tmp/fib.s -o environment/.validation-tmp/fib
environment/.validation-tmp/fib
```

Observed status 0 and stdout:

```text
0
1
1
2
3
5
8
13
21
34
```

Both generated files and the scratch directory were then removed.

## Final artifact hygiene

After `make -C starter clean` and `make -C sealed/reference clean` removed the
two host-specific binaries, the reproducible final check was:

```bash
python3 environment/verify_artifact.py
```

Observed status 0:

```text
required-paths: 23/23 regular files present
forbidden-paths: absent
symlinks-or-special-files: 0
learner-directory-forbidden-names: 0
metadata: strict JSON and exact expected objects
credential-pattern-scan: no matches
```

## Informative unavailable check

The following exact command sequence attempted an AddressSanitizer and
UndefinedBehaviorSanitizer build and then named the intended test commands:

```bash
make -C sealed/reference clean all CFLAGS='-std=c11 -O1 -g -Wall -Wextra -Wpedantic -Werror -fsanitize=address,undefined -fno-omit-frame-pointer'
ASAN_OPTIONS=detect_leaks=1 MICA_BIN=sealed/reference/mica python3 public_tests/test_public.py
ASAN_OPTIONS=detect_leaks=1 MICA_BIN=sealed/reference/mica python3 sealed/reference_tests/test_reference.py
```

The linker failed the first command:

```text
/usr/bin/ld: cannot find /usr/lib64/libasan.so.5.0.0
/usr/bin/ld: cannot find /usr/lib64/libubsan.so.1.0.0
collect2: error: ld returned 1 exit status
```

Because the three lines were not joined with `&&`, the two suites subsequently
attempted to launch the absent binary and reported 7 and 14 `FileNotFoundError`
errors respectively. Those are consequences of the unavailable sanitizer
runtime, not test results. No sanitizer coverage is claimed. The reference was
then rebuilt normally and both suites passed as recorded above.

## Labels and limitations

No independent validator was run by this worker. No `BUILDS`, `TESTED`, `FUZZED`,
`BENCHMARKED`, `REVIEWED`, `TRANSFER_VERIFIED`, or `PRODUCTIONIZED` label is
claimed. `MANIFEST.yaml` intentionally remains exactly `GENERATED` + `PARTIAL`.
