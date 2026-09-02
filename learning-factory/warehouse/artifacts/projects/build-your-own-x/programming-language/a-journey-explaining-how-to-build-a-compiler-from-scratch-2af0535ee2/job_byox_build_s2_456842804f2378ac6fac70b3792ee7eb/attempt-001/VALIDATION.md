# Validation record

Validation date: 2026-09-02 (America/Chicago). All commands ran from the repository root in the allocated workspace. Shell startup also printed harmless `id: cannot find name for user/group ID` warnings because the container’s numeric identity has no name mapping; those warnings were outside the invoked programs.

The authoritative artifact status remains `GENERATED` + `PARTIAL`. These observations do not grant `BUILDS`, `TESTED`, `FUZZED`, `BENCHMARKED`, `REVIEWED`, `TRANSFER_VERIFIED`, or `PRODUCTIONIZED`; the learning-factory’s independent validator controls those labels.

## Environment

Command:

```sh
python3 environment/check_environment.py
```

Observed exit 0 and:

```text
environment check: PASS
compiler: cc (GCC) 8.5.0 20210514 (Red Hat 8.5.0-22)
make: GNU Make 4.2.1
python: 3.6.8 (default, Apr 25 2024, 09:54:46)
C11 int64_t compile/run probe: PASS
```

No network or upstream repository access was attempted. There are no third-party dependencies.

## Ordinary builds and tests

Commands:

```sh
make -C starter clean all
make -C sealed/reference clean all
python3 public_tests/run_tests.py --binary sealed/reference/build/sprig
python3 sealed/reference_tests/run_tests.py --binary sealed/reference/build/sprig
make -C sealed/reference_tests clean test
```

Observed:

- Both C implementations compiled and linked with `-std=c11 -Wall -Wextra -Wpedantic -Werror -O2`; exit 0 and no compiler diagnostics.
- Public suite against the sealed reference: 10 tests run, all `OK`, exit 0.
- Sealed black-box suite: 19 tests run, all `OK`, exit 0. This includes exact nesting, instruction, variable, source-size, numeric, and VM-stack boundaries.
- Direct malformed-bytecode suite: `10 VM safety tests passed`, exit 0.

The intentional starter baseline was also observed with:

```sh
python3 public_tests/run_tests.py --binary starter/build/sprig
```

It exited 1: 10 tests ran, the empty-program and token-mode tests passed, and the remaining 8 failed at the explicit compiler stub. This is the expected progressively revealable starting state, not a passing implementation claim.

After the final ordinary confirmation, scratch binaries and objects were removed with:

```sh
make -C starter clean
make -C sealed/reference clean
make -C sealed/reference_tests clean
```

## Informative failed attempts

The first direct VM test used C `tmpfile()`:

```sh
make -C sealed/reference_tests test
```

It exited 2 after reporting `tmpfile unavailable` for all 10 cases. This sandbox does not provide a usable C temporary-file location. The fixture was changed to a named scratch file under `sealed/reference_tests/build/`, closed and removed after every case; the same test then passed as recorded above. No VM defect was implicated by the first failure.

An undefined-behavior sanitizer build was attempted with:

```sh
make -C sealed/reference clean all CFLAGS='-std=c11 -Wall -Wextra -Wpedantic -Werror -O1 -g -fsanitize=undefined -fno-sanitize-recover=undefined'
UBSAN_OPTIONS=halt_on_error=1 python3 sealed/reference_tests/run_tests.py --binary sealed/reference/build/sprig
make -C sealed/reference_tests clean test CFLAGS='-std=c11 -Wall -Wextra -Wpedantic -Werror -O1 -g -fsanitize=undefined -fno-sanitize-recover=undefined'
```

Both sanitizer links failed with `/usr/bin/ld: cannot find /usr/lib64/libubsan.so.1.0.0`; the Python command consequently reported that the binary did not exist. No sanitized tests ran, and no sanitizer result is claimed. The normal build was restored and revalidated afterward.

## Harness smoke checks

The timing harness was executed only to verify its workload and output checks:

```sh
python3 benchmarks/run_benchmark.py --binary sealed/reference/build/sprig --iterations 1 --warmup 0
```

It exited 0 with one observed sample and median of `0.005655542016029358` seconds for “60 bindings and 190 print statements.” A single unwarmed sample on this shared host is not benchmark evidence and supports no `BENCHMARKED` label.

The deterministic corpus generator was run through a Python `TemporaryDirectory` under the workspace, using the argument array `['python3', 'adversarial/generate_cases.py', target]`. It exited 0, reported `generated 10 cases`, and a file count confirmed 10. The scoped directory was removed automatically afterward.

## Metadata and archive audit

`MANIFEST.yaml` and `PROVENANCE.json` were loaded with Python’s strict JSON parser. Observed raw SHA-256 values were:

```text
MANIFEST.yaml    d790bd7487c566f570a0207bb94f3cf1d2af4815acb04f3d14153bde62600c8e
PROVENANCE.json  db3da454c4b0e7f852e59a264c6e2296b2dd561c35ca2b5bf5f8f9b04d127169
```

The manifest values were confirmed as `status=GENERATED`, `validation_labels=[GENERATED, PARTIAL]`, and `productionized=false`; its object and the provenance object contain the authoritative values supplied for this job with no extra fields.

A shell loop checked every authoritative required path with `test -f`, every forbidden path with `test -e`, and generated path types with:

```sh
find . \( -path './.agents' -o -path './.codex' -o -path './.factory-workspace' \) -prune -o -mindepth 1 ! -type f ! -type d -print
```

Observed: `required_files=23 missing=0`, `forbidden_paths_present=0`, and `generated_special_files_or_symlinks=0`. Pre-existing factory marker directories were pruned and not inspected.

A recursive filename-only credential scan of generated files (excluding factory markers and scratch `build/` directories) looked for private-key headers, AWS-style access identifiers, GitHub/OpenAI-style tokens, and assigned password/API-key/client-secret values. Observed: `credential_pattern_matches=0`.

Benchmarking, fuzzing, transfer testing, security review, and production hardening remain incomplete. Independent validation is mandatory.
