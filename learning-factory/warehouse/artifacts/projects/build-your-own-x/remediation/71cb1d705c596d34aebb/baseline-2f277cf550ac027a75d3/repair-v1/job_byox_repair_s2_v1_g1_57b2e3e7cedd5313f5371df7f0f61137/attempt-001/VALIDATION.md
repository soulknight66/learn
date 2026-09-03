# Builder validation record — repair generation 1

Date: 2026-09-03 (America/Chicago)

Status remains **GENERATED + PARTIAL**. These are builder-controlled checks,
not independent validation and not evidence for `BUILDS`, `TESTED`, `FUZZED`,
`BENCHMARKED`, `REVIEWED`, `TRANSFER_VERIFIED`, or `PRODUCTIONIZED` labels.
The managed wrapper repeatedly printed `/usr/bin/id` warnings for unmapped
numeric user/group IDs; the commands below still returned the stated statuses.

## Tool identity

Commands:

```sh
/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc --version | sed -n '1p'
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
/usr/bin/make --version | sed -n '1p'
```

Observed:

```text
gcc (GCC) 15.2.0
Python 3.11.5
GNU Make 4.2.1
```

The configured cross compilers, Java, Node, Go, QEMU, assembler,
parser-generators, and GLib were not relevant and were not invoked.

## Normal builds

Commands, from the pack root:

```sh
mkdir -p environment/.validation-tmp
TMPDIR="$PWD/environment/.validation-tmp" \
  /usr/bin/timeout 30s /usr/bin/make -C starter clean all \
  CC=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc
TMPDIR="$PWD/environment/.validation-tmp" \
  /usr/bin/timeout 30s /usr/bin/make -C sealed/reference clean all \
  CC=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc
```

Both commands exited 0. Compilation used
`-std=c11 -Wall -Wextra -Wpedantic -Werror -g`; no compiler diagnostic was
emitted.

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

Each exited 0:

```text
Ran 11 tests in 0.426s — OK
Ran 16 tests in 0.587s — OK
Ran 4 tests in 0.048s — OK
```

The new sealed regressions passed for byte-exact embedded CR and LF in `-c`,
CR before an LF batch delimiter, redirections and pipelines with inherited fd
0 or fd 1 closed, parent built-in redirection with those descriptors closed,
an inherited `SIGCHLD=SIG_IGN`, and sign/whitespace rejection for `exit` and
`fg`. The public suite's background-pipeline/`jobs`/`fg` case and PTY
foreground-interrupt case both ran and passed.

## Bounded PTY failure path

Command:

```sh
PYTHONDONTWRITEBYTECODE=1 TMPDIR="$PWD/environment/.validation-tmp" \
  MSH_BIN=/bin/sh /usr/bin/timeout 10s \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  sealed/reference_tests/test_reference.py \
  InteractiveJobControlTests.test_stop_list_resume_and_interrupt_foreground_job
```

The deliberately incompatible target printed `bash-4.4$ ` instead of `msh$ `.
The test therefore exited 1 with its expected `TimeoutError` after 4.029s;
the outer timeout did not fire. Its `finally` path completed deadline-driven
`WNOHANG` cleanup without a blocking `waitpid`; bounded TERM/KILL escalation
is present if closing the PTY does not terminate the child.

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

Observed exit status: 0, with no analyzer diagnostic.

## AddressSanitizer and UndefinedBehaviorSanitizer

Build command:

```sh
TMPDIR="$PWD/environment/.validation-tmp" /usr/bin/timeout 30s \
  /usr/bin/make -C sealed/reference clean all \
  CC=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc \
  CFLAGS='-std=c11 -Wall -Wextra -Wpedantic -Werror -g -fsanitize=address,undefined -fno-omit-frame-pointer' \
  LDFLAGS='-fsanitize=address,undefined'
```

