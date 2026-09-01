# Generation-time validation

Status remains **GENERATED + PARTIAL**. The observations below are local generation evidence, not
independent validation and not an award of BUILDS, TESTED, FUZZED, BENCHMARKED, REVIEWED,
TRANSFER_VERIFIED, or PRODUCTIONIZED.

Date: 2026-08-31 (America/Chicago)

Working directory:

```text
/projects/se/pj34000401_refsys/users/yuali01/learn/learning-factory/warehouse/workspaces/job_byox_build_v1_1863bc88c1a77e27040408cec497262d/attempt-002
```

The execution wrapper printed these unrelated identity lookup warnings before shell commands:

```text
/usr/bin/id: cannot find name for user ID 532319
/usr/bin/id: cannot find name for group ID 500275
/usr/bin/id: cannot find name for user ID 532319
```

## Tool availability

Command:

```sh
command -v cc
command -v gcc
command -v clang
command -v make
python3 --version
```

Observed output (the absent `clang` line means it was not found):

```text
/usr/bin/cc
/usr/bin/gcc
/usr/bin/make
Python 3.6.8
```

## Build and reference validation

Exact command:

```sh
make -C starter clean all
make -C sealed/reference clean all
python3 public_tests/run_tests.py sealed/reference/build/minic
python3 sealed/reference_tests/run_tests.py sealed/reference/build/minic
sealed/reference/build/minic sealed/reference/examples/meta_vm.mc
```

Both make invocations exited 0. Their compiler commands were:

```text
cc -Iinclude -std=c11 -O2 -Wall -Wextra -Wpedantic -Werror -c src/main.c -o build/main.o
cc -Iinclude -std=c11 -O2 -Wall -Wextra -Wpedantic -Werror -c src/source.c -o build/source.o
cc -Iinclude -std=c11 -O2 -Wall -Wextra -Wpedantic -Werror -c src/interpreter.c -o build/interpreter.o
cc -std=c11 -O2 -Wall -Wextra -Wpedantic -Werror build/main.o build/source.o build/interpreter.o -o build/minic
cc -std=c11 -O2 -Wall -Wextra -Wpedantic -Werror src/minic.c -o build/minic
```

Observed test and demonstration output:

```text
PASS arithmetic
PASS control
PASS functions
PASS short-circuit
PASS syntax-error
PASS step-limit
6 passed; 0 failed
PASS comments-zero
PASS forward-call
PASS evaluation-order
PASS signed-math
PASS recursive
PASS nested-interpreter
PASS add-overflow
PASS sub-overflow
PASS mul-overflow
PASS neg-overflow
PASS divide-overflow
PASS remainder-overflow
PASS divide-zero
PASS literal-overflow
PASS unterminated-comment
PASS undefined-function
PASS wrong-arity
PASS duplicate-local
PASS missing-main
PASS main-parameter
PASS frame-limit
PASS step-exact
PASS two-step-success
PASS usage-zero-budget
PASS missing-input
25 passed; 0 failed
42
```

The combined command exited 0.

## Expected incomplete-starter result

Exact command (the shell captured the expected nonzero runner status, then exited 0 so generation
could continue):

```sh
python3 public_tests/run_tests.py starter/build/minic
status=$?
printf 'starter_public_exit=%s\n' "$status"
exit 0
```

Observed result:

```text
FAIL arithmetic
  exit: expected 0, got 65
  stdout: expected '14\n20\n', got ''
FAIL control
  exit: expected 0, got 65
  stdout: expected '120\n', got ''
FAIL functions
  exit: expected 0, got 65
  stdout: expected '42\n', got ''
FAIL short-circuit
  exit: expected 0, got 65
  stdout: expected '0\n1\n', got ''
FAIL syntax-error
  exit: expected 65, got 65
  stdout: expected '', got ''
  stderr needed 'expected', got '<workspace>/public_tests/cases/bad_syntax.mc:1: interpreter not implemented (budget=1000000, bytes=42)\n'
FAIL step-limit
  exit: expected 70, got 65
  stdout: expected '', got ''
  stderr needed 'step limit', got '<workspace>/public_tests/cases/infinite.mc:1: interpreter not implemented (budget=20, bytes=51)\n'
0 passed; 6 failed
starter_public_exit=1
```

In the two diagnostic lines above, `<workspace>` abbreviates the working directory printed at the
top of this file; all other text is verbatim. This is an intentionally informative failure: the
starter loads input but has a marked interpreter TODO.

## Structure and safety audit

The final audit checks all authoritative paths, forbidden names, special files, strict JSON with
duplicate-key rejection, and common credential/private-key patterns. Its final observed output is
recorded after the audit below.

```text
STRICT_JSON MANIFEST.yaml
STRICT_JSON PROVENANCE.json
AUDIT required_paths=23 missing=0 forbidden=0 special_files=0 credential_hits=0
```

Compiled scratch outputs were removed with `make -C starter clean` and
`make -C sealed/reference clean` after validation. Source, fixtures, and logs in this document are
preserved.
