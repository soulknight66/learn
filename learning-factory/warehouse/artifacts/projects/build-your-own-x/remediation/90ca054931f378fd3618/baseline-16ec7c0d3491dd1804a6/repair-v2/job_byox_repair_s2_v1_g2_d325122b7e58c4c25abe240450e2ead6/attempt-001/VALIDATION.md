# Local repair validation evidence

## Status boundary

Repair generation 2 was exercised locally on 2026-09-03 from the repository
root.  `MANIFEST.yaml` remains `GENERATED` with only `GENERATED` and `PARTIAL`
labels, and independent validation remains `REQUIRED`.  These observations are
builder evidence, not factory validation labels or a production-readiness
claim.

The complete builder archive intentionally contains `sealed/`.  No student
workspace was created.  Publication still requires an orchestrator-controlled
learner projection that excludes sealed reference, test, review, and answer
material.

## Repairs exercised

- All three Makefiles now pass GCC an explicit `-B` path for the configured GNU
  Binutils directory.  `CC=...` and `BINUTILS_DIR=...` remain overrides.
- `environment/check.sh` now verifies GCC's resolved linker and performs an
  actual compile, link, and execution smoke test in self-cleaning scratch.
- `verify_pack.py` now rejects names outside an explicit top-level allowlist,
  traverses every allowlisted entry without following symlinked directories,
  rejects all entry types except regular files and directories, and scans every
  regular file for credential patterns.
- Three verifier regression tests cover a clean allowlisted archive plus an
  unexpected top-level regular file and symlink.

## Tools actually invoked

```sh
/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc --version | sed -n '1p'
/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/ld --version | sed -n '1p'
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
/usr/bin/make --version | sed -n '1p'
```

Observed, respectively:

```text
gcc (GCC) 15.2.0
GNU ld (GNU Binutils) 2.43
Python 3.11.5
GNU Make 4.2.1
```

GCC, GNU ld, and Python were invoked through their exact configured absolute
paths.  The other configured toolchain roots were not needed.

The explicit resolution probe was:

```sh
/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc \
  -B/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/ \
  -print-prog-name=ld
```

It exited 0 and printed exactly:

```text
/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/ld
```

## Clean-environment link reproduction

The first staging attempt used:

```sh
/usr/bin/timeout 30s /usr/bin/env -i PATH=/usr/bin:/bin \
  ./environment/check.sh
```

It exited 126 with `Permission denied` before running the script because the
copy operation had normalized its executable bit to mode 0644.  The three
pre-existing executable scripts were restored to mode 0755, and the same
command was rerun.  The rerun exited 0 and printed:

```text
gcc (GCC) 15.2.0
GNU ld (GNU Binutils) 2.43
Python 3.11.5
GCC linker: /arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/ld
C17 compile/link/execute smoke check: PASS
```

The documented builds were then run without adding GCC or ld to `PATH`:

```sh
/usr/bin/timeout 60s /usr/bin/env -i PATH=/usr/bin:/bin \
  /usr/bin/make -C starter clean all
/usr/bin/timeout 60s /usr/bin/env -i PATH=/usr/bin:/bin \
  /usr/bin/make -C sealed/reference clean all
/usr/bin/timeout 60s /usr/bin/env -i PATH=/usr/bin:/bin \
  /usr/bin/make -C sealed/reference_tests clean all
```

All three exited 0.  Their command logs showed the exact configured GCC plus
`-B/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/` for every compilation and
link.  Both interpreters used `-std=c17 -O2 -g -Wall -Wextra -Werror
-pedantic`; the direct VM test used the same strict flags.

## Behavioral checks

All guest execution and test harness commands were bounded with
`/usr/bin/timeout`.

```sh
/usr/bin/timeout 30s /usr/bin/env -i PATH=/usr/bin:/bin \
  MICROC_BIN="$PWD/starter/build/emberc" \
  PYTHON_BIN=/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  ./public_tests/run.sh --lexer-only
/usr/bin/timeout 30s /usr/bin/env -i PATH=/usr/bin:/bin \
  MICROC_BIN="$PWD/sealed/reference/build/emberc-ref" \
  PYTHON_BIN=/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  ./public_tests/run.sh
/usr/bin/timeout 90s /usr/bin/env -i PATH=/usr/bin:/bin \
  PYTHON_BIN=/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  ./sealed/reference_tests/run.sh
```

