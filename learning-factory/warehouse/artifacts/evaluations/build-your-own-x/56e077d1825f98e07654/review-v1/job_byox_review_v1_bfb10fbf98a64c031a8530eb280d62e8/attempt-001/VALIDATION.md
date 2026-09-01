# Independent validation record

Date: 2026-08-31 (America/Chicago)

Builds and test executions were bounded with `timeout`. `CANDIDATE/` was inspected read-only. Builds
ran from a reviewer-owned copy at `.review-scratch/`; scratch products were removed after recording
results. The shell repeatedly printed an infrastructure warning that numeric UID/GID names could not
be resolved. It did not alter command outcomes.

## Candidate integrity and metadata

The aggregate hashes were taken before and after all review activity:

```text
$ find CANDIDATE -type f -exec sha256sum {} \; | LC_ALL=C sort | sha256sum
992cecf74439a2ed8c158b464afc54cc129211601c64a60d31bee7eab9171570  -

$ find CANDIDATE -type f | LC_ALL=C sort | sha256sum
8dff7c7ffb3c9c950af14902eedef931f3b72845abb0e0a6963cd58462e07b7a  -
```

Both post-review values were identical. The package contains 47 regular files and 23 directories;
`find CANDIDATE ! -type d ! -type f -print` produced no output.

```text
$ python3 -m json.tool CANDIDATE/PROVENANCE.json >/dev/null && \
  python3 -m json.tool CANDIDATE/MANIFEST.yaml >/dev/null
exit 0

$ python3 -c 'import json; m=json.load(open("CANDIDATE/MANIFEST.yaml")); \
  p=json.load(open("CANDIDATE/PROVENANCE.json")); \
  checks={"project_id":m["project_id"]==p["project"]["project_id"], \
  "source_commit":m["source_commit"]==p["source"]["commit_hash"]== \
  p["project"]["metadata"]["provenance"]["source_commit"], \
  "source_id":m["source_id"]==p["source"]["source_id"]==p["project"]["source_id"], \
  "snapshot_digest":m["provenance_sha256"]==p["snapshot_sha256"], \
  "labels":m["status"]=="GENERATED" and \
  m["validation_labels"]==["GENERATED","PARTIAL"] and \
  m["productionized"] is False}; print(checks); \
  raise SystemExit(0 if all(checks.values()) else 1)'
{'project_id': True, 'source_commit': True, 'source_id': True,
 'snapshot_digest': True, 'labels': True}
exit 0
```

The label check required `status == GENERATED`, labels exactly `GENERATED, PARTIAL`, and
`productionized == false`. A bounded common credential-signature scan returned no matches; that is
not a comprehensive secret audit.

## Host and optional-tool inventory

```text
$ cc --version | head -n 1
cc (GCC) 8.5.0 20210514 (Red Hat 8.5.0-22)

$ make --version | head -n 1
GNU Make 4.2.1

$ timeout 20s sh .review-scratch/environment/check.sh
cc: available
make: available
arm-none-eabi-gcc: unavailable
qemu-system-arm: unavailable
exit 0
```

No `clang`, `valgrind`, `cppcheck`, or other listed static-analysis/fuzz tool was found. The initial
`cp -a` retained the factory's immutable directory modes, so the first scratch build stopped at
`mkdir build: Permission denied`. After `chmod -R u+w .review-scratch` (scratch only), builds ran as
follows.

## Builds and submitted tests

```text
$ timeout 30s make -C .review-scratch/starter clean all
cc -Iinclude -std=c11 -O2 -g -Wall -Wextra -Werror -pedantic \
  -c src/kernel.c -o build/kernel.o
ar rcs libtinyarm.a build/kernel.o
exit 0

$ timeout 30s make -C .review-scratch/sealed/reference clean all
cc -I../../starter/include -std=c11 -O2 -g -Wall -Wextra -Werror -pedantic \
  -c src/kernel.c -o build/kernel.o
ar rcs libtinyarm-reference.a build/kernel.o
exit 0

$ timeout 30s make -C .review-scratch/public_tests clean test \
  IMPL_DIR=../sealed/reference
public tests: 3 groups passed
exit 0

$ timeout 30s make -C .review-scratch/sealed/reference_tests clean test
sealed reference tests: 6 groups passed
exit 0
```

The learner starter was also checked, with the expected nonzero result:

