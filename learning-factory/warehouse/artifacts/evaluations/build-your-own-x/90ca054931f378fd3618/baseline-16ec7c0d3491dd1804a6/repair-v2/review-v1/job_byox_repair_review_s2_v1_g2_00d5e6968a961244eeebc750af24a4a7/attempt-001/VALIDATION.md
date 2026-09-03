# Independent review validation

Review date: 2026-09-03. Commands were run from the review workspace unless a
different working directory is stated. `CANDIDATE/` was read-only. Compilation
and generated fixtures used a writable `REVIEW_SCRATCH/` copy.

## Toolchain evidence

```sh
/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc --version
/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/ld --version
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
/usr/bin/make --version
```

Observed first lines: `gcc (GCC) 15.2.0`, `GNU ld (GNU Binutils) 2.43`,
`Python 3.11.5`, and `GNU Make 4.2.1`.

The independent resolution probe exited 0 and printed the exact configured
linker:

```sh
/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc \
  -B/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/ \
  -print-prog-name=ld
```

```text
/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/ld
```

## Staging and clean-environment builds

```sh
mkdir REVIEW_SCRATCH
cp -a CANDIDATE/. REVIEW_SCRATCH/
chmod -R u+w REVIEW_SCRATCH
```

From `REVIEW_SCRATCH/`:

```sh
/usr/bin/timeout 30s /usr/bin/env -i PATH=/usr/bin:/bin \
  ./environment/check.sh
/usr/bin/timeout 60s /usr/bin/env -i PATH=/usr/bin:/bin \
  /usr/bin/make -C starter clean all
/usr/bin/timeout 60s /usr/bin/env -i PATH=/usr/bin:/bin \
  /usr/bin/make -C sealed/reference clean all
/usr/bin/timeout 60s /usr/bin/env -i PATH=/usr/bin:/bin \
  /usr/bin/make -C sealed/reference_tests clean all
```

All four commands exited 0. The environment probe printed GCC 15.2.0, GNU ld
2.43, Python 3.11.5, the exact linker path above, and
`C17 compile/link/execute smoke check: PASS`. Every compile/link line used the
absolute GCC path and explicit Binutils `-B` directory with strict C17 warning
flags.

## Submitted suites (supporting evidence only)

```sh
/usr/bin/timeout 30s /usr/bin/env -i PATH=/usr/bin:/bin \
  MICROC_BIN="$PWD/starter/build/emberc" \
  PYTHON_BIN=/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  ./public_tests/run.sh --lexer-only

/usr/bin/timeout 30s /usr/bin/env -i PATH=/usr/bin:/bin \
  MICROC_BIN="$PWD/sealed/reference/build/emberc-ref" \
  PYTHON_BIN=/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  ./public_tests/run.sh

/usr/bin/timeout 90s /usr/bin/env -i PATH=/usr/bin:/bin \
  PYTHON_BIN=/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  ./sealed/reference_tests/run.sh
```

Observed results:

- starter: 2 lexer tests passed and 8 later-milestone tests skipped;
- reference public suite: 10 of 10 passed;
- sealed runner: `VM unit tests: 26 passed`, followed by 21 passing Python
  methods (18 behavior and 3 pack-verifier methods).

These are submitted tests and do not independently prove a validation label.

## Reviewer-controlled behavior and VM checks

Two ephemeral reviewer harnesses were created outside `CANDIDATE/`. They used
subprocess argument arrays, captured output, temporary fixtures, and per-run
timeouts.

```sh
/usr/bin/timeout 60s /usr/bin/env -i PATH=/usr/bin:/bin \
  PYTHONDONTWRITEBYTECODE=1 \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  reviewer_checks.py
```

Exit 0: `independent reviewer black-box assertions: 21 passed`.

The assertions covered arithmetic/precedence, negative division/remainder,
short-circuit fault suppression, shadow initializers, heap endpoints, signed
argument endpoints, 255/256 syntax-depth entry, 256/257 locals, 63/64-byte
identifiers, non-ASCII input, comments at EOF, exact/oversize 1,048,576-byte
sources, exact instruction budgets, exact/oversize 65,536-word bytecode,
emitted word layout, and the tower output.

```sh
/usr/bin/timeout 30s \
  /arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc \
  -B/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/ \
  -Isealed/reference/include -std=c17 -O2 -g \
  -Wall -Wextra -Werror -pedantic \
  reviewer_vm.c sealed/reference/build/vm.o -o reviewer_vm
/usr/bin/timeout 30s ./reviewer_vm
```

Both exited 0; execution printed
`independent reviewer VM assertions: 9 passed`. Cases covered slots 255/256,
an invalid target on a non-taken `JZ`, a missing final operand, exact opcode
budgets, exact/oversize program metadata, and the 4,096-value stack boundary.

## Static and sanitizer checks

Each reference translation unit was compiled separately with the exact GCC
path, strict flags, `-fanalyzer -c`, and output directed to `/dev/null`:

```sh
/usr/bin/timeout 60s \
  /arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc \
  -B/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/ \
  -Isealed/reference/include -std=c17 -O0 -g \
  -Wall -Wextra -Werror -pedantic -fanalyzer -c \
  sealed/reference/src/main.c -o /dev/null
```

The same command was run for `lexer.c`, `compiler.c`, and `vm.c`. All four
exited 0 without analyzer diagnostics.

Reviewer binaries were then compiled as follows:

