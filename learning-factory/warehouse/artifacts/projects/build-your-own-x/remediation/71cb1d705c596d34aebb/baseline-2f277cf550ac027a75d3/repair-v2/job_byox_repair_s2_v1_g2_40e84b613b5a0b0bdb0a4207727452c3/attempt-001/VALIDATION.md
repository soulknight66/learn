# Builder validation record — repair generation 2

Date: 2026-09-03 (America/Chicago)

Status remains **GENERATED + PARTIAL**. These are builder-controlled checks,
not independent validation and not evidence for `BUILDS`, `TESTED`, `FUZZED`,
`BENCHMARKED`, `REVIEWED`, `TRANSFER_VERIFIED`, or `PRODUCTIONIZED` labels.
The managed wrapper repeatedly printed `/usr/bin/id` warnings for unmapped
numeric user/group IDs; the commands below still returned the stated statuses.

## Repair scope exercised

- Child setup now checks disposition/mask operations and unblocks `SIGINT`,
  `SIGQUIT`, `SIGTSTP`, `SIGTTIN`, `SIGTTOU`, and `SIGCHLD` before a child
  built-in or `execvp`.
- Batch length accounting excludes one delimiting LF. Both exact 1 MiB forms
  and a strictly over-limit line have regressions.
- Public, sealed, adversarial, and benchmark target launches use a shared
  argv-only, new-session runner with bounded TERM/KILL process-group cleanup.
- Both Makefile `check` targets use an overridable `PYTHON` variable whose
  default is the configured Python 3.11.5 executable; Python 3.9 is the stated
  minimum.
- `LICENSE_BOUNDARY.md` gives the independently generated material an explicit
  CC0-1.0 grant while excluding the `NOASSERTION` linked resource.

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

Those exact compiler and Python paths were used below. The configured cross
compilers, Java, Node, Go, QEMU, assembler, parser generators, and GLib were
irrelevant and were not invoked.

## Normal builds

Commands from the pack root:

```sh
mkdir -p environment/.validation-tmp
TMPDIR="$PWD/environment/.validation-tmp" /usr/bin/timeout 30s \
  /usr/bin/make -C starter clean all \
  CC=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc
TMPDIR="$PWD/environment/.validation-tmp" /usr/bin/timeout 30s \
  /usr/bin/make -C sealed/reference clean all \
  CC=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc
```

Both exited 0. Compilation used
`-std=c11 -Wall -Wextra -Wpedantic -Werror -g`; GCC emitted no diagnostic.

## Normal test suites

Commands:

```sh
PYTHONDONTWRITEBYTECODE=1 TMPDIR="$PWD/environment/.validation-tmp" \
  MSH_BIN="$PWD/sealed/reference/msh" /usr/bin/timeout 60s \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  public_tests/test_shell.py
PYTHONDONTWRITEBYTECODE=1 TMPDIR="$PWD/environment/.validation-tmp" \
  MSH_BIN="$PWD/sealed/reference/msh" /usr/bin/timeout 60s \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  sealed/reference_tests/test_reference.py
PYTHONDONTWRITEBYTECODE=1 TMPDIR="$PWD/environment/.validation-tmp" \
  MSH_BIN="$PWD/sealed/reference/msh" /usr/bin/timeout 60s \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  adversarial/test_boundaries.py
```

Observed, each exit 0:

```text
public_tests/test_shell.py:             Ran 11 tests in 0.451s — OK
sealed/reference_tests/test_reference.py: Ran 17 tests in 0.726s — OK
adversarial/test_boundaries.py:          Ran 6 tests in 0.394s — OK
```

The sealed PTY regression blocked all six specified signals before `exec` of
the shell, ran `/bin/sleep 5`, sent Ctrl-C, observed a new prompt within its
two-second deadline, and reaped a clean shell exit. The boundary regression
accepted exactly 1,048,576 command bytes both at EOF and before LF, rejected
1,048,577 bytes before LF with status 2, and completed within its deadlines.
The harness self-test forked a ten-second same-group descendant, forced a
0.3-second timeout, and verified by PID that the descendant no longer existed;
the entire test completed inside the asserted 2.5-second bound.

