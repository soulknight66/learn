# Independent validation record

Date: 2026-09-02 (America/Chicago). Commands ran from the provided review workspace. `CANDIDATE/` was never edited.

Shell startup printed `id: cannot find name for user/group ID` on every invocation. Those container identity warnings were external to the candidate programs.

## Isolation and environment

The candidate was copied to `.review-scratch.xRRC95/candidate`. `cp -a` preserved the immutable source directory modes, so the first copied build attempts exited 2 with `Cannot create temporary file in ./: Permission denied`; the first environment probe exited 1 because no system temporary directory was usable. Those attempts did not evaluate candidate compilation.

Write permission was added only to the disposable copy, and a local temp directory was selected:

```sh
chmod -R u+w .review-scratch.xRRC95/candidate
mkdir .review-scratch.xRRC95/tmp
TMPDIR="$PWD/.review-scratch.xRRC95/tmp" python3 environment/check_environment.py
```

Observed exit 0:

```text
environment check: PASS
compiler: cc (GCC) 8.5.0 20210514 (Red Hat 8.5.0-22)
make: GNU Make 4.2.1
python: 3.6.8 (default, Apr 25 2024, 09:54:46)
C11 int64_t compile/run probe: PASS
```

## Builds and supplied suites

From the isolated candidate root, with the same local `TMPDIR`:

```sh
make -C starter clean all
make -C sealed/reference clean all
make -C sealed/reference_tests clean all
```

All exited 0. Both Sprig binaries used `-std=c11 -Wall -Wextra -Wpedantic -Werror -O2`; no compiler diagnostics were emitted.

```sh
python3 public_tests/run_tests.py --binary sealed/reference/build/sprig
python3 sealed/reference_tests/run_tests.py --binary sealed/reference/build/sprig
make -C sealed/reference_tests test
python3 public_tests/run_tests.py --binary starter/build/sprig
```

Observed, in order:

- exit 0, 10 public tests, `OK`;
- exit 0, 19 sealed black-box tests, `OK`;
- exit 0, `10 VM safety tests passed`;
- exit 1, 10 starter tests: empty-program and token-mode passed, 8 tests failed at the explicit compiler stub.

The starter result matches the documented progressive baseline and is not treated as a completed implementation.

## Reviewer-authored correctness checks

An ephemeral reviewer-authored Python harness generated expressions from 13 signed 64-bit boundary values, computed expected results with Python integers, and invoked the reference with argument arrays and a three-second per-process timeout:

```sh
python3 independent_checks.py candidate/sealed/reference/build/sprig independent-cases
```

Observed exit 0:

```text
independent checks: PASS
arithmetic model cases: 520 valid, 156 runtime errors
contract boundary cases: 13
```

The 13 boundary cases independently checked 31/32-byte identifiers, embedded NUL, exact and over-limit VM stack depth, exact and over-limit parenthesis/unary nesting, an exact 1024-instruction disassembly, an over-limit program, and exact/over-limit 1 MiB sources.

The reference was separately compiled with GCC signed-overflow trapping and the same harness was repeated:

```sh
cc -Icandidate/sealed/reference/include \
  -std=c11 -Wall -Wextra -Wpedantic -Werror -O2 -ftrapv \
  candidate/sealed/reference/src/main.c \
  candidate/sealed/reference/src/lexer.c \
  candidate/sealed/reference/src/compiler.c \
  candidate/sealed/reference/src/vm.c -o trapv-sprig
python3 independent_checks.py trapv-sprig trapv-cases
```

Compile exit 0; the same 520 valid, 156 runtime-error, and 13 boundary cases passed with exit 0.

A separate reviewer-authored C harness linked directly to `vm.c` under `-ftrapv`:

```sh
cc -Icandidate/sealed/reference/include \
  -std=c11 -Wall -Wextra -Wpedantic -Werror -O2 -ftrapv \
  independent_vm_checks.c candidate/sealed/reference/src/vm.c \
  -o independent-vm-checks
./independent-vm-checks
```

