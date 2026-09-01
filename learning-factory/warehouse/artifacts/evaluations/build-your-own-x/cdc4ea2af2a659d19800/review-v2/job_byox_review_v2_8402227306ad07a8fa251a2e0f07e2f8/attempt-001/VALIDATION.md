# Independent validation log

Date: 2026-08-31. Commands ran from the review workspace root. `CANDIDATE/` was read-only and
was not edited. Program executions were bounded to 20 seconds.

## Available environment

```text
$ cc --version | sed -n '1,2p'
cc (GCC) 8.5.0 20210514 (Red Hat 8.5.0-22)

$ python3 --version
Python 3.6.8

$ /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
Python 3.11.5
```

`clang`, `valgrind`, `git`, and `rg` were not available.

## Submitted-tree build and replay

Documented build entry point:

```text
$ python3 CANDIDATE/scripts/build_all.py
python3: can't open file 'CANDIDATE/scripts/build_all.py': [Errno 2] No such file or directory
exit: 2
```

Strict native compile:

```text
$ cc -std=c11 -Wall -Wextra -Werror -pedantic -O2 -fno-omit-frame-pointer \
    -I CANDIDATE/include CANDIDATE/sealed/reference/allocator.c \
    CANDIDATE/public_tests/contract.c -o /dev/null
CANDIDATE/sealed/reference/allocator.c:1:14: fatal error: allocator.h: No such file or directory
CANDIDATE/public_tests/contract.c:1:10: fatal error: allocator.h: No such file or directory
exit: 1
```

File checks confirmed that `CANDIDATE/include/allocator.h` and
`CANDIDATE/scripts/build_all.py` do not exist.

Benchmark runner with the documented `python3`:

```text
$ python3 CANDIDATE/benchmarks/run.py --output ../.review_tmp/replayed-smoke.json
File "CANDIDATE/benchmarks/run.py", line 1
  from __future__ import annotations
SyntaxError: future feature annotations is not defined
exit: 1
```

Benchmark runner with the available Python 3.11 toolchain:

```text
$ /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
    CANDIDATE/benchmarks/run.py --output \
    /projects/se/pj34000401_refsys/users/yuali01/learn/learning-factory/warehouse/workspaces/\
job_byox_review_v2_8402227306ad07a8fa251a2e0f07e2f8/attempt-001/.review_tmp/replayed-smoke.json
FileNotFoundError: [Errno 2] No such file or directory: \
  'CANDIDATE/validation-output/bin/reference-benchmark'
exit: 1
```

Failure occurred before any output write. The other two recorded binaries and
`CANDIDATE/validation-output/toolchain.json` are also absent.

## Metadata and submitted benchmark evidence

```text
$ python3 -m json.tool CANDIDATE/MANIFEST.yaml >/dev/null
exit: 0
$ python3 -m json.tool CANDIDATE/PROVENANCE.json >/dev/null
exit: 0
$ python3 -m json.tool CANDIDATE/benchmarks/results/smoke.json >/dev/null
exit: 0
```

Independent arithmetic checks recomputed `timed_operations * 1e9 / elapsed_ns` and
`1 - largest_free_block / free_bytes` for each architecture. All stored values matched within
their printed precision. Each command named in the result points to a missing executable. Its
strict flags contain this non-portable path:

```text
/projects/se/pj34000401_refsys/users/yuali01/learn/learning-factory/warehouse/workspaces/
job_project_allocator_vertical_v1/attempt-002/include
```

No controller log, exit-code record, validation label, or referenced toolchain JSON accompanies
the result.

## Auxiliary compilation with inferred declarations

Because the required header is absent, the reviewer created a temporary header outside
`CANDIDATE/` containing only declarations inferable from the implementations and tests: six
distinct status constants, `lf_allocator_stats` fields used by the sources, and the eight public
function prototypes. This header and all binaries were scratch diagnostics, not repairs or
candidate build evidence.

The following strict pattern was applied to each combination:

```text
$ cc -std=c11 -Wall -Wextra -Werror -pedantic -O2 -fno-omit-frame-pointer \
    -I .review_tmp IMPLEMENTATION.c TEST.c -o .review_tmp/bin/TEST
```

All 12 combinations of the three implementations with the public contract, submitted sealed
contract, deterministic model, and benchmark compiled with exit 0.