## Makefile runner selection

Commands:

```sh
TMPDIR="$PWD/environment/.validation-tmp" /usr/bin/timeout 30s \
  /usr/bin/make -C starter check
TMPDIR="$PWD/environment/.validation-tmp" /usr/bin/timeout 30s \
  /usr/bin/make -C sealed/reference check
```

Both recipes visibly selected
`/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3`. The deliberately
incomplete starter ran all 11 tests in 0.165s with 2 passes and 9 behavioral
failures, no interpreter/API errors; the suite exit 1 made `make` exit 2. This
is an expected incomplete-starter observation, not passing evidence. The
reference recipe ran 11 tests in 0.503s, reported `OK`, and exited 0.

## Static analyzer

Command:

```sh
TMPDIR="$PWD/environment/.validation-tmp" /usr/bin/timeout 30s \
  /arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc \
  -D_POSIX_C_SOURCE=200809L -Isealed/reference/include \
  -std=c11 -Wall -Wextra -Wpedantic -Werror -fanalyzer \
  -c sealed/reference/src/msh.c \
  -o environment/.validation-tmp/msh-analyzer.o
```

Observed exit 0 with no diagnostic.

## AddressSanitizer and UndefinedBehaviorSanitizer

Build command:

```sh
TMPDIR="$PWD/environment/.validation-tmp" /usr/bin/timeout 30s \
  /usr/bin/make -C sealed/reference clean all \
  CC=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc \
  CFLAGS='-std=c11 -Wall -Wextra -Wpedantic -Werror -g -fsanitize=address,undefined -fno-omit-frame-pointer' \
  LDFLAGS='-fsanitize=address,undefined'
```

The build exited 0. Each normal-suite command above was then repeated with:

```sh
LD_LIBRARY_PATH=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64
ASAN_OPTIONS=detect_leaks=0:halt_on_error=1
UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1
```

Observed results were 11/11 in 0.607s, 17/17 in 1.199s, and 6/6 in
0.877s, all exit 0 with no ASan or UBSan diagnostic. Leak detection was
explicitly disabled, so this is not LeakSanitizer evidence.

## Benchmark-driver smoke check

After a normal warning-clean rebuild, the optional driver was exercised once:

```sh
PYTHONDONTWRITEBYTECODE=1 TMPDIR="$PWD/environment/.validation-tmp" \
  MSH_BIN="$PWD/sealed/reference/msh" /usr/bin/timeout 20s \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  benchmarks/run.py --iterations 1
```

It exited 0 and printed:

```json
{"binary": "/projects/se/pj34000401_refsys/users/yuali01/learn/learning-factory/warehouse/workspaces/job_byox_repair_s2_v1_g2_40e84b613b5a0b0bdb0a4207727452c3/attempt-001/sealed/reference/msh", "elapsed_ns": 5091627, "iterations": 1, "python": "3.11.5"}
```

This only checks driver execution and runner integration. No threshold was
specified or evaluated, and the pack does not claim `BENCHMARKED`.

## Environment, metadata, structure, and credential checks

Final commands after scratch cleanup:

