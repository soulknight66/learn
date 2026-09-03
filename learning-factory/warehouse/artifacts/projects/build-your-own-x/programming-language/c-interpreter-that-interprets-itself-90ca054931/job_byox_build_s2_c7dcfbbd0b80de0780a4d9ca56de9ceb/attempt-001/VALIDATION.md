# Local validation evidence

## Status boundary

The immutable manifest remains `GENERATED` with labels `GENERATED` and
`PARTIAL`; `independent_validation` remains `REQUIRED`.  The observations below
are worker-local evidence, not learning-factory validation labels and not a
production-readiness claim.

Commands were run from the repository root on 2026-09-03.  No upstream network
access was attempted.  No benchmark or fuzzing run was performed.

## Pinned tools actually invoked

```text
/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc --version
gcc (GCC) 15.2.0

/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
Python 3.11.5

/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/ld --version
GNU ld (GNU Binutils) 2.43
```

## Normal build and test observations

```sh
environment/check.sh
```

Exit 0.  Observed `gcc (GCC) 15.2.0`, `Python 3.11.5`, and
`C17 syntax smoke check: PASS`.

```sh
make -C starter clean all
MICROC_BIN="$PWD/starter/build/emberc" public_tests/run.sh --lexer-only
```

Both commands exited 0.  The build used the exact pinned GCC path with
`-std=c17 -O2 -g -Wall -Wextra -Werror -pedantic`.  The test runner reported 2
passing lexer tests and 7 intentional compiler/VM skips.

```sh
make -C sealed/reference clean all
MICROC_BIN="$PWD/sealed/reference/build/emberc-ref" public_tests/run.sh
```

Both commands exited 0 with the same strict compile flags.  The public runner
reported 9 tests passing.

```sh
sealed/reference_tests/run.sh
```

Exit 0.  The direct C VM executable reported `VM unit tests: 10 passed`; the
sealed Python runner reported 11 tests passing.  These cover malformed
bytecode, arithmetic boundaries, scoping, heap bounds, instruction budgets,
emission layout, and the finite tower.

```sh
sealed/reference/build/emberc-ref --tower sealed/reference/self/tower.ec
```

Exit 0 with exact standard output:

```text
4242
```

## Sanitizer observation

The reference and direct VM tests compiled with:

```sh
SAN_FLAGS='-std=c17 -O1 -g -Wall -Wextra -Werror -pedantic -fsanitize=address,undefined -fno-omit-frame-pointer'
make -C sealed/reference clean all CFLAGS="$SAN_FLAGS"
make -C sealed/reference_tests clean all CFLAGS="$SAN_FLAGS"
```

Both builds exited 0.  The first execution attempt returned 127 with the exact
loader blocker `libasan.so.8: cannot open shared object file: No such file or
directory`; the pinned runtime directory contains versioned regular files but
no loader-name symlink.

The reproducible retry preloaded those exact pinned runtime files:

```sh
ASAN_LIB=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64/libasan.so.8.0.0
UBSAN_LIB=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64/libubsan.so.1.0.0
export LD_PRELOAD="$ASAN_LIB:$UBSAN_LIB"
export ASAN_OPTIONS=detect_leaks=0:halt_on_error=1
export UBSAN_OPTIONS=halt_on_error=1
sealed/reference_tests/build/test_vm
MICROC_BIN="$PWD/sealed/reference/build/emberc-ref" public_tests/run.sh
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  -m unittest -v sealed.reference_tests.test_private
```

All commands exited 0: 10 direct VM checks, 9 public checks, and 11 sealed
checks passed with no AddressSanitizer or UndefinedBehaviorSanitizer diagnostic.
This remains local evidence only.

## Informative host constraints

An early private-test harness used `tmpfile()` and returned `tmpfile failed` in
this sandbox.  Because none of those direct VM cases prints, it now uses its
existing standard-output stream and creates no scratch file.  An early
environment smoke check similarly found that `/tmp` does not exist; the final
check uses GCC `-fsyntax-only` on standard input.  Neither workaround changes
guest-language behavior.

## Archive checks

The final reproducible structure command is:

```sh
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  sealed/reference_tests/verify_pack.py
```

It exited 0 and printed `PASS` for required paths, forbidden paths,
manifest/provenance, the regular-file boundary, and the credential-pattern
scan.
