# Independent validation record

Review date: 2026-09-03 (America/Chicago). Commands were run from the review
workspace root unless a working directory is stated. All guest execution and
test harnesses were bounded with `/usr/bin/timeout`.

`CANDIDATE/` was read-only and was not edited. Build and adversarial checks ran
in `.review-scratch/`, initially made as a byte-for-byte copy. `cp -a` retained
read-only directory modes, so the first scratch build could not create
`starter/build`; the reviewer changed only the copy's owner-write bits and
repeated the build. The original candidate's aggregate digest was identical
before and after review.

Scratch setup was:

```sh
/usr/bin/mkdir .review-scratch
/usr/bin/cp -a CANDIDATE/. .review-scratch/.
/usr/bin/chmod -R u+w .review-scratch
```

The first build attempt preceded the `chmod`; all later commands described as
running "from the writable copy" used `.review-scratch/` as their working
directory.

## Tool identity

```sh
/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc --version
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/ld --version
/usr/bin/make --version
```

Observed first lines:

```text
gcc (GCC) 15.2.0
Python 3.11.5
GNU ld (GNU Binutils) 2.43
GNU Make 4.2.1
```

The useful configured binaries were invoked through the exact paths above.
The other configured toolchain roots were not needed. `rg` and `git` were not
available; inventory checks used `/usr/bin/find` and `/usr/bin/grep`.

## Submission integrity and provenance

```sh
cd CANDIDATE
/usr/bin/find . -type f -print0 | /usr/bin/sort -z \
  | /usr/bin/xargs -0 /usr/bin/sha256sum | /usr/bin/sha256sum
/usr/bin/sha256sum PROVENANCE.json MANIFEST.yaml
/usr/bin/find . -type l -print
```

Observed:

```text
d054d2bea356dc282bc4b8dec13116454915dab93901a6cee1137924ff0f789c  -
3dc7fc913794fd6c9205f6d0588d0a9c4370fb639ae6991b97b4f28aaff9d57a  PROVENANCE.json
65467d58c5d0aafa3bcc9160d5ebb6aa7a78416e57137d07672277ff4dea4586  MANIFEST.yaml
```

The aggregate digest was observed again unchanged after testing. No symlink,
`build/`, `__pycache__/`, `*.pyc`, or `*.o` was found in the submitted tree.
Strict JSON parsing and cross-checks confirmed that project ID, source ID,
source commit, and snapshot hash agree between the manifest and provenance.

```sh
/usr/bin/timeout 30s \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  CANDIDATE/sealed/reference_tests/verify_pack.py
```

Exit 0:

```text
required paths: PASS
forbidden paths: PASS
manifest/provenance: PASS
regular-file boundary: PASS
credential-pattern scan: PASS
```

An independent whole-tree search found no credential-pattern match in the
submitted candidate. Source inspection found no `shell=True`, `os.system`,
`popen`, or C `system()` call; both Python harnesses use `subprocess.run` with
argument arrays, captured streams, and explicit timeouts.

## Environment check and documented-build failure

From the writable copy:

```sh
/usr/bin/timeout 30s ./environment/check.sh
```

Exit 0:

```text
gcc (GCC) 15.2.0
Python 3.11.5
C17 syntax smoke check: PASS
```

The documented clean build commands were then run without adding a linker to
`PATH`:

```sh
/usr/bin/timeout 60s /usr/bin/make -C starter clean all
/usr/bin/timeout 60s /usr/bin/make -C sealed/reference clean all
```

Each exited 2. Both compiled all four objects, then failed at the executable
link with:

```text
collect2: fatal error: cannot find 'ld'
```

The diagnostic is explained by:

```sh
/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc -print-prog-name=ld
/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc \
  -B/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/ -print-prog-name=ld
```

Observed:

```text
ld
/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/ld
```

This failed reproduction is the primary reason for `REVISE`.

## Normal build and behavioral checks with explicit linker binding

To continue evaluating source correctness without repairing the candidate, the
reviewer supplied the configured Binutils directory only as a command-line
override in the scratch copy:

```sh
/usr/bin/timeout 60s /usr/bin/make -C starter clean all \
  "CC=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc -B/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/"
/usr/bin/timeout 60s /usr/bin/make -C sealed/reference clean all \
  "CC=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc -B/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/"
```

Both exited 0 using `-std=c17 -O2 -g -Wall -Wextra -Werror -pedantic`.

```sh
/usr/bin/timeout 30s env \
  MICROC_BIN="$PWD/starter/build/emberc" \
  PYTHON_BIN=/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  ./public_tests/run.sh --lexer-only
```

Exit 0: 10 discovered, 2 passed, 8 intentionally skipped.