```sh
PYTHONDONTWRITEBYTECODE=1 /usr/bin/timeout 20s /bin/sh environment/check.sh
PYTHONDONTWRITEBYTECODE=1 /usr/bin/timeout 20s \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 environment/audit.py
/usr/bin/sha256sum PROVENANCE.json
find AGENTS.md CONCEPTS.md DESIGN_QUESTIONS.md LICENSE_BOUNDARY.md \
  MANIFEST.yaml PROVENANCE.json README.md REQUIREMENTS.md VALIDATION.md \
  adversarial benchmarks debugging environment public_tests review_exercises \
  sealed starter -type l -print
find AGENTS.md CONCEPTS.md DESIGN_QUESTIONS.md LICENSE_BOUNDARY.md \
  MANIFEST.yaml PROVENANCE.json README.md REQUIREMENTS.md VALIDATION.md \
  adversarial benchmarks debugging environment public_tests review_exercises \
  sealed starter ! -type d ! -type f ! -type l -print
find AGENTS.md CONCEPTS.md DESIGN_QUESTIONS.md LICENSE_BOUNDARY.md \
  MANIFEST.yaml PROVENANCE.json README.md REQUIREMENTS.md VALIDATION.md \
  adversarial benchmarks debugging environment public_tests review_exercises \
  sealed starter -type f | /usr/bin/wc -l
comm -23 \
  <(cd PRIOR_BUILD && find AGENTS.md CONCEPTS.md DESIGN_QUESTIONS.md \
    LICENSE_BOUNDARY.md MANIFEST.yaml PROVENANCE.json README.md REQUIREMENTS.md \
    VALIDATION.md adversarial benchmarks debugging environment public_tests \
    review_exercises sealed starter -type f -print | sort) \
  <(find AGENTS.md CONCEPTS.md DESIGN_QUESTIONS.md LICENSE_BOUNDARY.md \
    MANIFEST.yaml PROVENANCE.json README.md REQUIREMENTS.md VALIDATION.md \
    adversarial benchmarks debugging environment public_tests review_exercises \
    sealed starter -type f -print | sort)
comm -13 \
  <(cd PRIOR_BUILD && find AGENTS.md CONCEPTS.md DESIGN_QUESTIONS.md \
    LICENSE_BOUNDARY.md MANIFEST.yaml PROVENANCE.json README.md REQUIREMENTS.md \
    VALIDATION.md adversarial benchmarks debugging environment public_tests \
    review_exercises sealed starter -type f -print | sort) \
  <(find AGENTS.md CONCEPTS.md DESIGN_QUESTIONS.md LICENSE_BOUNDARY.md \
    MANIFEST.yaml PROVENANCE.json README.md REQUIREMENTS.md VALIDATION.md \
    adversarial benchmarks debugging environment public_tests review_exercises \
    sealed starter -type f -print | sort)
test ! -e ARTIFACT_INVENTORY.sha256
```

Observed final audit output:

```text
required files: 23 present
forbidden paths: 0 present
generated entries audited: 57
regular files scanned for credential patterns: 42
metadata: strict JSON; manifest object exact; source snapshot consistent
provenance document: pinned file SHA-256 verified
```

`environment/check.sh` printed the pinned GCC and Python versions followed by
`environment prerequisites present` and exited 0. The direct provenance digest
was `8aa702b8b64241bda70f3a63e3d1b9a681e7dc87f4d5930b9b4f764f584e5dad`.
The symlink and special-entry finds printed nothing; the regular-file count was
42. The missing-prior-path `comm` printed nothing, so all 41 prior files were
preserved. The added-path `comm` printed only
`public_tests/process_harness.py`. The inventory nonexistence check exited 0.

The audit's credential scan covers all generated regular files. It also checks
all required paths, every forbidden path, strict JSON parsing, exact manifest
equality, project/snapshot identities, and the pinned provenance byte digest.
The manifest remains exactly `GENERATED` plus `PARTIAL`, with independent
validation required and `productionized: false`.

Build objects, binaries, bytecode caches, and
`environment/.validation-tmp` were removed by explicit `unlink`/`rmdir`
commands after their exact paths were enumerated. A final search for `msh`,
`*.o`, `*.pyc`, `__pycache__`, and `.validation-tmp` beneath canonical roots
printed nothing.

## Limitations

- The immutable upstream catalog/source object database and linked tutorial
  were unavailable and network access was not used. Their declared hashes,
  CC0 evidence, and the no-copy assertion were not recomputed.
- No orchestrator-created learner view was available, so actual transfer-time
  exclusion of sealed and harness-only material was not exercised.
- Sanitizer leak detection was disabled. No fault injection, coverage-guided
  fuzzing, benchmark acceptance threshold, portability matrix, or production
  readiness assessment was performed.
- Process-group timeout cleanup addresses ordinary same-group descendants. It
  is not cgroup containment for a deliberately escaping hostile process.
- Builder-authored checks and this record do not replace fresh independent
  validation.
