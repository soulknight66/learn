# Independent validation record

Date: 2026-08-31 (America/Chicago)

This record reports reviewer-observed results. It does not edit `CANDIDATE/MANIFEST.yaml` or assign
`BUILDS`, `TESTED`, `FUZZED`, `BENCHMARKED`, `REVIEWED`, `TRANSFER_VERIFIED`, or `PRODUCTIONIZED`.

## Candidate immutability and inventory

The submitted tree was read-only (`0444` regular files and `2555` directories). All build products
were created in `REVIEW_SCRATCH`, a copy outside `CANDIDATE`:

```sh
find CANDIDATE -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum
find CANDIDATE -type f | wc -l
find CANDIDATE -mindepth 1 ! -type d ! -type f -print
mkdir REVIEW_SCRATCH
cp -a CANDIDATE/. REVIEW_SCRATCH/.
chmod -R u+w REVIEW_SCRATCH
```

Observed before and after all checks:

```text
3efa1ccb162d8a90b1f3f3d3aab4304cffa748c07e72eb2813ab8e6e00d22dda  -
42
```

The special-entry command printed nothing. The first scratch build attempt, before `chmod`, exited
2 because `cp -a` preserved the candidate's read-only directory modes; only the scratch copy was
made writable, and the commands below were then rerun. After results were recorded, the validated
scratch directory was removed with `find REVIEW_SCRATCH -depth -delete`; the command exited `0`, and
`test ! -e REVIEW_SCRATCH` passed.

## Tool availability

```sh
for tool in python3 cc gcc make ar ld nm objcopy clang valgrind cppcheck \
  clang-tidy scan-build splint qemu-system-i386 qemu-system-x86_64 nasm; do
    path=$(command -v "$tool" 2>/dev/null || true)
    if [ -n "$path" ]; then
        printf '%s=%s\n' "$tool" "$path"
    else
        printf '%s=UNAVAILABLE\n' "$tool"
    fi
done
python3 --version
cc --version | sed -n '1p'
make --version | sed -n '1p'
```

Observed available tools were `/usr/bin/python3`, `cc`, `gcc`, `make`, `ar`, `ld`, `nm`, and
`objcopy`. Versions were Python 3.6.8, GCC 8.5.0, and GNU Make 4.2.1. Clang, Valgrind, cppcheck,
clang-tidy, scan-build, splint, QEMU, and NASM were unavailable.

## Supplied build and test paths

```sh
timeout 30s make -C REVIEW_SCRATCH/starter clean build
timeout 30s make -C REVIEW_SCRATCH/starter test
```

The build exited `0`. The deliberately incomplete starter test exited `2` and reproduced the
documented baseline:

```text
[PASS] initializers and constants
[PASS] scheduler validation
[PASS] VM validation
[PASS] RAMFS validation
[FAIL] scheduler lifecycle
[FAIL] VM lifecycle
[FAIL] RAMFS lifecycle

4 passed, 3 failed
```

```sh
timeout 30s make -C REVIEW_SCRATCH/sealed/reference clean test
```

Observed exit code: `0`.

```text
reference tests: PASS
```

The command also completed its byte comparison between the starter and reference headers and built
all core files with `-std=c11 -Wall -Wextra -Werror -pedantic -ffreestanding`.

```sh
cc -IREVIEW_SCRATCH/sealed/reference/include -std=c11 -Wall -Wextra \
  -Werror -pedantic REVIEW_SCRATCH/public_tests/test_public.c \
  REVIEW_SCRATCH/sealed/reference/build/libmicaos.a \
  -o REVIEW_SCRATCH/sealed/reference/build/test_public_against_reference
timeout 30s REVIEW_SCRATCH/sealed/reference/build/test_public_against_reference
nm -u REVIEW_SCRATCH/sealed/reference/build/libmicaos.a
```

All three commands exited `0`. The public executable reported `7 passed, 0 failed`; `nm` listed the
three object headings with no undefined symbols.

## Independent behavioral comparison

A reviewer-authored scratch C harness maintained separate abstract models and compared status codes,
outputs, and complete public state after deterministic pseudo-random operations. It exercised PID
collision/wrap inputs, scheduler lifecycle and output preservation, two VM address spaces with frame
exhaustion/reuse/protection, and RAMFS capacity, invalid names, ranges, sparse I/O, slot reuse, and
overlapping write input.