Bounded submitted-test results:

| Architecture | Public | Submitted sealed contract | Deterministic model |
|---|---:|---:|---:|
| first-fit | exit 0 | exit 0 | exit 0; completed 1759, allocation failures 918, resize failures 409 |
| best-fit | exit 0 | exit 0 | exit 0; completed 1821, allocation failures 844, resize failures 374 |
| segregated bins | exit 0 | exit 0 | exit 0; completed 1746, allocation failures 901, resize failures 393 |

Each model reported seed `0x20260830` and 4000 iterations.

Direct benchmark diagnostics all exited 0:

| Architecture | Current elapsed ns | Current ops/s | Stored elapsed ns | Deterministic layout match |
|---|---:|---:|---:|---|
| first-fit | 14,874,199 | 5,378,440.883 | 10,711,614 | yes |
| best-fit | 15,326,554 | 5,219,699.092 | 10,479,660 | yes |
| segregated bins | 3,002,539 | 26,644,116.862 | 1,738,324 | yes |

“Layout match” means exact equality for block, live/free byte, free-block, largest-free-block,
success, failure, and fragmentation fields. Timing differences are expected and are not used to
authenticate the historical result.

## Independent contract check

The reviewer harness exercised ordinary allocation, alignment, range disjointness, foreign and
interior pointers, overflow failure atomicity, double-free semantics, resize-to-zero, stats, and
final coalescing. Those checks passed. One independent case failed on every architecture:

```c
/* arena begins beyond sizeof(state), but inside the larger declared state_bytes span */
lf_init(state_storage, declared_state_bytes, arena_inside_declared_state_span, 1024U)
```

The published contract requires `LF_ERR_ARGUMENT`. Observed results:

| Architecture | Observed API result | Process result |
|---|---|---:|
| first-fit | `LF_OK` | exit 1 |
| best-fit | `LF_OK` | exit 1 |
| segregated bins | `LF_OK` | exit 1 |

Representative output:

```text
reviewer contract: overlap in the tail of the declared state span was accepted
reviewer contract failed for address-ordered-first-fit: 1 finding(s)
```

Source inspection explains the common failure: the three implementations compute
`state_end = state_raw + sizeof(state)` while using `state_bytes` only for the minimum-size
check.

## Exercise and integrity diagnostics

Compiled with the same temporary-header limitation:

```text
$ timeout 20s .review_tmp/bin/segregated-integrity
segregated bins reject missing, inconsistent, duplicate, and extraneous nodes
exit: 0

$ timeout 20s .review_tmp/bin/debug-reference
adjacent coalescing retained the exact physical arena span
exit: 0

$ timeout 20s .review_tmp/bin/debug-buggy
detected allocator metadata corruption after adjacent coalescing
exit: 1 (expected reproduction)

$ timeout 20s .review_tmp/bin/rounding-demo
reproduced request-size overflow: SIZE_MAX rounded down to zero
exit: 0
```

Static token-aware scans found no call to `malloc`, `calloc`, `realloc`, `free`, `sbrk`, or
`mmap` in the first-fit, best-fit, or segregated-bin allocator implementation.

## Sanitizer probe

```text
$ cc -std=c11 -Wall -Wextra -Werror -pedantic -O1 -g -fno-omit-frame-pointer \
    -fsanitize=address,undefined CANDIDATE/environment/sanitizer_probe.c \
    -o .review_tmp/bin/sanitizer-probe
/usr/bin/ld: cannot find /usr/lib64/libasan.so.5.0.0
/usr/bin/ld: cannot find /usr/lib64/libubsan.so.1.0.0
collect2: error: ld returned 1 exit status
exit: 1
```

The runtime gate therefore did not pass, and no sanitized test result is claimed.

## Disclosure, provenance, and licensing inspection

- Inventory found 34 files total and 12 reference/answer/test files under top-level or nested
  sealed paths.
- No learner-view allowlist, reveal tool, or packaging/isolation test was found.
- No `LICENSE`, `NOTICE`, `COPYING`, or SPDX identifier was found for the generated pack.
- Provenance records the catalog source, commit, CC0 catalog license, linked tutorial as
  `NOASSERTION`, generated/inferred/measured categories, and a no-copy assertion.
- Network was restricted and the upstream checkout was outside the review workspace, so those
  historical assertions remain unverified limitations.