```text
$ timeout 30s make -C .review-scratch/public_tests clean test IMPL_DIR=../starter
FAIL test_public.c:49: mk_init(&kernel, 1u) == MK_OK
FAIL test_public.c:69: mk_init(&kernel, 2u) == MK_OK
FAIL test_public.c:88: mk_init(&kernel, 1u) == MK_OK
3 public test group(s) failed
make: *** [Makefile:20: test] Error 1
exit 2
```

These results independently reproduce the ordinary builder-local transcript, but do not by
themselves establish any completion label.

## Reviewer-authored contract checks

A temporary strict-C11 harness added cases not present in the submitted public suite:

- invalid initialization preserving all bytes, blocked-only wake timing, and terminal PID rollover;
- VM `UINTPTR_MAX`/`SIZE_MAX` ranges, exact-end zero-length access, cross-page unmapped/read-only
  failure atomicity, and zeroed frame reuse;
- maximum/excessive paths, lowest block selection, unchanged state on oversized replacement,
  `SIZE_MAX` read offset, unchanged output parameters on errors, and filesystem-storage alias input.

```text
$ timeout 30s cc -I.review-scratch/starter/include -std=c11 -O2 -g \
  -Wall -Wextra -Werror -pedantic .review_contract_tests.c \
  .review-scratch/sealed/reference/src/kernel.c -o .review_contract_tests && \
  timeout 20s ./.review_contract_tests
independent contract tests: 3 groups passed
exit 0
```

A focused fourth case exercised the candidate's stated reentrant callback interface. Its PID 1
callback performed this sequence:

```c
mk_exit_current(kernel, 19);
mk_reap(kernel, pid_1, NULL);
pid_2 = mk_spawn(kernel, replacement_that_continues, NULL);
mk_tick(kernel);                 /* PID 2 runs once and remains RUNNING at quantum 2. */
return MK_STEP_EXIT;             /* This result belongs to PID 1. */
```

The same compile command with the focused harness produced:

```text
$ timeout 30s cc -I.review-scratch/starter/include -std=c11 -O2 -g \
  -Wall -Wextra -Werror -pedantic .review_repro.c \
  .review-scratch/sealed/reference/src/kernel.c -o .review_repro && \
  timeout 20s ./.review_repro
pid=2 state=4 exit=0 steps=1 calls=1 now=2
exit 1
```

State 4 is `MK_TASK_ZOMBIE`. Inspection located the cause at
`sealed/reference/src/kernel.c:265-285`: the captured PID guards the step increment, but not callback
result application.

## Repeated-build check

```text
$ timeout 30s make -C .review-scratch/sealed/reference clean all >/dev/null && \
  sha256sum .review-scratch/sealed/reference/libtinyarm-reference.a
54743dcbe4deaecce42dcb353691f23cba2f8964bfd2dd29c61e5205b8bf597c  .review-scratch/sealed/reference/libtinyarm-reference.a

$ timeout 30s make -C .review-scratch/sealed/reference clean all >/dev/null && \
  sha256sum .review-scratch/sealed/reference/libtinyarm-reference.a
54743dcbe4deaecce42dcb353691f23cba2f8964bfd2dd29c61e5205b8bf597c  .review-scratch/sealed/reference/libtinyarm-reference.a
```

This shows same-workspace repeatability for this archive only, not a cross-toolchain reproducible
build guarantee.

## Blocked and inconclusive checks

```text
$ timeout 30s make -C .review-scratch/sealed/reference_tests clean test SANITIZE=1
/usr/bin/ld: cannot find /usr/lib64/libasan.so.5.0.0
/usr/bin/ld: cannot find /usr/lib64/libubsan.so.1.0.0
collect2: error: ld returned 1 exit status
exit 2

$ timeout 30s make -C .review-scratch/sealed/reference/arm clean all
arm-none-eabi-gcc ... -o kernel.elf
make: arm-none-eabi-gcc: Command not found
make: *** [Makefile:13: kernel.elf] Error 127
exit 2
```

QEMU was not attempted without the compiler, emulator, or ARM binary. The upstream repository and
immutable source snapshot were not available inside this review workspace, so provenance fields were
checked only for internal consistency. The evaluator bundle exposes all 20 `sealed/` files to the
reviewer but contains no independently executable learner-export step; transfer isolation therefore
remains unverified. No sanitizer, ARM boot, fuzz, benchmark, transfer, security, or production claim
is made.
