# Independent validation record

Date: 2026-09-03 (America/Chicago)

All commands were run from the review workspace root. `CANDIDATE/` was kept
immutable. Builds and behavioral execution used `.review-work/`, a copied
scratch tree that was deleted after validation. The managed command wrapper
repeatedly printed `/usr/bin/id` warnings for unmapped numeric user/group IDs;
those warnings did not change the recorded exit statuses.

## Tool identity

Commands:

```sh
/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc --version | sed -n '1p'
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
/usr/bin/make --version | sed -n '1p'
```

Observed, all exit 0:

```text
gcc (GCC) 15.2.0
Python 3.11.5
GNU Make 4.2.1
```

The exact GCC and Python paths above were used for every applicable check.
The configured cross-compilers, Java, Node, Go, QEMU, assembler, parser
generators, and GLib were irrelevant to this C/Python pack and were not used.

## Immutable submission, metadata, and packaging

Commands:

```sh
find CANDIDATE -type f -exec /usr/bin/sha256sum {} + \
  | LC_ALL=C sort | /usr/bin/sha256sum
/usr/bin/sha256sum CANDIDATE/PROVENANCE.json
find CANDIDATE -type l -print
find CANDIDATE ! -type d ! -type f ! -type l -print
PYTHONDONTWRITEBYTECODE=1 /usr/bin/timeout 20s \
  /bin/sh CANDIDATE/environment/check.sh
PYTHONDONTWRITEBYTECODE=1 /usr/bin/timeout 20s \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  CANDIDATE/environment/audit.py
```

Observed:

```text
b6e6cb39b1c6905f1d192fdbafdecd41a67eb34e531de14040cd9d79172b2099  -
8aa702b8b64241bda70f3a63e3d1b9a681e7dc87f4d5930b9b4f764f584e5dad  CANDIDATE/PROVENANCE.json
gcc (GCC) 15.2.0
Python 3.11.5
environment prerequisites present
required files: 23 present
forbidden paths: 0 present
generated entries audited: 57
regular files scanned for credential patterns: 42
metadata: strict JSON; manifest object exact; source snapshot consistent
provenance document: pinned file SHA-256 verified
```

Both entry-type searches printed nothing. A separate count found 42 regular
files and 24 directories. No `msh`, object, bytecode, cache, or core build
artifact existed under `CANDIDATE/`. Repeating the aggregate command after all
tests and scratch cleanup produced the same digest.

## Isolated build setup and resolved inconclusive attempt

The scratch tree was created and its bytes checked with:

```sh
test ! -e .review-work
mkdir .review-work
cp -a CANDIDATE/. .review-work/
find .review-work -type f -exec /usr/bin/sha256sum {} + \
  | sed 's#\.review-work/#CANDIDATE/#' \
  | LC_ALL=C sort | /usr/bin/sha256sum
```

The copied-tree digest was the same
`b6e6cb39b1c6905f1d192fdbafdecd41a67eb34e531de14040cd9d79172b2099`.

The first build attempt was inconclusive: `cp -a` preserved the submission's
read-only directory modes, so scratch `mkdir` and GCC output creation reported
`Permission denied`; no reference binary was produced. Those downstream
missing-binary errors are setup fallout, not behavioral failures. The retry
changed only scratch modes:

```sh
chmod -R u+w .review-work
mkdir -p .review-work/environment/.review-tmp
```

## Normal builds and supplied suites

Commands:

```sh
TMPDIR="$PWD/.review-work/environment/.review-tmp" /usr/bin/timeout 30s \
  /usr/bin/make -C .review-work/starter clean all \
  CC=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc
TMPDIR="$PWD/.review-work/environment/.review-tmp" /usr/bin/timeout 30s \
  /usr/bin/make -C .review-work/sealed/reference clean all \
  CC=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc

PYTHONDONTWRITEBYTECODE=1 \
  TMPDIR="$PWD/.review-work/environment/.review-tmp" \
  MSH_BIN="$PWD/.review-work/sealed/reference/msh" \
  /usr/bin/timeout 60s \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  .review-work/public_tests/test_shell.py
PYTHONDONTWRITEBYTECODE=1 \
  TMPDIR="$PWD/.review-work/environment/.review-tmp" \
  MSH_BIN="$PWD/.review-work/sealed/reference/msh" \
  /usr/bin/timeout 60s \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  .review-work/sealed/reference_tests/test_reference.py
PYTHONDONTWRITEBYTECODE=1 \
  TMPDIR="$PWD/.review-work/environment/.review-tmp" \
  MSH_BIN="$PWD/.review-work/sealed/reference/msh" \
  /usr/bin/timeout 60s \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  .review-work/adversarial/test_boundaries.py
```