All exited 0.  The starter run discovered 10 tests, passed its 2 lexer tests,
and intentionally skipped 8 later milestones.  The reference passed all 10
public tests.  The sealed runner reported 26 passing direct VM checks followed
by 21 passing Python methods: 18 interpreter behavior methods and 3 archive
verifier methods.

```sh
/usr/bin/timeout 10s /usr/bin/env -i PATH=/usr/bin:/bin \
  ./sealed/reference/build/emberc-ref \
  --tower sealed/reference/self/tower.ec
```

It exited 0 with stdout exactly `4242\n` and empty stderr.

The direct failure probes were:

```sh
/usr/bin/timeout 10s ./sealed/reference/build/emberc-ref \
  public_tests/cases/bad_overflow.ec
/usr/bin/timeout 10s ./sealed/reference/build/emberc-ref \
  --max-steps 0 public_tests/cases/factorial.ec
```

Each exited 1 and printed one stderr line, respectively:

```text
public_tests/cases/bad_overflow.ec:3:19: runtime error: signed arithmetic overflow
public_tests/cases/factorial.ec:2:13: runtime error: instruction budget exceeded
```

## Archive-verifier regression checks

The focused bounded command was:

```sh
PYTHONDONTWRITEBYTECODE=1 /usr/bin/timeout 30s \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  -m unittest -v sealed.reference_tests.test_verify_pack
```

It exited 0 with 3 passing tests.  The acceptance case copied exactly the
allowlisted pack entries to uniquely named local scratch and exercised required
paths, forbidden paths, exact manifest/provenance checks, whole-tree entry
types, and whole-archive credential scanning.  The two rejection cases added
an unexpected top-level regular file or symlink and observed
`VerificationError` in each case.  These fixtures existed only under
`sealed/reference_tests/build/` and were removed by the harness.

## Final artifact checks

After testing, the three Makefile clean targets were run and their now-empty
`build/` directories were removed explicitly.  The final verifier regression
command above was repeated after this document was updated and again passed
all 3 tests; its scratch directory was then removed.

```sh
/usr/bin/make -C starter clean
/usr/bin/make -C sealed/reference clean
/usr/bin/make -C sealed/reference_tests clean
/usr/bin/rmdir starter/build sealed/reference/build sealed/reference_tests/build
PYTHONDONTWRITEBYTECODE=1 /usr/bin/timeout 30s \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  -m unittest -v sealed.reference_tests.test_verify_pack
/usr/bin/rmdir sealed/reference_tests/build
```

The clean and removal commands all exited 0.

```sh
/usr/bin/sha256sum PROVENANCE.json MANIFEST.yaml
```

Observed:

```text
3dc7fc913794fd6c9205f6d0588d0a9c4370fb639ae6991b97b4f28aaff9d57a  PROVENANCE.json
65467d58c5d0aafa3bcc9160d5ebb6aa7a78416e57137d07672277ff4dea4586  MANIFEST.yaml
```

A final explicit-path inventory found every authoritative required file and no
forbidden path, symlink, special file, `build/`, `__pycache__/`, `*.pyc`,
`*.o`, top-level `LICENSE`, or artifact-inventory root.  The allowlisted clean
archive verifier found no credential-pattern match.

```sh
/usr/bin/find starter public_tests environment sealed adversarial debugging \
  review_exercises benchmarks ! -type f ! -type d -print
/usr/bin/find starter public_tests environment sealed adversarial debugging \
  review_exercises benchmarks -type d \
  \( -name build -o -name __pycache__ \) -print
/usr/bin/find starter public_tests environment sealed adversarial debugging \
  review_exercises benchmarks -type f \
  \( -name '*.pyc' -o -name '*.o' \) -print
test ! -e LICENSE -a ! -e ARTIFACT_INVENTORY.sha256
```

All four checks exited 0 and the three `find` commands printed nothing.

No network access, sanitizer, leak detector, fuzzer, benchmark, learner
transfer, cross-platform test, or production review was run in generation 2.
Prior-generation observations are not reused as evidence.  No corresponding
validation label is claimed.
