# Repair generation 1 validation record

These are local worker observations from 2026-08-31 in the supplied
`America/Chicago` environment. They are not independent validation and do not
promote the artifact: `MANIFEST.yaml` remains `GENERATED` + `PARTIAL`, requires
independent validation, and has `productionized` set to false.

The command runner prefixed invocations with identity lookup warnings for
numeric user ID 532319 and group ID 500275. Those warnings came from the
runner, not from pack code. No upstream repository or linked tutorial was
accessed.

## Toolchain

Command:

```sh
timeout 15s sh environment/check_toolchain.sh
```

Observed exit status: `0`.

```text
cc: /usr/bin/cc
make: /usr/bin/make
python3: /usr/bin/python3
C compiler: cc (GCC) 8.5.0 20210514 (Red Hat 8.5.0-22)
make: GNU Make 4.2.1
python: Python 3.6.8
```

## Focused repair regressions

After a strict reference build, the two tests added for the independently
reported high-severity defects were run directly:

```sh
timeout 30s env SHELL_UNDER_TEST="$PWD/sealed/reference/byosh" \
  python3 -m unittest -v \
  sealed.reference_tests.test_shell.RedirectionAndPipelineTests.test_enoexec_file_is_not_interpreted_by_a_host_shell \
  sealed.reference_tests.test_shell.NonInteractiveJobTests.test_background_exit_is_reaped_during_foreground_wait
```

Observed exit status: `0`; both tests printed `ok`, and the runner ended with
`Ran 2 tests in 0.097s` and `OK`. The ENOEXEC case exercised both a supplied
path and controlled `PATH` lookup, required status 126, and asserted that the
file's command text produced no output. The child-reaping case synchronized
through inherited pipes, kept a foreground fixture gated, and boundedly
verified that the completed background PID disappeared from the shell's
session before releasing the foreground fixture.

## Starter and public parser boundary

Command:

```sh
timeout 30s make -C starter clean all check
```

Observed exit status: `0`. Four starter translation units compiled with
`-std=c11 -Wall -Wextra -Wpedantic -Werror -g`; `starter/byosh` linked; the
starter-owned test archive was created; and the final line was:

```text
baseline parser contract: PASS
```

The archive membership was inspected with:

```sh
ar t starter/libbyosh_test.a
```

Observed exit status: `0` and output:

```text
parser.o
pipeline.o
execute.o
```

`byosh_pipeline_init` is defined in `pipeline.o`, while the parser entry point
is in `parser.o`, so the passing baseline exercised a real cross-translation-
unit parser link rather than only documenting configurability.

The intentionally incomplete later milestone was then checked:

```sh
timeout 30s make -C starter check-milestones
```

Observed exit status: `2`. Compilation and archive linking succeeded; the
starter then reported exactly `20 milestone assertion(s) failed`. The original
quote/operator milestones remain learner work, while the new exact and
one-past command-capacity cases account for three additional expected failures.
This is the intended initial boundary, not a passing completed-shell claim.

## Sealed reference and full behavior suite

Clean build command:

```sh
timeout 45s make -C sealed/reference clean all
```

Observed exit status: `0`. GCC compiled `main.c`, `lexer.c`, `parser.c`,
`jobs.c`, and `builtins.c` with
`-D_POSIX_C_SOURCE=200809L -std=c11 -Wall -Wextra -Wpedantic -Werror -O2 -g`
and linked `sealed/reference/byosh`.

Full sealed-suite command:

```sh
timeout 120s make -C sealed/reference_tests test
```

Observed exit status: `0`:

```text
Ran 34 tests in 3.594s

OK
```

All 34 cases printed `ok`; none printed `skipped`. This run included both new
repair regressions as well as parsing, redirection, descriptor-layout,
pipeline, status, built-in, background, idle-reaping, and pseudo-terminal job
control cases.

Public black-box command:

```sh
timeout 45s make -C public_tests cli SHELL_UNDER_TEST=../sealed/reference/byosh
```

Observed exit status: `0` and final output:

```text
completed-shell public smoke tests: PASS
```

## Metadata, preservation, disclosure, and final audit

A read-only preservation check enumerated every regular file under
`PRIOR_BUILD/` and tested the corresponding top-level pack path. It observed:

```text
prior_regular_files=62
missing_at_pack_root=0
```

The provenance canonical digest and conservative manifest fields were read
independently of the pack audit with Python's JSON parser. Observed output:

```text
0343524004b914e47b5ad2522b50dedc30016985a996823676752128998bf4d9
GENERATED
GENERATED,PARTIAL
false
REQUIRED
```

After `make clean` in `public_tests/`, `starter/`, and `sealed/reference/`, and
after deleting only generated `*.pyc`/empty `__pycache__` paths beneath the
sealed test directory, the audit command was:

```sh
timeout 20s python3 sealed/reference_tests/audit_pack.py
```

Observed exit status: `0`:

```text
pack audit: PASS
required files: 23
forbidden paths: 0
locally sealed exercise answers: 6
allowlisted learner-view files: 20
symlinks or special files: 0
credential-scanned generated files: 64
manifest labels: GENERATED, PARTIAL
```

The 20-file learner-view allowlist is explicit and exact. This worker did not
materialize a learner workspace. The allowlist and local audit are not evidence
of a harness-controlled transfer, so `TRANSFER_VERIFIED` is not claimed.

## Unperformed checks and remaining limits

This repair run did not perform sanitizer execution, fuzzing, allocation/fork
fault injection, syscall tracing, multi-platform testing, a benchmark, or an
upstream similarity/license comparison. It did not independently materialize
or validate a transferred learner view. No labels for `TESTED`, `FUZZED`,
`BENCHMARKED`, `REVIEWED`, `TRANSFER_VERIFIED`, or `PRODUCTIONIZED` are claimed;
a fresh independent review remains mandatory.
