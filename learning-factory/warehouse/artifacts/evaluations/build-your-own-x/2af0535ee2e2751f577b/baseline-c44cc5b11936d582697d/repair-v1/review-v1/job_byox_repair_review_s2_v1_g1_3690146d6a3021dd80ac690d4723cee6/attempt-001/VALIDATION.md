# Independent validation record

Date: 2026-09-02 (America/Chicago). Commands ran from the workspace root unless noted. `CANDIDATE/` was treated as immutable; builds and runtime scratch were confined to `review-scratch.iYrGLi/`, a writable copy that was removed after validation. No network access was attempted.

Scratch setup was:

```sh
mktemp -d ./review-scratch.XXXXXX
cp -R --no-preserve=mode CANDIDATE/. review-scratch.iYrGLi/
```

`mktemp` returned `./review-scratch.iYrGLi`. All build and test commands below ran from that directory unless their paths begin with `CANDIDATE/`.

## Toolchain observations

Exact commands:

```sh
/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc --version
/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/ld --version
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3.11 --version
/usr/bin/make --version
```

All exited 0. First lines were `gcc (GCC) 15.2.0`, `GNU ld (GNU Binutils) 2.43`, `Python 3.11.5`, and `GNU Make 4.2.1`.

The submitted environment probe was independently invoked from the scratch copy:

```sh
TMPDIR="$PWD/sealed/reference_tests/build/tmp" /usr/bin/timeout 30s \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3.11 \
  environment/check_environment.py \
  --cc /arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc \
  --cc-option=-B/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/ \
  --make /usr/bin/make
```

It exited 0 and reported `C11 int64_t compile/run probe: PASS` with those exact compiler, Python, and Make paths.

`rg` and `git` were unavailable in the review shell. Inventory and integrity checks therefore used `find`, `diff`, `cmp`, and `sha256sum`.

## Integrity and archive boundary

Read-only inventory found 49 regular candidate files, no symlinks, and no sockets, devices, or FIFOs. The files were mode 0444 and candidate directories mode 0555/2555. An initial SHA-256 was recorded for each file.

The candidate audit was replayed as a supporting check, not accepted as proof on its own:

```sh
/usr/bin/timeout 30s \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3.11 \
  environment/audit_pack.py
```

Observed exit 0:

```text
required_files=23 missing=0
forbidden_paths_present=0
unexpected_top_level_entries=0
generated_special_files_or_symlinks=0
credential_pattern_matches=0
MANIFEST.yaml_sha256=d790bd7487c566f570a0207bb94f3cf1d2af4815acb04f3d14153bde62600c8e
PROVENANCE.json_sha256=db3da454c4b0e7f852e59a264c6e2296b2dd561c35ca2b5bf5f8f9b04d127169
pack audit: PASS
```

Static inspection separately covered every source, test, script, document, Makefile, allowlist, and credential pattern. The declared learner inputs contain no reference implementation or answer key; solution-bearing files and maintainer tests are under sealed paths. Actual publication-layer view enforcement was not available to this reviewer.

The final reviewed checksum stream was computed with:

```sh
find CANDIDATE -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum
```

It produced `856fe4df7e21164c32d17b7bae240e7668c3b699f40f5b47a9c5a65135e5e938`. A content comparison between `CANDIDATE/` and the scratch source, excluding scratch-only build products and the reviewer harness, exited 0 with no differences.

## Strict builds

The following form was run for `starter`, `sealed/reference`, and `sealed/reference_tests` from the scratch root, with a 30-second outer timeout:

```sh
/usr/bin/timeout 30s /usr/bin/make -C DIRECTORY clean all \
  CC=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc \
  CFLAGS='-std=c11 -Wall -Wextra -Wpedantic -Werror -O2 -B/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/'
```

All three exited 0 with no compiler warning or error.

The historical no-`-B` failure in the submitted record was also replayed:

```sh
/usr/bin/timeout 30s /usr/bin/make -C sealed/reference clean all \
  BUILD_DIR=build-no-b \
  CC=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc \
  CFLAGS='-std=c11 -Wall -Wextra -Wpedantic -Werror -O2'
```

It exited 0 here rather than 2. `command -v ld` resolved `/usr/bin/ld`, whose version is GNU ld 2.30; `gcc -print-prog-name=ld` returned `ld`. This environment-dependent discrepancy does not affect the pinned 2.43 builds, but the original failure is not replayable without its PATH context.

## Submitted test suites

Exact reference commands:

```sh
TMPDIR="$PWD/sealed/reference_tests/build/tmp" /usr/bin/timeout 60s \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3.11 \
  public_tests/run_tests.py --binary sealed/reference/build/sprig

TMPDIR="$PWD/sealed/reference_tests/build/tmp" /usr/bin/timeout 90s \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3.11 \
  sealed/reference_tests/run_tests.py --binary sealed/reference/build/sprig

/usr/bin/timeout 30s /usr/bin/make -C sealed/reference_tests test \
  CC=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc \
  CFLAGS='-std=c11 -Wall -Wextra -Wpedantic -Werror -O2 -B/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/'
```

Observed results were exit 0 with 11/11 public tests, exit 0 with 22/22 sealed black-box tests, and exit 0 with `12 VM safety tests passed`.

The public runner was also pointed at `starter/build/sprig`. It exited 1 as intended: the empty program and both token-mode cases passed, while eight cases stopped at the documented compiler stub.

## Independent differential and boundary checks

A reviewer-authored, external Python harness used subprocess argument arrays, three-second per-child timeouts, new process sessions, captured streams, and a fixed random seed `0x5A17`. Its SHA-256 was `7c9acb7136ea28f7dda9c275906fe464f6bb678fbdb4c81aba1a94cc268d46b5`. It checked:

