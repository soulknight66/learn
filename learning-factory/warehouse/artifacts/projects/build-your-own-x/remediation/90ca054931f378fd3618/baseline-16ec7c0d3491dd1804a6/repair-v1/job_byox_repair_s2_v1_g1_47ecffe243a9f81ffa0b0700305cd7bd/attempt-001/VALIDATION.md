# Local repair validation evidence

## Status boundary

Repair generation 1 was exercised locally on 2026-09-03 from the repository
root.  `MANIFEST.yaml` remains `GENERATED` with only `GENERATED` and `PARTIAL`
labels, and independent validation remains `REQUIRED`.  These observations are
builder evidence, not factory validation labels or a production-readiness
claim.  No network access, benchmark, or fuzzing run was performed.

The complete builder archive intentionally contains `sealed/`.  No student
workspace was created.  Publication remains conditional on an
orchestrator-captured learner projection proving that sealed/reference/answer
material is absent.

## Tools actually invoked

```sh
/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc --version | sed -n '1p'
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
/usr/bin/make --version | sed -n '1p'
```

Observed, respectively:

```text
gcc (GCC) 15.2.0
Python 3.11.5
GNU Make 4.2.1
```

The configured GCC and Python binaries were invoked by their exact absolute
paths.  The other configured toolchain roots were not needed.

## Strict normal builds and tests

Every command was bounded with `timeout` when it could execute guest code or a
test harness.

```sh
timeout 30s environment/check.sh
timeout 60s make -C starter clean all
timeout 30s env MICROC_BIN="$PWD/starter/build/emberc" \
  public_tests/run.sh --lexer-only
```

All exited 0.  The environment check printed the pinned GCC and Python
versions and `C17 syntax smoke check: PASS`.  The starter built with
`-std=c17 -O2 -g -Wall -Wextra -Werror -pedantic`; its milestone run reported
2 passing lexer tests and 8 intentional language-test skips.

```sh
timeout 60s make -C sealed/reference clean all
timeout 30s env MICROC_BIN="$PWD/sealed/reference/build/emberc-ref" \
  public_tests/run.sh
timeout 60s sealed/reference_tests/run.sh
timeout 10s sealed/reference/build/emberc-ref \
  --tower sealed/reference/self/tower.ec
```

All exited 0.  The reference used the same strict flags.  The public suite
reported 10 passing tests.  The sealed runner reported `VM unit tests: 26
passed` and 18 passing Python test methods.  Those durable tests include each
checked-arithmetic failure class, malformed VM inputs, exact runtime prefixes,
zero/invalid/exhausted budgets, output before fault, and accepted/rejected
boundaries for parentheses, call primaries, unary chains, blocks, `if`, and
`while`.  The original 8,000-parenthesis regression also returned the asserted
source-located depth diagnostic rather than a signal.  Tower stdout was exactly
`4242\n`.

Direct diagnostic probes were run with:

```sh
timeout 10s sealed/reference/build/emberc-ref \
  public_tests/cases/bad_overflow.ec
timeout 10s sealed/reference/build/emberc-ref --max-steps 0 \
  public_tests/cases/factorial.ec
```

Each returned 1 and printed one stderr line:

```text
public_tests/cases/bad_overflow.ec:3:19: runtime error: signed arithmetic overflow
public_tests/cases/factorial.ec:2:13: runtime error: instruction budget exceeded
```

An earlier `sealed/reference_tests/run.sh` attempt built successfully and
reported all 26 direct VM checks passing, but its Python phase ended with 36
errors because this workspace has no usable system temporary directory.  The
harness was changed to create bounded temporary cases under its writable
`sealed/reference_tests/build/` scratch directory.  The successful normal and
sanitizer reruns above and below use that final harness.

## Address/undefined-behavior sanitizer rerun

Final sources were rebuilt with:

```sh
SAN_FLAGS='-std=c17 -O1 -g -Wall -Wextra -Werror -pedantic -fsanitize=address,undefined -fno-omit-frame-pointer'
timeout 60s make -C sealed/reference clean all CFLAGS="$SAN_FLAGS"
timeout 60s make -C sealed/reference_tests clean all CFLAGS="$SAN_FLAGS"
```

Both builds exited 0.  Because the pinned runtime directory has versioned
regular files but no loader-name symlinks, each execution explicitly preloaded
the exact configured runtime files:

```sh
timeout 30s env \
  LD_PRELOAD=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64/libasan.so.8.0.0:/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64/libubsan.so.1.0.0 \
  ASAN_OPTIONS=detect_leaks=0:halt_on_error=1:abort_on_error=1 \
  UBSAN_OPTIONS=halt_on_error=1 \
  sealed/reference_tests/build/test_vm
timeout 30s env \
  LD_PRELOAD=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64/libasan.so.8.0.0:/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64/libubsan.so.1.0.0 \
  ASAN_OPTIONS=detect_leaks=0:halt_on_error=1:abort_on_error=1 \
  UBSAN_OPTIONS=halt_on_error=1 \
  MICROC_BIN="$PWD/sealed/reference/build/emberc-ref" public_tests/run.sh
timeout 60s env \
  LD_PRELOAD=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64/libasan.so.8.0.0:/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64/libubsan.so.1.0.0 \
  ASAN_OPTIONS=detect_leaks=0:halt_on_error=1:abort_on_error=1 \
  UBSAN_OPTIONS=halt_on_error=1 \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  -m unittest -v sealed.reference_tests.test_private
```

All exited 0: 26 direct VM checks, 10 public tests, and 18 private test methods
passed, including both syntax-depth boundaries and the 8,000-parenthesis
regression.  No ASan or UBSan diagnostic was observed.  Leak detection was
explicitly disabled, so this is not leak-check evidence.

## Final archive-boundary checks

Build outputs and Python bytecode caches were removed explicitly.  The final
bounded verifier command was:

```sh
timeout 30s /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  sealed/reference_tests/verify_pack.py
```

It exited 0 and printed `PASS` for required paths, forbidden paths,
manifest/provenance equality, regular archive entry types, and the
credential-pattern scan.  A separate final search found no `build/`,
`__pycache__/`, `*.pyc`, top-level `LICENSE`, or
`ARTIFACT_INVENTORY.sha256` output in the repaired pack.
