# Independent validation record

Date: 2026-09-03 (America/Chicago)

All executable checks used an isolated copy. `CANDIDATE/` was never built in or
edited. The managed wrapper printed repeated `/usr/bin/id` warnings for unmapped
numeric IDs; they did not change the recorded exit statuses. The temporary copy
was `.review-tmp.KOY9Du` and was removed after validation.

## Tool identity

Commands:

```sh
/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc --version | /usr/bin/sed -n '1p'
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
/usr/bin/make --version | /usr/bin/sed -n '1p'
/usr/bin/python3 --version
```

Observed, all exit 0:

```text
gcc (GCC) 15.2.0
Python 3.11.5
GNU Make 4.2.1
Python 3.6.8
```

The first two are the exact configured toolchain paths used for compilation and
tests. No required configured toolchain was unavailable. The other configured
cross compilers, Java, Node, Go, QEMU, assembler, parser generators, and GLib
were irrelevant and were not invoked. `rg` and `git` were absent from PATH.

## Candidate integrity and metadata

Commands, from the workspace root:

```sh
find CANDIDATE -type f -print0 | /usr/bin/sort -z \
  | /usr/bin/xargs -0 /usr/bin/sha256sum | /usr/bin/sha256sum
find CANDIDATE -type f | /usr/bin/wc -l
find CANDIDATE -type l -print
find CANDIDATE ! -type d ! -type f ! -type l -print
/usr/bin/sha256sum CANDIDATE/PROVENANCE.json
PYTHONDONTWRITEBYTECODE=1 /usr/bin/timeout 20s \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  CANDIDATE/environment/audit.py
```

Observed:

```text
aggregate digest before review: 466ca2eb284c88e7e4a5205ff605bcc4e4557422c04c8cfedd32bedaf029cc6c
regular files: 41
symlinks: none
special entries: none
PROVENANCE.json: 8aa702b8b64241bda70f3a63e3d1b9a681e7dc87f4d5930b9b4f764f584e5dad
required files: 23 present
forbidden paths: 0 present
generated entries audited: 56
regular files scanned for credential patterns: 41
metadata: strict JSON; manifest object exact; source snapshot consistent
provenance document: pinned file SHA-256 verified
```

An independent strict-JSON assertion also confirmed matching project IDs and
snapshot identifiers plus exactly `GENERATED`, `PARTIAL`,
`independent_validation: REQUIRED`, and `productionized: false`. The aggregate
candidate digest was recomputed after all checks and remained identical.

## Isolated builds

The copied tree was made writable only after copying, because `cp -a` preserved
the immutable candidate directory mode. Commands in the copy:

```sh
TMPDIR="$PWD/.tmp" /usr/bin/timeout 30s /usr/bin/make \
  -C sealed/reference clean all \
  CC=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc
TMPDIR="$PWD/.tmp" /usr/bin/timeout 30s /usr/bin/make \
  -C starter clean all \
  CC=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc
```

Both exited 0. GCC emitted no diagnostics under
`-std=c11 -Wall -Wextra -Wpedantic -Werror -g`.

## Normal suites

Each suite used this prefix and its listed script:

```sh
PYTHONDONTWRITEBYTECODE=1 TMPDIR="$PWD/.tmp" \
  MSH_BIN="$PWD/sealed/reference/msh" /usr/bin/timeout 60s \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 SCRIPT
```

Observed:

| Script | Result | Exit |
|---|---:|---:|
| `public_tests/test_shell.py` | 11 tests, OK (0.409 s) | 0 |
| `sealed/reference_tests/test_reference.py` | 16 tests, OK (0.532 s) | 0 |
| `adversarial/test_boundaries.py` | 4 tests, OK (0.048 s) | 0 |

The same public command against `starter/msh` ran 11 tests in 0.166 s and exited
1 with 2 passes and 9 failures, matching the candidate's intentional-incomplete
disclosure.

The documented negative PTY check was also repeated:

```sh
PYTHONDONTWRITEBYTECODE=1 TMPDIR="$PWD/.tmp" MSH_BIN=/bin/sh \
  /usr/bin/timeout 10s \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  sealed/reference_tests/test_reference.py \
  InteractiveJobControlTests.test_stop_list_resume_and_interrupt_foreground_job
```