- 576 combinations of 12 boundary values and all four arithmetic operators against Python big-integer results, including C truncating division;
- 160 recursively generated deterministic expressions;
- exact accepted/rejected stack, mixed nesting, instruction, binding, identifier, and 1 MiB source boundaries;
- token atomicity, disassembly coordinates, malformed syntax, NUL rejection, usage status, and all three stdout modes against `/dev/full`.

Command:

```sh
/usr/bin/timeout 90s \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3.11 \
  independent_checks.py --binary sealed/reference/build/sprig \
  --tmpdir sealed/reference_tests/build/tmp
```

The first run exited 1 only because the reviewer harness expected EOF at column 18 for a test whose actual and correct coordinate was column 17. That external expectation was corrected. The rerun exited 0:

```text
independent checks: PASS
arithmetic matrix cases=576
deterministic generated expressions=160
total compiler invocations=757
```

These deterministic checks are not exhaustive fuzzing and do not establish `FUZZED`.

## UndefinedBehaviorSanitizer

The reference and direct VM target were rebuilt with these commands (the same `CFLAGS` value was used for both):

```sh
/usr/bin/timeout 30s /usr/bin/make -C sealed/reference clean all \
  BUILD_DIR=build-ubsan \
  CC=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc \
  CFLAGS='-std=c11 -Wall -Wextra -Wpedantic -Werror -O1 -g -fsanitize=undefined -fno-sanitize-recover=undefined -B/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/'

/usr/bin/timeout 30s /usr/bin/make -C sealed/reference_tests clean all \
  BUILD_DIR=build-ubsan \
  CC=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc \
  CFLAGS='-std=c11 -Wall -Wextra -Wpedantic -Werror -O1 -g -fsanitize=undefined -fno-sanitize-recover=undefined -B/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/'
```

Both builds exited 0. In the first test attempts, every instrumented child exited 127 before candidate code ran, causing the two harnesses to exit 1, because `libubsan.so.1` was not on the default loader path. The supplied runtime was found at `/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64/libubsan.so.1`. With this explicit environment:

```sh
LD_LIBRARY_PATH=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64 \
TMPDIR="$PWD/sealed/reference_tests/build/tmp" \
  /usr/bin/timeout 90s \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3.11 \
  sealed/reference_tests/run_tests.py --binary sealed/reference/build-ubsan/sprig

LD_LIBRARY_PATH=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64 \
  /usr/bin/timeout 120s \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3.11 \
  independent_checks.py --binary sealed/reference/build-ubsan/sprig \
  --tmpdir sealed/reference_tests/build/tmp

LD_LIBRARY_PATH=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64 \
  /usr/bin/timeout 30s /usr/bin/make -C sealed/reference_tests test \
  BUILD_DIR=build-ubsan \
  CC=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc \
  CFLAGS='-std=c11 -Wall -Wextra -Wpedantic -Werror -O1 -g -fsanitize=undefined -fno-sanitize-recover=undefined -B/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/'
```

The outcomes were 22/22 sealed tests, all 757 independent invocations, and all 12 direct VM tests passing with no sanitizer diagnostic. This is bounded sanitizer evidence, not a security certification.

## Adversarial generator, build reproducibility, and benchmark smoke

Two generation commands produced ten cases each, and the comparison had no output:

```sh
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3.11 \
  adversarial/generate_cases.py sealed/reference_tests/build/reviewer-cases-a
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3.11 \
  adversarial/generate_cases.py sealed/reference_tests/build/reviewer-cases-b
/usr/bin/diff -qr sealed/reference_tests/build/reviewer-cases-a \
  sealed/reference_tests/build/reviewer-cases-b
```

All exited 0. Running the first corpus produced: `max_variables` 0, `too_many_variables` 65, `instruction_limit` 65, `right_heavy_stack` 70, `nesting_limit` 65, `add_overflow` 70, `computed_minimum` 0, `long_identifier` 65, `embedded_nul` 65, and `comment_at_eof` 0. Successful outputs were respectively `63`, `-9223372036854775808`, and `1`.

Two additional optimized builds used `BUILD_DIR=build-repro-a` and `BUILD_DIR=build-repro-b` with the strict flags above. `cmp` exited 0, and those binaries plus the primary build all had SHA-256:

```text
494ba8d100328e7dc50fe2f17edd8918f96d56186bdbd3355c7a98742f331583
```

Finally:

```sh
/usr/bin/timeout 30s \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3.11 \
  benchmarks/run_benchmark.py --binary sealed/reference/build/sprig \
  --iterations 3 --warmup 1
```

It exited 0, validated the 190-line output shape, and observed three shared-host samples with median `0.0024395626969635487` seconds. This is only a harness smoke check; it does not establish `BENCHMARKED` or a portable performance result.

## Limitations and label boundary

The immutable source baseline and linked upstream repository were unavailable, and network access was not used. The recorded source commit, catalog license evidence, and no-copy claim could therefore only be checked for internal consistency. Cross-platform transfer, exhaustive fuzzing, production readiness, and security certification were not performed. The candidate appropriately claims none of them.

This PASS is advisory. It does not edit `CANDIDATE/MANIFEST.yaml`, grant `REVIEWED`, or replace the orchestrator's independent acceptance validator.

The scoped scratch copy was then removed with:

```sh
rm -r -- review-scratch.iYrGLi
```

It exited 0. The scratch artifacts were reviewer-generated and are not recoverable; `CANDIDATE/` and the three review deliverables remain.
