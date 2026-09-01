# Validation record

Review date: 2026-08-31 (America/Chicago). Commands ran from the review workspace root. `CANDIDATE/` was treated as read-only; all reviewer build products were placed under `.review-tmp/` and removed after observation.

## Environment

```text
$ python3 --version
Python 3.6.8

$ /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
Python 3.11.5

$ gcc --version | head -n 1
gcc (GCC) 8.5.0 20210514 (Red Hat 8.5.0-22)

$ uname -srmo
Linux 4.18.0-553.el8_10.x86_64 x86_64 GNU/Linux
```

`clang`, `valgrind`, and `jq` were not found on `PATH`. The recorded smoke-report platform, GCC, and Python 3.11.5 are present in the environment.

## Inventory and immutability

```text
$ test -f CANDIDATE/include/allocator.h; echo $?
1
$ test -f CANDIDATE/scripts/build_all.py; echo $?
1
$ test -d CANDIDATE/validation-output; echo $?
1
```

Exit 1 means each required path is absent. There are 34 regular candidate files, no symlinks, and all candidate files have mode `0444`.

The aggregate hash was computed before and after validation:

```text
$ find CANDIDATE -type f -print0 | LC_ALL=C sort -z | xargs -0 sha256sum | sha256sum
fe5d46294f55626220e3cbf2f2284d8cda566b539cdfa22dd245b1d3c7ac3d7f  -
```

The value was unchanged.

## Candidate-native checks

### Documented build

```text
$ cd CANDIDATE && timeout 30s python3 scripts/build_all.py
python3: can't open file 'scripts/build_all.py': [Errno 2] No such file or directory
```

Observed exit: 2.

### Strict C syntax sweep

Each C file was checked without producing an object:

```text
$ gcc -std=c11 -Wall -Wextra -Werror -pedantic -O2 \
    -fno-omit-frame-pointer -I CANDIDATE/include -fsyntax-only FILE.c
```

Observed results: 10 of 13 translation units failed at `#include "allocator.h"`. The three self-contained units passed: `environment/sanitizer_probe.c`, `review_exercises/rounding-overflow/proposed/rounding.c`, and `review_exercises/rounding-overflow/sealed/demonstrate.c`.

Representative failure:

```text
CANDIDATE/public_tests/contract.c:1:10: fatal error: allocator.h: No such file or directory
```

### Python runner

```text
$ python3 CANDIDATE/benchmarks/run.py --output /dev/null
  File "CANDIDATE/benchmarks/run.py", line 1
    from __future__ import annotations
SyntaxError: future feature annotations is not defined
```

Observed exit: 1 with the default Python 3.6.8.

```text
$ /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3.11 \
    CANDIDATE/benchmarks/run.py --output /dev/null
FileNotFoundError: [Errno 2] No such file or directory: \
'.../CANDIDATE/validation-output/bin/reference-benchmark'
```

Observed exit: 1. Failure occurred at `subprocess.run` before output handling; no candidate file was created.

### Structured artifacts

```text
$ python3 -c 'import json, pathlib; files=["CANDIDATE/MANIFEST.yaml", \
  "CANDIDATE/PROVENANCE.json", "CANDIDATE/benchmarks/results/smoke.json"]; \
  [json.loads(pathlib.Path(f).read_text()) for f in files]; print(len(files))'
3
```

All three parse as JSON (and the manifest's JSON is valid YAML). Recomputing each stored `operations_per_second` and external-fragmentation ratio produced only rounding-level deltas: at most `0.000403` operations/second and `3.0e-10`, respectively.

## Reviewer-assisted source diagnostics

These checks do **not** repair or validate the candidate package. To examine the otherwise stranded source bodies, the reviewer created an inferred `allocator.h` only under `.review-tmp/include/`, defining the symbols and named statistics fields used by the submitted code. Its SHA-256 was `3afdcb64c1a9b13e6f3dfc5639c54ef8e5a795b4bc3ca8e0db3b4ce8f6636cee`. It was not copied into or read from `CANDIDATE/`.

The compile pattern was:

```text
$ gcc -std=c11 -Wall -Wextra -Werror -pedantic -O2 \
    -fno-omit-frame-pointer -I .review-tmp/include \
    IMPLEMENTATION.c TEST.c -o .review-tmp/bin/TEST
$ timeout 30s .review-tmp/bin/TEST
```

Observed matrix:

| Diagnostic | Reference | Best fit | Segregated bins |
|---|---:|---:|---:|
| strict compile + public contract | exit 0 | exit 0 | exit 0 |
| strict compile + withheld contract | exit 0 | exit 0 | exit 0 |
| strict compile + fixed-seed model | exit 0 | exit 0 | exit 0 |
| reviewer-authored edge/stress contract | exit 0 | exit 0 | exit 0 |
| one benchmark executable smoke run | exit 0 | exit 0 | exit 0 |

The included models reported:

```text
address-ordered-first-fit: completed=1759 allocation_failures=918 resize_failures=409
address-ordered-best-fit: completed=1821 allocation_failures=844 resize_failures=374
segregated-size-class-bins: completed=1746 allocation_failures=901 resize_failures=393
```

The reviewer-authored test used a different deterministic generator and checked alignment, bounds canaries, payload integrity, invalid/interior frees, double/stale frees, overflow rejection, coalescing, failed-resize atomicity, and invariants across 2,500 operations. It also probed declared-span overlap:

```text
reviewer contract passed architecture=address-ordered-first-fit declared-overlap-result=0
reviewer contract passed architecture=address-ordered-best-fit declared-overlap-result=0
reviewer contract passed architecture=segregated-size-class-bins declared-overlap-result=0
```

The inferred header defined `LF_OK` as 0, so each implementation accepted the overlapping declared spans.

The segregated-bin white-box integrity test exited 0. The intentional coalescing regression exited 1 for the buggy implementation and 0 for the reference. The rounding-overflow demonstration exited 0 and printed `reproduced request-size overflow: SIZE_MAX rounded down to zero`.

A source search found no calls to `malloc`, `calloc`, `realloc`, `free`, `sbrk`, or `mmap` in the allocator implementations themselves.

### Diagnostic benchmark comparison

Reviewer-built executables reproduced the stored architecture names, operation counts, allocation counts, and complete fragmentation objects exactly. Timing varied, as expected for a one-shot smoke run:

| Architecture | Stored elapsed ns | Observed elapsed ns |
|---|---:|---:|
| reference | 10,711,614 | 12,001,818 |
| best-fit | 10,479,660 | 11,521,358 |
| segregated-bins | 1,738,324 | 2,258,553 |

This is plausibility evidence only because the reviewer-supplied header and binaries are not submitted evidence.

## Unavailable or inconclusive checks

- `-fsanitize=address,undefined` compilation failed at link time: `/usr/bin/ld` could not find `libasan.so.5.0.0` or `libubsan.so.1.0.0`. Static sanitizer archives were also unavailable. No sanitizer result is claimed.
- `clang` and `valgrind` were unavailable, so there was no independent second compiler or dynamic checker.
- The cited source repository and outbound tutorial were outside the readable workspace, and network access was restricted. Copy/originality and external license assertions were not independently verified.
- No controller-owned validator, hidden evidence, transfer target, validator log, or evidence-to-label record was submitted.
- The inferred API header makes all assisted source results inconclusive for candidate-native `BUILDS`/`TESTED`; no such label is promoted.
- The model runs are bounded deterministic checks, not exhaustive testing or fuzzing. Benchmark executions were single smoke samples, not production measurements.