It exited 1 after 4.028 s with the claimed bounded `TimeoutError` and observed
`bash-4.4$ ` instead of `msh$ `; the outer timeout did not fire.

## Independent contract checks

A temporary reviewer script invoked the copied reference with bounded
subprocess/PTY cleanup. Its three cases were:

1. `b"true"` padded with spaces to exactly 1,048,576 bytes and followed by LF;
2. the identical line ending at EOF;
3. a PTY shell exec'd after blocking `SIGINT`, followed by `/bin/sleep 10`,
   Ctrl-C, and a one-second prompt deadline.

Command:

```sh
PYTHONDONTWRITEBYTECODE=1 TMPDIR="$PWD/.tmp" /usr/bin/timeout 15s \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  reviewer_checks.py "$PWD/sealed/reference/msh"
```

Observed exit 1:

```text
inherited-blocked-SIGINT case: ERROR, prompt absent after Ctrl-C
exact 1 MiB at EOF: ok, return 0
exact 1 MiB plus LF: FAIL, return 2
diagnostic: msh: syntax: input line exceeds 1 MiB
Ran 3 tests in 1.136s
```

The PTY failure path captured both the shell and foreground process groups and
completed bounded `SIGKILL` cleanup.

## Harness containment probe

A temporary executable forked a ten-second sleeper and then blocked. It was
passed to `public_tests.test_shell.run_command` with a 0.3-second timeout. A
supervisor checked the recorded descendant PID and killed it immediately.

```sh
/bin/chmod 700 leaky_target.py
PYTHONDONTWRITEBYTECODE=1 /usr/bin/timeout --kill-after=1s 5s \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  check_timeout_cleanup.py
```

Observed exit 0 from the probe:

```text
timeout_elapsed=0.303s descendant_alive=True
```

Thus the API deadline returns promptly but does not contain the target's
descendants.

## Static and sanitizer checks

Static analyzer command:

```sh
TMPDIR="$PWD/.tmp" /usr/bin/timeout 30s \
  /arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc \
  -D_POSIX_C_SOURCE=200809L -Isealed/reference/include \
  -std=c11 -Wall -Wextra -Wpedantic -Werror -fanalyzer \
  -c sealed/reference/src/msh.c -o .tmp/msh-analyzer.o
```

It exited 0 with no diagnostic.

The reference was rebuilt with
`-fsanitize=address,undefined -fno-omit-frame-pointer` and linked with
`-fsanitize=address,undefined`; the build exited 0. All three normal suites were
then rerun with:

```sh
LD_LIBRARY_PATH=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64
ASAN_OPTIONS=detect_leaks=0:halt_on_error=1
UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1
```

Observed results were 11/11 in 0.571 s, 16/16 in 0.951 s, and 4/4 in 0.285 s,
all exit 0 with no ASan/UBSan diagnostic. Leak detection was disabled, so this
is not LeakSanitizer evidence.

## Learner-facing `make check`

Command in the isolated copy:

```sh
TMPDIR="$PWD/.tmp" PYTHONDONTWRITEBYTECODE=1 /usr/bin/timeout 30s \
  /usr/bin/make -C starter check
```

It selected unpinned `/usr/bin/python3` 3.6.8 and exited 2. All 11 tests errored:
ordinary cases rejected the unsupported `text=` argument and the PTY case lacked
`os.waitstatus_to_exitcode`. This is distinct from the expected behavioral
failures observed with the pinned Python 3.11.5 command.

## Limitations

- The immutable catalog baseline and linked external repository were not in the
  workspace, and network access was restricted. Their hashes, license, and the
  candidate's independent-creation assertion could not be verified.
- No learner-view or transfer artifact was provided. Directory placement was
  inspected, but sealed-content exclusion by the orchestrator is inconclusive.
- Review covered one managed Linux/POSIX environment. It did not establish
  cross-platform behavior, allocation/fork failure handling, coverage-guided
  fuzzing, benchmarking, leak freedom, or production readiness.
- This advisory verdict does not publish a `REVIEWED` label; only the separate
  orchestrator-controlled acceptance validator can do that.