The build exited 0. The first bounded test launches omitted a loader path and
each suite exited 1 because the binary could not load `libasan.so.8`. This was
retained as an informative environment failure. The configured runtimes were
then located at:

```text
/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64/libasan.so.8.0.0
/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64/libubsan.so.1.0.0
```

The three normal-suite commands above were repeated with these additional
environment assignments:

```sh
LD_LIBRARY_PATH=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64
ASAN_OPTIONS=detect_leaks=0:halt_on_error=1
UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1
```

Final observed results against the repaired sources and tests:

```text
Ran 11 tests in 0.538s — OK
Ran 16 tests in 0.912s — OK
Ran 4 tests in 0.243s — OK
```

All three commands exited 0 with no ASan or UBSan diagnostic. Leak detection
was explicitly disabled; this is not LeakSanitizer evidence.

## Intentionally incomplete starter

Command:

```sh
PYTHONDONTWRITEBYTECODE=1 TMPDIR="$PWD/environment/.validation-tmp" \
  MSH_BIN="$PWD/starter/msh" /usr/bin/timeout 60s \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  public_tests/test_shell.py
```

Observed exit status was 1: 11 tests ran in 0.171s, with the blank-line and
syntax-no-launch cases passing and the other 9 failing. The PTY case terminated
under Ctrl-C rather than hanging. This matches the disclosed execution TODO
and is not evidence of a completed learner solution.

## Environment, metadata, structure, and credential checks

Commands:

```sh
PYTHONDONTWRITEBYTECODE=1 /usr/bin/timeout 20s /bin/sh environment/check.sh
PYTHONDONTWRITEBYTECODE=1 /usr/bin/timeout 20s \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 environment/audit.py
sha256sum PROVENANCE.json
```

All exited 0. Observed audit output after scratch cleanup:

```text
required files: 23 present
forbidden paths: 0 present
generated entries audited: 56
regular files scanned for credential patterns: 41
metadata: strict JSON; manifest object exact; source snapshot consistent
provenance document: pinned file SHA-256 verified
```

The provenance document digest was
`8aa702b8b64241bda70f3a63e3d1b9a681e7dc87f4d5930b9b4f764f584e5dad`.
The manifest remains exactly the authoritative object with status `GENERATED`,
labels `GENERATED` and `PARTIAL`, independent validation required, and
`productionized: false`.

Direct `find` checks over the canonical paths found 41 regular files, no
symlinks, and no special entries. A sorted path-only `diff` between the prior
pack and the repaired canonical roots exited 0, confirming that every prior
file path was preserved and no extra canonical file path was added. Build
binaries, objects, and `environment/.validation-tmp` were removed explicitly;
no artifact-inventory file was created.

The exact direct structure commands were:

```sh
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
  sealed starter -type f | wc -l
diff \
  <(cd PRIOR_BUILD && find AGENTS.md CONCEPTS.md DESIGN_QUESTIONS.md \
    LICENSE_BOUNDARY.md MANIFEST.yaml PROVENANCE.json README.md REQUIREMENTS.md \
    VALIDATION.md adversarial benchmarks debugging environment public_tests \
    review_exercises sealed starter -type f -print | sort) \
  <(find AGENTS.md CONCEPTS.md DESIGN_QUESTIONS.md LICENSE_BOUNDARY.md \
    MANIFEST.yaml PROVENANCE.json README.md REQUIREMENTS.md VALIDATION.md \
    adversarial benchmarks debugging environment public_tests review_exercises \
    sealed starter -type f -print | sort)
```

## Limitations

- The immutable upstream catalog/source object database and linked tutorial
  were unavailable and network access was not used. Their declared hashes,
  CC0 evidence, and the no-copy assertion were not recomputed.
- The sanitizer run disabled leak detection. No fault injection, coverage-
  guided fuzzing, benchmark acceptance test, portability matrix, or production
  readiness assessment was performed.
- The PTY checks exercised this Linux host only. Static analysis and
  builder-authored tests do not replace fresh independent review.