Observed compile exit 0 and execution exit 0: `independent VM checks: PASS (11 cases)`. Cases covered invalid metadata, negative/out-of-range slots, arithmetic and unary underflow, stack overflow, missing/early HALT, and a valid store/load/add/print program.

## Independently reproduced contract failures

Late lexical failure in token mode was invoked with an argv array against:

```text
let x = 1;
print @;
```

Observed:

```json
{"exit": 65, "stderr": "late-lex-error.sprig:2:7: error: unexpected byte '@'\n", "stdout": "1:1 LET\n1:5 IDENTIFIER x\n1:7 EQUAL\n1:9 INTEGER 1\n1:10 SEMICOLON\n2:1 PRINT\n"}
```

The exit and diagnostic are correct, but nonempty stdout violates `REQUIREMENTS.md` line 45.

Each CLI mode was then run with stdout opened on `/dev/full`, using a three-second timeout:

```json
{"disassemble": {"exit": 0, "stderr": ""}, "run": {"exit": 70, "stderr": "./candidate/sealed/reference/examples/hello.sprig:6:1: error: failed to flush program output"}, "tokens": {"exit": 0, "stderr": ""}}
```

`REQUIREMENTS.md` line 44 assigns file-I/O failures exit 74. None of the three observations met that contract.

## Harness and metadata checks

```sh
python3 candidate/adversarial/generate_cases.py generated-cases-a
python3 candidate/adversarial/generate_cases.py generated-cases-b
diff -u <(cd generated-cases-a && sha256sum -- *) \
        <(cd generated-cases-b && sha256sum -- *)
```

Both generator runs exited 0 and reported 10 cases; `diff` exited 0. The aggregate list digest was `ddf0c6a6377ac36cb59aa4a9c4d0ea93c7d25f2e598a7f548a73c1a61a00a9c7`.

```sh
python3 candidate/benchmarks/run_benchmark.py \
  --binary candidate/sealed/reference/build/sprig \
  --iterations 3 --warmup 1
```

Observed exit 0, three samples, 190 output lines per run, and median `0.00395661685615778` seconds. This only confirms that the bounded harness executes and validates output shape; it is not `BENCHMARKED` evidence.

Strict JSON loading and SHA-256 checks observed:

```text
d790bd7487c566f570a0207bb94f3cf1d2af4815acb04f3d14153bde62600c8e  CANDIDATE/MANIFEST.yaml
db3da454c4b0e7f852e59a264c6e2296b2dd561c35ca2b5bf5f8f9b04d127169  CANDIDATE/PROVENANCE.json
```

Project ID, source ID, source commit, snapshot link, CC0 catalog license, and linked-resource `NOASSERTION` fields matched internally. The manifest reports exactly `GENERATED, PARTIAL`, `independent_validation=REQUIRED`, and `productionized=false`.

Independent filesystem/content checks found 48 regular candidate files, zero entries other than regular files/directories, zero basic credential-pattern matches, and zero sealed parser/checked-arithmetic implementation signatures in the declared learner-facing files. `diff -qr --exclude=build CANDIDATE .review-scratch.xRRC95/candidate` exited 0 after testing, confirming candidate source content remained unchanged.

## Limitations

- `rg` and `git` are not installed (both exited 127); `find`, `grep`, `cmp`, `diff`, and `sha256sum` were used.
- UBSan linking was unavailable. A static-runtime attempt exited 1 with `/usr/bin/ld: cannot find -lubsan`; `-ftrapv` is narrower and is not sanitizer evidence.
- System temp directories were unavailable; a workspace-local `TMPDIR` was required.
- No network or upstream snapshot was available, so originality, upstream contents/license, and source hashes were not externally verified.
- No actual orchestrator-rendered learner view was supplied; progressive disclosure was checked from paths and content only.
- The candidate does not include the exact path lists and full scan recipe needed to replay its reported `required_files=23` archive audit exactly.
- No fuzzing, cross-platform transfer, security review, certified benchmark, or production validation was performed.