```sh
cc -IREVIEW_SCRATCH/sealed/reference/include -std=c11 -Wall -Wextra \
  -Werror -pedantic -O2 REVIEW_SCRATCH/independent_model_test.c \
  REVIEW_SCRATCH/sealed/reference/scheduler.c \
  REVIEW_SCRATCH/sealed/reference/vm.c \
  REVIEW_SCRATCH/sealed/reference/ramfs.c \
  -o REVIEW_SCRATCH/independent_model_test
timeout 30s REVIEW_SCRATCH/independent_model_test
```

Observed exit codes: compile `0`, run `0`.

```text
independent model sequences: PASS (90000 operations)
```

This was a bounded deterministic comparison, not a coverage-guided fuzzer and not evidence for a
`FUZZED` label.

## Additional compilation and reproducibility checks

Each reference core file compiled separately at `-O2` with the submitted flags plus
`-Wconversion -Wsign-conversion -Wshadow -Wstrict-prototypes -Wmissing-prototypes`; all three
commands exited `0` with no diagnostics.

The complete reference suite was then compiled and run at `-O3` once with `-fsigned-char` and once
with `-funsigned-char`. Both compiles and runs exited `0` and printed `reference tests: PASS`.

Two successive `make -s -C REVIEW_SCRATCH/sealed/reference clean test` runs both passed. A
path-normalized SHA-256 over every regular build output was identical:

```text
reference_build_tree_hash_1=8c72b3a9199c44732dcac5975e21d313443cdb03ec54a7fb45e40eab910d8db2
reference_build_tree_hash_2=8c72b3a9199c44732dcac5975e21d313443cdb03ec54a7fb45e40eab910d8db2
repeat_build_match=yes
```

## Metadata, provenance, and content checks

An independent Python audit used duplicate-key- and non-finite-number-rejecting JSON parsing. It
checked the exact manifest key set, fixed project/source/commit identities, `GENERATED` / `PARTIAL`
labels, `independent_validation: REQUIRED`, `productionized: false`, the shared snapshot digest, and
catalog/linked-resource license cross-fields.

Observed exit code: `0`.

```text
strict manifest/provenance audit: PASS
labels: GENERATED,PARTIAL
linked resource license: NOASSERTION
```

`cmp -s` confirmed that the starter and sealed public headers are byte-identical. A scan for AWS-,
GitHub-, and OpenAI-shaped tokens, private-key headers, and assigned credential values exited `0`:

```text
credential-pattern scan: 0 matches across 42 regular files
```

Manual inspection found all solution implementations and answer documents under `sealed/`, while
learner-facing material contains requirements, prompts, symptoms, and public examples. No exported
student view was available for an end-to-end isolation check.

## Documentation/API consistency finding

```sh
grep -RInE '\bcurrent\b|\bcursor\b' CANDIDATE
```

The scan showed that two sealed scheduler answers use a `current` field absent from the API. A small
independent probe ran spawn, schedule, and block against the reference:

```text
selected=1 cursor=0 running=0 selected_state=3
cursor_probe_compile_exit=0
cursor_probe_run_exit=0
```

State `3` is `MICA_PROCESS_BLOCKED`. Thus `cursor` remains scheduling history when there is no
running process, contradicting the answer text that `current` is cleared or exactly tracks RUNNING.

## Inconclusive or unavailable checks

AddressSanitizer and UndefinedBehaviorSanitizer compilation were attempted with GCC. Both link steps
failed before execution because the installed runtime targets were missing:

```text
/usr/bin/ld: cannot find /usr/lib64/libasan.so.5.0.0
/usr/bin/ld: cannot find /usr/lib64/libubsan.so.1.0.0
```

No sanitizer result is claimed. There was also no second compiler, static analyzer, cross toolchain,
emulator, hardware, coverage run, benchmark, or production test. The upstream repositories and
immutable source snapshot were outside the review workspace, so the recorded commit, source license,
and no-copy assertion could not be compared externally. These remain limitations, not passes.

## Result

`REVISE`: executable checks passed in the exercised host scope, but the two sealed scheduler answers
must be corrected before approval.
