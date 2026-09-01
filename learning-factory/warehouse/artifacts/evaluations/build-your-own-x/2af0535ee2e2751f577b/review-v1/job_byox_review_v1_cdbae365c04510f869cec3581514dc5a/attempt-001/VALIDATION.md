# Independent validation record

## Scope and method

`CANDIDATE/` was treated as immutable. Its files were initially mode `0444`; builds and temporary
review harnesses ran only in a writable copy created as follows:

```sh
review_scratch=$(mktemp -d -p "$PWD" .review-scratch.XXXXXX)
SCRATCH="$review_scratch/candidate"
cp -a CANDIDATE "$SCRATCH"
chmod -R u+w "$SCRATCH"
```

Candidate executions and submitted test suites had outer timeouts. Simple inventory and compiler
commands were run directly. The scratch copy and reviewer harnesses were removed after evidence
collection with:

```sh
find "$review_scratch" -depth -delete
```

## Environment

```sh
cc --version | sed -n '1,2p'
make --version | sed -n '1,2p'
python3 --version
command -v clang || true
command -v valgrind || true
```

Observed:

- GCC/`cc` 8.5.0 (Red Hat 8.5.0-22)
- GNU Make 4.2.1
- Python 3.6.8
- `clang` and `valgrind` absent
- The shell emitted numeric account-name lookup warnings before commands; exit statuses were
  unaffected.

`rg` was also absent, so bounded searches used `find` and `grep`.

## Inventory, integrity, and metadata

```sh
find CANDIDATE -type f | wc -l
find CANDIDATE -type l | wc -l
find CANDIDATE -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum
```

Observed both before and after validation: 52 regular files, 0 symlinks, aggregate listing digest
`fb256cf3559e3ffa37c70424e1d759d4fa0a603c5299fcf08191f8c50c4c121c`.

An independent strict-JSON parse of `MANIFEST.yaml` and `PROVENANCE.json` found matching project ID,
source ID, and source commit. Hash observations were:

```text
PROVENANCE.json byte SHA-256:      faadfb8f39cea41f1cee79a7f44a3845c4ceceda6b2bfbe473bcac96836a94ae
PROVENANCE canonical JSON SHA-256: b1a0bbc2feaff012132039bd8ded15748d618243b357b1c01dc32fbcd02d9fe0
manifest provenance_sha256:       a352640b7e055e83e7c856a44576b2a3b92ed775ecb1d881d399163221097a16
embedded snapshot_sha256:         a352640b7e055e83e7c856a44576b2a3b92ed775ecb1d881d399163221097a16
```

No `LICENSE`, `COPYING`, SPDX identifier, or conventional permission grant was found for the
generated material.

The submitted structural audit was also executed as an observation, not accepted as independent
proof:

```sh
timeout 30s python3 CANDIDATE/environment/audit_repository.py
```

Exit 0: it reported 23 required paths present, 21 forbidden paths absent, only regular
files/directories, matching manifest/provenance objects, and no credential-like pattern.

## Builds and submitted checks

Commands below use `$SCRATCH` as shorthand for the writable candidate copy.

```sh
timeout 60s make -C "$SCRATCH/starter" clean all
timeout 60s make -C "$SCRATCH/starter" test
```

The starter clean build exited 0 with C11, `-Wall -Wextra -Wpedantic -Werror -O2`. Its test target
exited 2: 11 tests ran, 9 failed and 2 passed. Every failure was consistent with the documented
`compiler not implemented` placeholder.

```sh
timeout 120s make -C "$SCRATCH/sealed/reference" clean all test
```

Exit 0. Observed 11/11 public tests, 18/18 sealed boundary tests, and `api_test: 16 checks passed`.

```sh
timeout 60s env PEBBLE_BIN="$SCRATCH/sealed/reference/build/pebble" \
  python3 "$SCRATCH/adversarial/test_adversarial.py"
```

Exit 0; 7/7 deterministic adversarial test methods passed. This was a fixed corpus, not fuzzing.

The three exercise C fragments were independently compiled with the same strict warning flags; all
three compilations exited 0.

## Independent semantic and API checks

An inline Python driver invoked the reference executable with argv arrays, captured streams, and a
five-second per-case timeout. Results:

```text
mixed precedence:       PASS, rc=0,  stdout='1\n',    stderr=''
nested short circuit:   PASS, rc=0,  stdout='1\n1\n', stderr=''
shadow restoration:     PASS, rc=0,  stdout='5\n2\n', stderr=''
negative arithmetic:    PASS, rc=0,  stdout='-2\n-1\n1\n', stderr=''
compile atomicity:      PASS, rc=65, stdout='', diagnostic at 1:24
```

A second deterministic driver tested the Cartesian product of these ten values:

```text
INT64_MIN, INT64_MIN+1, -3037000500, -2, -1, 0, 1, 2, 3037000500, INT64_MAX
```

with `+`, `-`, `*`, `/`, and `%`. It independently computed mathematical overflow and C11
truncate-toward-zero quotient/remainder expectations, then checked exit class and exact output:

```text
arithmetic matrix: 500 checks, 0 failures
```

An independently authored C harness was compiled directly with the submitted reference source:

```sh
timeout 60s cc -std=c11 -Wall -Wextra -Wpedantic -Werror -O2 \
  -I"$SCRATCH/sealed/reference/include" independent_api.c \
  "$SCRATCH/sealed/reference/src/pebble.c" -o independent_api
timeout 20s ./independent_api
```

It checked compile publication atomicity, repeat execution, stack/step/constant/symbol limits, exact
output, and null API arguments. Exit 0: `independent_api: 18 checks, 0 failures`.

## Independent failure probes

### Embedded NUL and non-regular input

An inline Python driver wrote the exact bytes `print 1;\x00print 2;` to a named scratch file and ran
the reference in file mode. Observed:

```text
rc=0 stdout='1\n' stderr=''
```

The trailing bytes were silently ignored. The same driver ran the reference on `/dev/null`:

```text
rc=0 stdout='' stderr=''
```

Thus the implementation does not reject special files as required by its own documented boundary.

### Parser depth

The driver generated `print `, then *N* opening parentheses, `1`, *N* closing parentheses, and `;`.
Each subprocess had a five-second timeout:

```text
N=128:    rc=0,   stdout='1\n'
N=1024:   rc=0,   stdout='1\n'
N=4096:   rc=0,   stdout='1\n'
N=16384:  rc=-11, no output or diagnostic (SIGSEGV)
```

The failing source was valid and only 32,776 bytes.

### Lexer exercise

An independent probe passed non-NUL-terminated arrays of exact lengths 1–4 to the submitted
`classify_name` function. Built with `-O2 -D_FORTIFY_SOURCE=2`, it exited 0 and printed:

```text
l=1 le=1 let=1 lets=0
```

Here 1 is `TOKEN_LET`. This confirms the short-prefix classification bug. Static C-library semantics
show that `strncmp(..., length)` examines at most the slice length and stops at NUL, so the prompt's
additional out-of-bounds claim is not supported.

## Rebuild and unavailable instrumentation

Two same-path clean reference builds were hashed:

```text
first  = 5dc3961e052a5aa3f71bd4ef5b938f736700c035d1c42b8fddfba27f6ce49de5
second = 5dc3961e052a5aa3f71bd4ef5b938f736700c035d1c42b8fddfba27f6ce49de5
match  = yes
```

This is limited same-host evidence, not a reproducible-build certification.

The independent sanitizer attempt was:

```sh
timeout 60s cc -std=c11 -Wall -Wextra -Wpedantic -Werror -O1 -g \
  -fsanitize=address,undefined -I"$SCRATCH/sealed/reference/include" \
  "$SCRATCH/sealed/reference/src/main.c" "$SCRATCH/sealed/reference/src/pebble.c" \
  -o pebble-sanitized
```

It exited 1 at link time: `/usr/lib64/libasan.so.5.0.0` and
`/usr/lib64/libubsan.so.1.0.0` were not found. No sanitizer result is claimed.

## Limitations and non-claims

- No network or out-of-scope upstream source was accessed. The catalog license evidence, linked-work
  originality boundary, and no-copy claim remain unverified.
- No student-view artifact or transfer harness was supplied, so disclosure isolation was not
  transfer-verified.
- No clang, valgrind, sanitizer runtime, alternate platform/compiler, allocation-failure injector, or
  concurrency harness was available.
- The benchmark harness was not run because it makes no result claim and lacks a bounded child
  timeout. No random or coverage-guided fuzzing was performed.
- Passing submitted scripts is recorded only as an observation. This review does not promote the
  manifest or assert any validation label.