```sh
/usr/bin/timeout 30s env \
  MICROC_BIN="$PWD/sealed/reference/build/emberc-ref" \
  PYTHON_BIN=/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  ./public_tests/run.sh
/usr/bin/timeout 90s env \
  "CC=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc -B/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/" \
  PYTHON_BIN=/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  ./sealed/reference_tests/run.sh
```

Both exited 0. Observed totals were 10 public tests, 26 direct VM checks, and
18 private test methods, all passing.

Direct probes:

```sh
/usr/bin/timeout 10s ./sealed/reference/build/emberc-ref \
  --tower sealed/reference/self/tower.ec
/usr/bin/timeout 10s ./sealed/reference/build/emberc-ref \
  public_tests/cases/bad_overflow.ec
/usr/bin/timeout 10s ./sealed/reference/build/emberc-ref \
  --max-steps 0 public_tests/cases/factorial.ec
```

Observed respectively:

```text
exit 0; stdout: 4242\n
exit 1; public_tests/cases/bad_overflow.ec:3:19: runtime error: signed arithmetic overflow
exit 1; public_tests/cases/factorial.ec:2:13: runtime error: instruction budget exceeded
```

## Reviewer-authored boundary checks

The temporary reviewer-authored `reviewer_independent_checks.py` (SHA-256
`d32cf15b9b94f6ca35ad5ebf696ae0706d759cb31b1a30f36b09a7e5cb0016ce`)
launched the reference with argument arrays and five- or ten-second subprocess
timeouts, created cases only under the writable scratch directory, and asserted
behavior directly from `REQUIREMENTS.md` rather than accepting builder prose as
an oracle. It was reviewer instrumentation, not candidate material, and was
removed after the recorded run.

```sh
/usr/bin/timeout 60s \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  reviewer_independent_checks.py
```

Exit 0:

```text
independent checks: 9 passed
PASS: 63-byte identifier accepted
PASS: 64-byte identifier rejected with one diagnostic
PASS: 256 simultaneous locals accepted
PASS: 257th simultaneous local rejected
PASS: logical results normalized and faulting RHS short-circuited
PASS: opcode-only budget accounting and UINT64_MAX parsing
PASS: non-ASCII source byte rejected
PASS: source-size boundary enforced
PASS: bytecode-word boundary enforced
```

## Sanitizer rerun

The reference and direct VM test were rebuilt in the scratch copy with:

```text
-std=c17 -O1 -g -Wall -Wextra -Werror -pedantic
-fsanitize=address,undefined -fno-omit-frame-pointer
```

The same explicit GCC `-B` binding was used. Executions preloaded:

```text
/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64/libasan.so.8.0.0
/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64/libubsan.so.1.0.0
```

with `ASAN_OPTIONS=detect_leaks=0:halt_on_error=1:abort_on_error=1` and
`UBSAN_OPTIONS=halt_on_error=1`. The direct VM binary passed 26 checks, the
public suite passed 10 tests, and the private suite passed 18 methods. All
commands exited 0 and no ASan/UBSan diagnostic was observed. Leak detection was
disabled, so this provides no leak-check claim.

## Verifier adversarial check

Only in the scratch copy, the reviewer inserted an unexpected top-level file
named `UNEXPECTED_SECRET.txt` containing a clearly fake string that matches the
verifier's `api_key` credential regex. Running the normal verifier command
still exited 0 and printed all five `PASS` lines, including
`credential-pattern scan: PASS`. The fixture was then removed.

Static inspection explains the result: `managed_paths()` scans known required
top-level files and descendants of `MANAGED_ROOTS`, not arbitrary root
entries. The current submitted candidate independently contains no unexpected
entry or credential match; this is a regression weakness in the verifier, not
evidence of a present secret.

## Disclosure, licensing, and unresolved checks

- All learner-facing and sealed materials were inspected. Sealed answers and
  private tests occur under `sealed/`; none was found outside that tree.
- The complete candidate is a builder archive, not a learner projection. No
  orchestrator-captured transfer evidence was available, so isolation remains
  inconclusive and the archive must not be published directly.
- The CC0 assertion is scoped to catalog metadata; the linked tutorial remains
  `NOASSERTION`. This boundary is explicit and internally consistent.
- Network and the immutable source baseline were unavailable, so upstream
  commit identity, linked-resource licensing, and independent authorship were
  not externally corroborated.
- No fuzzing, benchmark, leak-detection, production, transfer, or cross-host
  run was performed. None of those labels is awarded by this review.

After all evidence was captured, the reviewer deleted the explicitly verified
`.review-scratch/` tree and its build products. The immutable `CANDIDATE/` tree
and the durable review artifacts were retained.
