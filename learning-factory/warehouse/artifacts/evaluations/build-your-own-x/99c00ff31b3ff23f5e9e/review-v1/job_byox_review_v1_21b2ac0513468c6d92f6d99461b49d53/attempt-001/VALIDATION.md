# Independent validation record

Date: 2026-08-31 (America/Chicago).

`CANDIDATE/` was inspected read-only. Builds and runtime tests used a writable
`.review-work` copy, which was removed after testing. The composite SHA-256 over
the sorted submitted-file hashes was unchanged before and after review:

```text
d1b07dee3bdffd96cb9bd9b3afe35bf63032ab55c75358e93d1793031b9fa122
```

The job's login shell emitted three harmless user/group lookup warnings before
many commands; those warnings are host setup noise, not candidate output.

## Environment and submitted structure

Commands:

```bash
python3 CANDIDATE/environment/check_environment.py
python3 CANDIDATE/environment/verify_artifact.py
find CANDIDATE -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum
```

All returned 0. Observed environment: GCC 8.5.0, GNU Make 4.2.1, Python 3.6.8,
x86_64. The candidate verifier reported 23/23 required paths, no forbidden or
special paths, exact expected metadata, and no credential-pattern match. The
last command produced the composite digest above. Independent traversal found
40 regular files and no symlinks or special files.

## Clean-copy builds and supplied suites

Commands:

```bash
cp -a CANDIDATE .review-work
chmod -R u+w .review-work
make -C .review-work/starter clean all
make -C .review-work/sealed/reference clean all

cd .review-work
python3 public_tests/test_public.py
MICA_BIN=sealed/reference/mica python3 public_tests/test_public.py
MICA_BIN=sealed/reference/mica python3 sealed/reference_tests/test_reference.py
make -C sealed/reference check
```

Both builds returned 0 with `-std=c11 -O2 -Wall -Wextra -Wpedantic -Werror`.
Observed suite results:

- Starter baseline: status 1; 7 ran, 2 passed, 5 failed with the documented
  unfinished-stage diagnostic.
- Public suite on reference: status 0; 7/7 passed.
- Sealed suite on reference: status 0; 14/14 passed.
- Makefile wrapper: status 0; the same 14/14 passed.

The builder's recorded results are reproducible, but these candidate-authored
suites are corroboration rather than self-proving validation labels.

## Reviewer-authored functional checks

A temporary deterministic Python harness was run with:

```bash
python3 .review-independent.py
```

It returned 0 and printed `independent-checks: 10/10 passed`. The harness was
review-only and removed with the scratch copy. Its groups covered:

- CLI status/stream behavior and I/O failure;
- token normalization, positions, comments, and malformed bytes;
- source bytes at 1,048,576 and 1,048,577;
- source-order declarations and skipped declaration storage;
- 256 and 257 variables;
- expression-tree and syntactic nesting at 128 and 129;
- 65,536 and the first excess AST node;
- 160 expressions generated with seed `741913`, compared to an independent
  Python two's-complement/division oracle and linked native output;
- nested terminating `while`/`if` control flow with independently calculated
  output `247`;
- deterministic assembly and an invalid output-path error.

This deterministic corpus is not coverage-guided fuzzing, and no `FUZZED` claim
is made.

## Native smoke and optimization variants

Commands:

```bash
sealed/reference/mica compile sealed/reference/examples/fibonacci.mica -o environment/.review-smoke/fib.s
cc -no-pie environment/.review-smoke/fib.s -o environment/.review-smoke/fib
environment/.review-smoke/fib

cc -Isealed/reference/include -std=c11 -O0 -g -Wall -Wextra -Wpedantic -Werror -o environment/mica-o0 sealed/reference/src/mica.c
MICA_BIN=environment/mica-o0 python3 sealed/reference_tests/test_reference.py

cc -Isealed/reference/include -std=c11 -O3 -DNDEBUG -Wall -Wextra -Wpedantic -Werror -o environment/mica-o3 sealed/reference/src/mica.c
MICA_BIN=environment/mica-o3 python3 public_tests/test_public.py
```

All returned 0. Fibonacci stdout was:

```text
0
1
1
2
3
5
8
13
21
34
```

The O0 sealed suite passed 14/14 and the O3 public suite passed 7/7.

## Contract failure found independently

The reference was invoked with no arguments while stdout/stderr and status were
captured. Observed:

```text
returncode=2
stdout=''
stderr='usage: mica tokens FILE\n       mica run FILE\n       mica compile FILE -o OUTPUT.s\n'
stderr_lines=3
```

This fails `REQUIREMENTS.md:91-93`, which includes usage failures in the
one-line `mica: <phase> error:` rule. Static inspection found the same usage
function in the starter. The public and sealed suites have no invalid-usage
test.

A separate lexical probe containing byte `0x0b` between `print` and `1`
returned 1 with:

```text
mica: lexical error: 1:6: unexpected byte 0x0b
```

This exposes the normative document's unspecified meaning of “Whitespace”; it
does not by itself establish which behavior should be chosen.

## Isolation, integrity, and provenance probes

Command and observed modes:

```bash
stat -c '%A %a %n' \
  CANDIDATE/starter/src/mica.c \
  CANDIDATE/public_tests/test_public.py \
  CANDIDATE/sealed/reference/src/mica.c \
  CANDIDATE/sealed/reference_tests/test_reference.py
```

All four were `-r--r--r-- 444`; a direct read test of the sealed reference
returned 0. No external learner-view projection was available to validate.

In the disposable copy, the following four files were moved outside the
artifact before rerunning its verifier, then restored:

```text
starter/src/mica.c
public_tests/test_public.py
sealed/reference/src/mica.c
sealed/reference_tests/test_reference.py
```

`python3 environment/verify_artifact.py` still returned 0 and reported 23/23
required paths. Thus that script does not validate operational completeness.

Independent digest observations were:

```text
PROVENANCE.json file SHA-256:       6992abe93cba117def298c113e4277009b9c29d7ee93ff6bad71e8618d17972d
canonical JSON SHA-256:             89e2d6b2fddf6b8cd2a643e8f9290374bad176c3bc446ecbd23a7f9b21358808
manifest provenance_sha256:         16c1f2fa7154cfbf9531c6d77cf7024fd08511e5def5b6488d364f550056629b
provenance internal snapshot_sha256:16c1f2fa7154cfbf9531c6d77cf7024fd08511e5def5b6488d364f550056629b
```

Independent pattern searches found no credential-shaped text, C process-launch
APIs, Python `shell=True`, or non-regular filesystem entries. No standalone
license-grant file was present.

## Unavailable checks and other limits

Attempted command:

```bash
cc -Isealed/reference/include -std=c11 -O1 -g -Wall -Wextra -Wpedantic -Werror \
  -fsanitize=address,undefined -fno-omit-frame-pointer \
  -o environment/mica-sanitized sealed/reference/src/mica.c
```

It returned 1 because the linker could not find
`/usr/lib64/libasan.so.5.0.0` and `/usr/lib64/libubsan.so.1.0.0`. `clang`,
`valgrind`, `cppcheck`, and `scan-build` were not installed. A non-login shell
could identify `cc` but could not execute `cc1`; the job's normal login shell
built successfully.

Network and the recorded upstream checkout were unavailable, so upstream
license evidence, commit contents, and independent-generation/no-copy claims
were not verified. Checks ran on one GCC/x86-64 host only. No sanitizer,
cross-platform, benchmark, production, or transfer-validation conclusion is
claimed.
