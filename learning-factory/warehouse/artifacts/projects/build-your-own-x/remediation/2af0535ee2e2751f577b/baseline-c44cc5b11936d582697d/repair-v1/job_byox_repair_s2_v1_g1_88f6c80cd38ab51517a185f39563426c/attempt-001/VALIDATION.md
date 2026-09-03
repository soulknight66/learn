# Validation record — repair generation 1

Validation date: 2026-09-02 (America/Chicago). Commands ran from the repository root unless a different working directory is stated. No network access was attempted. The authoritative artifact status remains `GENERATED` + `PARTIAL`; these local observations grant no stronger validation label.

## Supplied toolchain

Exact version commands:

```sh
/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc --version
/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/ld --version
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3.11 --version
/usr/bin/make --version
```

All exited 0. The first lines were, respectively, `gcc (GCC) 15.2.0`, `GNU ld (GNU Binutils) 2.43`, `Python 3.11.5`, and `GNU Make 4.2.1`.

The environment probe was run without adding the supplied roots to `PATH`:

```sh
mkdir -p sealed/reference_tests/build/tmp
TMPDIR="$PWD/sealed/reference_tests/build/tmp" /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3.11 environment/check_environment.py --cc /arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc --cc-option=-B/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/ --make /usr/bin/make
```

Both commands exited 0. The probe reported the exact compiler, Make, and Python paths above, their same versions, and `C11 int64_t compile/run probe: PASS`.

## Builds

An initial build attempt deliberately passed the supplied GCC by absolute path but did not yet give its isolated driver the Binutils search prefix:

```sh
/usr/bin/make -C starter clean all CC=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc
/usr/bin/make -C sealed/reference clean all CC=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc
/usr/bin/make -C sealed/reference_tests clean all CC=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc
```

Each command compiled its C translation units without diagnostics, then exited 2 at link time with `collect2: fatal error: cannot find 'ld'`. This was a tool-location failure, not a source compilation failure.

The bounded rebuild supplied Binutils 2.43 explicitly through GCC's `-B` option:

```sh
/usr/bin/make -C starter clean all CC=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc CFLAGS='-std=c11 -Wall -Wextra -Wpedantic -Werror -O2 -B/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/'
/usr/bin/make -C sealed/reference clean all CC=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc CFLAGS='-std=c11 -Wall -Wextra -Wpedantic -Werror -O2 -B/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/'
/usr/bin/make -C sealed/reference_tests clean all CC=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc CFLAGS='-std=c11 -Wall -Wextra -Wpedantic -Werror -O2 -B/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/'
```

All three exited 0. GCC emitted no warnings or errors under the recorded warning-as-error flags.

## Tests and repaired regressions

Exact test commands:

```sh
TMPDIR="$PWD/sealed/reference_tests/build/tmp" /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3.11 public_tests/run_tests.py --binary sealed/reference/build/sprig
TMPDIR="$PWD/sealed/reference_tests/build/tmp" /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3.11 sealed/reference_tests/run_tests.py --binary sealed/reference/build/sprig
/usr/bin/make -C sealed/reference_tests test CC=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc CFLAGS='-std=c11 -Wall -Wextra -Wpedantic -Werror -O2 -B/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/'
TMPDIR="$PWD/sealed/reference_tests/build/tmp" /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3.11 public_tests/run_tests.py --binary starter/build/sprig
```

Observed outcomes, in order:

- exit 0, 11 public reference tests, `OK`;
- exit 0, 22 sealed black-box tests, `OK`;
- exit 0, `12 VM safety tests passed`;
- exit 1, 11 public starter tests: the empty program, ordinary token mode, and late-error token atomicity passed; the other eight stopped at the intentional compiler stub.

The new black-box checks verify that a lexical error after valid tokens exits 65 with empty standard output. They direct each of normal, `--tokens`, and `--disassemble` output to `/dev/full`, cover a runtime error after buffered program output, and close a pipe before the child writes; every attempted-output failure must exit 74 with an error diagnostic. The direct VM additions use unbuffered and fully buffered `/dev/full` streams to exercise both immediate write failure and final-flush failure.

One direct invocation was initially made from the repository root:

```sh
sealed/reference_tests/build/vm_safety
```

It exited 1 because the fixture's documented relative `build/vm_safety_output.tmp` path is resolved from `sealed/reference_tests/`; all ten file-backed pre-existing cases reported that their output fixture was unavailable. Running through the Makefile command above supplied the intended working directory and passed all 12 cases.

## Bounded harness smoke checks

The deterministic adversarial generator was run twice into scoped build scratch directories:

```sh
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3.11 adversarial/generate_cases.py sealed/reference_tests/build/generated-cases-a
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3.11 adversarial/generate_cases.py sealed/reference_tests/build/generated-cases-b
diff -qr sealed/reference_tests/build/generated-cases-a sealed/reference_tests/build/generated-cases-b
```

Both generator runs exited 0 and reported 10 cases; `diff` exited 0 with no output.

The benchmark helper received only a one-sample harness smoke check:

```sh
TMPDIR="$PWD/sealed/reference_tests/build/tmp" /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3.11 benchmarks/run_benchmark.py --binary sealed/reference/build/sprig --iterations 1 --warmup 0
```

It exited 0, validated 190 output lines, and observed `0.002429450862109661` seconds. This shared-host sample is not benchmark evidence and does not support a `BENCHMARKED` label.

## Metadata, isolation, credentials, and cleanup

The complete required/forbidden lists and credential patterns are now replayable in `environment/audit_pack.py`. The final clean-tree command was:

```sh
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3.11 environment/audit_pack.py
```

It exited 0 with `required_files=23 missing=0`, `forbidden_paths_present=0`, `unexpected_top_level_entries=0`, `generated_special_files_or_symlinks=0`, `credential_pattern_matches=0`, and `pack audit: PASS`. Its duplicate-key-rejecting JSON loader also confirmed the exact manifest object and immutable metadata bytes. Fresh SHA-256 observations were:

```text
d790bd7487c566f570a0207bb94f3cf1d2af4815acb04f3d14153bde62600c8e  MANIFEST.yaml
db3da454c4b0e7f852e59a264c6e2296b2dd561c35ca2b5bf5f8f9b04d127169  PROVENANCE.json
```

Only scoped scratch artifacts were removed:

```sh
/usr/bin/make -C starter clean
/usr/bin/make -C sealed/reference clean
/usr/bin/make -C sealed/reference_tests clean
rm -r sealed/reference_tests/build/generated-cases-a sealed/reference_tests/build/generated-cases-b
rmdir sealed/reference_tests/build/tmp
```

All five cleanup commands exited 0. The empty prior `build/` directories remain. No sanitizer, fuzzing, transfer, security, production-readiness, or independent acceptance validation was performed.