```sh
/usr/bin/timeout 60s \
  /arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc \
  -B/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/ \
  -Isealed/reference/include -std=c17 -O1 -g \
  -Wall -Wextra -Werror -pedantic \
  -fsanitize=address,undefined -fno-omit-frame-pointer \
  sealed/reference/src/main.c sealed/reference/src/lexer.c \
  sealed/reference/src/compiler.c sealed/reference/src/vm.c \
  -o reviewer_emberc_san

/usr/bin/timeout 60s \
  /arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc \
  -B/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/ \
  -Isealed/reference/include -std=c17 -O1 -g \
  -Wall -Wextra -Werror -pedantic \
  -fsanitize=address,undefined -fno-omit-frame-pointer \
  reviewer_vm.c sealed/reference/src/vm.c -o reviewer_vm_san
```

Both builds exited 0. The first clean-environment executions were
inconclusive: the direct VM process exited 127 because `libasan.so.8` was not on
the loader path, and the black-box wrapper consequently failed its first
assertion. GCC located the runtimes with:

```sh
/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc -print-file-name=libasan.so
/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc -print-file-name=libubsan.so
```

Both resolved beneath
`/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64`. Reruns used:

```sh
/usr/bin/timeout 90s /usr/bin/env -i PATH=/usr/bin:/bin \
  PYTHONDONTWRITEBYTECODE=1 \
  LD_LIBRARY_PATH=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64 \
  ASAN_OPTIONS=detect_leaks=0:halt_on_error=1 \
  UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1 \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  reviewer_checks.py "$PWD/reviewer_emberc_san"

/usr/bin/timeout 30s /usr/bin/env -i PATH=/usr/bin:/bin \
  LD_LIBRARY_PATH=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64 \
  ASAN_OPTIONS=detect_leaks=0:halt_on_error=1 \
  UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1 \
  ./reviewer_vm_san
```

Both corrected runs exited 0, repeated all 30 reviewer assertions, and emitted
no ASan or UBSan diagnostic. LeakSanitizer was deliberately disabled; no fuzz
campaign was run and no validation label is inferred.

## Archive, provenance, and disclosure checks

```sh
/usr/bin/timeout 30s /usr/bin/env -i PATH=/usr/bin:/bin \
  PYTHONDONTWRITEBYTECODE=1 \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  CANDIDATE/sealed/reference_tests/verify_pack.py
sha256sum CANDIDATE/PROVENANCE.json CANDIDATE/MANIFEST.yaml
find CANDIDATE ! -type f ! -type d -print
find CANDIDATE -type d \( -name build -o -name __pycache__ \) -print
find CANDIDATE -type f \( -name '*.o' -o -name '*.pyc' \) -print
```

The submitted verifier exited 0 with six `PASS` lines. The three `find`
commands printed nothing. Observed hashes were:

```text
3dc7fc913794fd6c9205f6d0588d0a9c4370fb639ae6991b97b4f28aaff9d57a  CANDIDATE/PROVENANCE.json
65467d58c5d0aafa3bcc9160d5ebb6aa7a78416e57137d07672277ff4dea4586  CANDIDATE/MANIFEST.yaml
```

A separate ephemeral archive harness independently checked identifiers,
digests, status labels, entry types, absence of build debris, and four limited
credential patterns. It also copied the immutable candidate and confirmed that
the submitted verifier rejected an unexpected top-level directory, a nested
symlink, a symlink replacing a required file, a FIFO, a credential-like fake
fixture, and a modified manifest:

```sh
/usr/bin/timeout 60s /usr/bin/env -i PATH=/usr/bin:/bin \
  PYTHONDONTWRITEBYTECODE=1 \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  reviewer_pack_checks.py
```

Exit 0: `independent reviewer archive assertions: 16 passed`.

Manual disclosure review confirmed that the learner instructions point to
requirements/concepts first and identify `sealed/` as validator-owned. The
full submitted archive nevertheless includes all sealed answers and oracle
material. No actual learner projection or transfer evidence was available.

Manual license review found a clear internal boundary: catalog metadata is
recorded as CC0-1.0, linked-resource licensing is `NOASSERTION`, and copying of
linked material is denied. The immutable source object and upstream resource
were unavailable, so those provenance assertions could not be independently
traced.

## Claim-integrity result and limitations

`CANDIDATE/sealed/reference_tests/README.md:19-21` asserts that the same checks
run in a documented sanitizer rerun. `CANDIDATE/VALIDATION.md:219-222` instead
states that no sanitizer was run in generation 2 and that prior-generation
results are not reused. This contradiction is the basis for the `REVISE`
verdict; the reviewer's later sanitizer check does not repair submitted prose.

Network/source-history validation, cross-platform and cross-compiler runs,
fuzzing, benchmarking, leak detection, learner transfer, and production review
were not performed. Configured Java, Arm cross-compilers, QEMU, GLib, Node, Go,
AArch64, NASM, flex, and bison were not needed for this C/Python artifact.

## Cleanup and review-artifact validation

The resolved scratch path was confirmed to end in
`attempt-001/REVIEW_SCRATCH`, then the disposable copy and its build products
were removed with a depth-first `find ... -delete`. `CANDIDATE/` was not a
cleanup target.

The final schema check parsed `EVALUATION.json`, required exactly
`builder_job_id`, `checks_run`, `evidence`, `limitations`, `project_id`, and
`verdict`, checked the configured identifiers and verdict enum, and confirmed
that both Markdown reports were nonempty. It exited 0 with:

```text
review artifact schema/content checks: PASS
```

The only retained files created by this review are `EVALUATION.json`,
`REVIEW.md`, and `VALIDATION.md`.