Both builds exited 0 under
`-std=c11 -Wall -Wextra -Wpedantic -Werror -g` without a compiler diagnostic.
Suite observations:

```text
public_tests/test_shell.py:                Ran 11 tests in 0.410s — OK
sealed/reference_tests/test_reference.py:  Ran 17 tests in 0.696s — OK
adversarial/test_boundaries.py:             Ran 6 tests in 0.380s — OK
```

No PTY case was skipped.

## Static analyzer and sanitizers

Static analyzer command:

```sh
TMPDIR="$PWD/.review-work/environment/.review-tmp" /usr/bin/timeout 30s \
  /arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc \
  -D_POSIX_C_SOURCE=200809L -I.review-work/sealed/reference/include \
  -std=c11 -Wall -Wextra -Wpedantic -Werror -fanalyzer \
  -c .review-work/sealed/reference/src/msh.c \
  -o .review-work/environment/.review-tmp/msh-analyzer.o
```

Observed exit 0 with no diagnostic.

Sanitizer build command:

```sh
TMPDIR="$PWD/.review-work/environment/.review-tmp" /usr/bin/timeout 30s \
  /usr/bin/make -C .review-work/sealed/reference clean all \
  CC=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc \
  CFLAGS='-std=c11 -Wall -Wextra -Wpedantic -Werror -g -fsanitize=address,undefined -fno-omit-frame-pointer' \
  LDFLAGS='-fsanitize=address,undefined'
```

The three normal-suite commands were repeated with:

```sh
LD_LIBRARY_PATH=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64
ASAN_OPTIONS=detect_leaks=0:halt_on_error=1
UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1
```

Observed:

```text
public:       11/11 in 0.522s — OK
sealed:       17/17 in 1.011s — OK
adversarial:   6/6  in 0.622s — OK
```

All commands exited 0 with no ASan or UBSan diagnostic. Leak detection was
disabled, so these observations are not LeakSanitizer evidence.

## Makefile runner and benchmark-driver smoke

After a normal reference rebuild:

```sh
TMPDIR="$PWD/.review-work/environment/.review-tmp" /usr/bin/timeout 30s \
  /usr/bin/make -C .review-work/starter check
TMPDIR="$PWD/.review-work/environment/.review-tmp" /usr/bin/timeout 30s \
  /usr/bin/make -C .review-work/sealed/reference check
PYTHONDONTWRITEBYTECODE=1 \
  TMPDIR="$PWD/.review-work/environment/.review-tmp" \
  MSH_BIN="$PWD/.review-work/sealed/reference/msh" \
  /usr/bin/timeout 20s \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  .review-work/benchmarks/run.py --iterations 1
```

Both Makefiles visibly selected the pinned Python. The deliberately incomplete
starter ran all 11 public tests, passed 2, failed 9 behaviorally, and made
`make` exit 2. The reference ran 11/11 and exited 0. The benchmark driver
exited 0 and printed:

```json
{"binary": "<review-root>/.review-work/sealed/reference/msh", "elapsed_ns": 2669847, "iterations": 1, "python": "3.11.5"}
```

This was only a driver/runner smoke check. No performance threshold was
specified or assessed.

## Independent contract edge matrix

A 30-second-bounded Python check imported the submitted
`public_tests.process_harness.run_process`, selected the scratch reference via
an absolute `REVIEW_BIN`, and made 21 explicit assertions. The invocation was:

```sh
PYTHONDONTWRITEBYTECODE=1 \
  TMPDIR="$PWD/.review-work/environment/.review-tmp" \
  REVIEW_BIN="$PWD/.review-work/sealed/reference/msh" \
  /usr/bin/timeout 30s \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 - <<'PY'
# Each target launch used run_process(..., timeout=4, check=False).
# Assertions exercised the exact cases tabulated below.
PY
```

Cases and oracles:

| Area | Exact case or invariant | Observation |
|---|---|---|
| Invocation | `msh -c`, `msh unexpected`, and `msh -c true extra` | each status 2 |
| Exit | batch `/bin/false` then `exit` | final status 1 |
| Invalid exit | `exit 256` followed by `printf 'continued\n'` | continued, final status 0, diagnostic present |
| File mode | `printf x > PATH` under umask `0027` | content `x`, mode `0640` |
| Built-in context | `cd / \| cat`, then `/bin/pwd`, from a temporary cwd | parent cwd unchanged |
| Pipeline exit | `exit 9 \| cat`, then a later `printf` | parent continued, final status 0 |
| Process group | two Python stages each wrote `getpgrp()` to separate redirected files | both values equalled announced PGID |
| Jobs | background IDs 1, 2, 3 with completion between launches | IDs monotonic; job 3 listed Running |
| Default foreground | `fg` without an ID for jobs 1 and 3 | selected greatest live ID and waited |
| Job validation | `jobs extra`, `fg 0`, `fg %%1`, and `fg +1` | each status 1 |

Observed exit 0 and:

```text
independent edge assertions: 21 passed
```

## Independent forced-timeout escalation

A separate 10-second-bounded Python check used `run_process` to launch a
Python parent which ignored `SIGTERM`, forked a child which also ignored
`SIGTERM`, recorded the child PID, and made both processes sleep for ten
seconds. `run_process` had a 0.2-second deadline. The check required
`TimeoutExpired`, polled the recorded PID for at most one second, and failed if
the descendant remained.

Observed exit 0:

```text
forced-timeout KILL escalation: passed in 0.704s
```

This verifies ordinary same-process-group escalation, not containment of a
hostile process that deliberately escapes its session or group.

## Manual review observations

- The reference parses the full token stream before execution, uses
  `fork`/`execvp` argv execution, tracks jobs by process group, closes pipe
  endpoints, retries foreground waits after `EINTR`, resets and unblocks all
  six stated child signals, and restores parent built-in descriptors.
- Learner-facing files contain requirements, concepts, prompts, starter code,
  and black-box tests. Reference code and answer keys are beneath `sealed/`;
  harness-only indexes do not expose their answers.
- `LICENSE_BOUNDARY.md` grants generated material CC0-1.0 and explicitly
  excludes the linked `NOASSERTION` resource. The upstream material itself was
  not available for comparison.
- `MANIFEST.yaml` remains exactly `GENERATED`/`PARTIAL`, requires independent
  validation, and keeps `productionized` false. Validation prose consistently
  disclaims promoted labels and distinguishes smoke tests from evidence.
- Low-priority reproducibility gap: `environment/check.sh` does not probe all
  commands or capabilities used by the suites despite printing that
  prerequisites are present.

## Cleanup and final integrity

Before deletion, scratch build products were enumerated as the two `msh`
binaries, starter/reference objects, and analyzer object. Cleanup used an
exact validated scratch path and depth-first deletion:

```sh
review_scratch="$PWD/.review-work"
test "$review_scratch" = \
  "/projects/se/pj34000401_refsys/users/yuali01/learn/learning-factory/warehouse/workspaces/job_byox_repair_review_s2_v1_g2_a1409fb9ec954e6912d2f1f3ab62e16f/attempt-001/.review-work"
find "$review_scratch" -depth -delete
test ! -e "$review_scratch"
find CANDIDATE -type f -exec /usr/bin/sha256sum {} + \
  | LC_ALL=C sort | /usr/bin/sha256sum
```

Cleanup exited 0. The final candidate aggregate remained:

```text
b6e6cb39b1c6905f1d192fdbafdecd41a67eb34e531de14040cd9d79172b2099  -
```

## Limitations

- The upstream catalog object database and linked tutorial were unavailable;
  network access was not used. Upstream hashes, CC0 evidence, and the no-copy
  statement were not independently recomputed.
- No orchestrator-generated learner view was available, so exclusion of
  sealed and harness-only content during transfer was not exercised.
- Only the configured Linux/POSIX host, GCC 15.2.0, Python 3.11.5, and GNU Make
  4.2.1 were exercised. Python 3.9 and other POSIX platforms were not.
- There was no LeakSanitizer run, fault injection, coverage-guided fuzzing,
  benchmark threshold, portability matrix, or production assessment.
- The initial archive-mode build attempt was inconclusive as described above;
  the writable-scratch retry superseded it without changing candidate bytes.
