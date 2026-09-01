# Local repair validation record

Status remains **GENERATED + PARTIAL**. These are repair-worker observations,
not independent evidence and not authorization for `BUILDS`, `TESTED`,
`FUZZED`, `BENCHMARKED`, `REVIEWED`, `TRANSFER_VERIFIED`, or
`PRODUCTIONIZED` labels.

Validation was performed in the allocated repair workspace on 2026-08-31.
`PRIOR_BUILD/` and `PRIOR_REVIEW/` were inspected but not modified. The linked
tutorial and source repository were not fetched or inspected. No student
workspace was created.

The command wrapper printed numeric user/group lookup warnings before commands.
Those wrapper messages are omitted from excerpts below and did not change the
reported command statuses.

## Host tools observed

Exact commands:

```sh
cc --version | sed -n '1p'
make --version | sed -n '1p'
python3 --version
timeout --version | sed -n '1p'
```

Observed exit 0 for each and:

```text
cc (GCC) 8.5.0 20210514 (Red Hat 8.5.0-22)
GNU Make 4.2.1
Python 3.6.8
timeout (GNU coreutils) 8.30
```

## Permanent public contract and one-time scaffold smoke

Exact commands, using an empty workspace-local `.repair-tmp` because global
temporary directories are not reliable in this sandbox:

```sh
env TMPDIR="$PWD/.repair-tmp" PYTHONDONTWRITEBYTECODE=1 LC_ALL=C \
  python3 -m unittest discover -s public_tests -v
env TMPDIR="$PWD/.repair-tmp" PYTHONDONTWRITEBYTECODE=1 LC_ALL=C \
  python3 public_tests/scaffold_smoke.py -v
```

Both commands exited 0. The permanent suite reported `Ran 9 tests in 0.426s`
and `OK`; the isolated pristine-scaffold smoke reported `Ran 1 test in 0.343s`
and `OK`. The permanent suite contains no expected TODO message. The separate
smoke is intentionally not discovered by the permanent suite and ceases to be
applicable when learner implementation begins.

## Sealed reference and repair regressions

Exact full-suite command:

```sh
timeout --signal=TERM --kill-after=5s 90s \
  env TMPDIR="$PWD/.repair-tmp" PYTHONDONTWRITEBYTECODE=1 LC_ALL=C \
  python3 sealed/reference_tests/test_reference.py -v
```

Observed exit 0, `Ran 53 tests in 3.312s`, and `OK`. The suite performed its
own clean warning-as-error C11 build and includes the two repair regressions.

The independently reported foreground continuation and closed-stdin commands
were also rerun directly after a strict build:

```sh
timeout --signal=TERM --kill-after=1s 4s sealed/reference/minish -c \
  "sh -c 'kill -STOP \$\$; sleep 0.30' | sh -c 'sleep 0.05; kill -CONT 0; sleep 0.10'"
timeout --signal=TERM --kill-after=1s 2s sealed/reference/minish <&-
```

Each exited 0 with no output. The first previously returned stale stop status
147; the repaired foreground waiter requests continued events and drains an
already-pending continuation before accepting a stopped aggregate. The second
now treats closed fd 0 as `/dev/null` EOF because standard descriptors are
reserved before the signal self-pipe is created.

Two consecutive clean reference builds were run with:

```sh
make -C sealed/reference clean all >/dev/null
sha256sum sealed/reference/minish
make -C sealed/reference clean all >/dev/null
sha256sum sealed/reference/minish
```

Both binary observations were:

```text
cc368d4770ce4f2a9a08106695045566c76fedc182b3e5b767d18b04158bba57  sealed/reference/minish
```

This same-path repeat is reproducibility evidence only; it is not a portable or
independently authenticated build claim.

## Public milestone harness

The public C probes were compiled strictly, and executable milestone checks
were exercised against the completed sealed binary without copying it into the
learner tree:

```sh
timeout --signal=TERM --kill-after=2s 25s \
  env TMPDIR="$PWD/.repair-tmp" PYTHONDONTWRITEBYTECODE=1 LC_ALL=C \
  PYTHONPATH=public_tests python3 -c \
  'from pathlib import Path; import run_milestone as m; m.BINARY=Path("sealed/reference/minish").resolve(); [m.CHECKS[name]() for name in ("process", "descriptor", "job", "terminal")]; print("completed-reference milestone checks: process descriptor job terminal: PASS")'
cc -std=c11 -Wall -Wextra -Wpedantic -Werror -Istarter/include \
  -fsyntax-only public_tests/milestones/lexer_probe.c \
  public_tests/milestones/parser_probe.c
```

Both commands exited 0. The first printed
`completed-reference milestone checks: process descriptor job terminal: PASS`;
the strict probe compile was silent. The pristine starter was then checked with:

```sh
env TMPDIR="$PWD/.repair-tmp" PYTHONDONTWRITEBYTECODE=1 LC_ALL=C \
  python3 public_tests/run_milestone.py lexer
```

Observed exit 1 and `milestone lexer: FAIL` with the expected initial
`tokenization is a TODO` diagnostic. This expected failure confirms that a
milestone does not falsely pass before its stage is implemented. A modular
completed learner library was not available, so successful lexer/parser probe
execution remains for learner or independent-validator runs.

## Adversarial and benchmark harness smoke

Exact commands:

```sh
timeout --signal=TERM --kill-after=5s 80s \
  env TMPDIR="$PWD/.repair-tmp" PYTHONDONTWRITEBYTECODE=1 LC_ALL=C \
  python3 adversarial/run.py --timeout 5 --max-output 800 \
  sealed/reference/minish
timeout --signal=TERM --kill-after=2s 30s \
  env TMPDIR="$PWD/.repair-tmp" PYTHONDONTWRITEBYTECODE=1 LC_ALL=C \
  python3 benchmarks/run.py --iterations 1 --warmup 0 --timeout 5 \
  sealed/reference/minish
```

Both exited 0. All ten adversarial cases were labelled
`completed(status=0)`; the corpus has no oracle and does not support a `FUZZED`
claim. The one-sample benchmark smoke observed:

```text
workload                 median ms     p95 ms     min ms     max ms
builtin_pwd                   2.184      2.184      2.184      2.184
builtin_list_20               2.243      2.243      2.243      2.243
external_true                 2.563      2.563      2.563      2.563
pipeline_128k                 3.069      3.069      3.069      3.069
pipeline_8                    3.853      3.853      3.853      3.853
background_burst              2.784      2.784      2.784      2.784
```

These volatile single samples are not a baseline and do not support a
`BENCHMARKED` label.

## Exercise-source checks

Exact command:

```sh
find debugging review_exercises -type f -name '*.c' -print | sort | \
  while IFS= read -r source_path; do
    cc -std=c11 -Wall -Wextra -Wpedantic -Werror \
      -fsyntax-only "$source_path" || exit 1
  done
```

Observed exit 0 for all eight buggy/fixed C sources. This checks compilation,
not the intended behavioral diagnoses.

## Machine-enforced views, inventory, and package contract

`environment/VIEW_POLICY.json` supplies an exact default-deny learner
allowlist. The verifier walks only declared artifact roots, rejects non-regular
objects and build products, checks all 23 required paths and all 21 forbidden
paths, content-checks the immutable metadata files, searches high-confidence
credential patterns, and compares learner files against full sensitive-file
hashes and 512-byte sensitive fragments. Exact commands:

```sh
env PYTHONDONTWRITEBYTECODE=1 python3 tools/view_integrity.py verify
env PYTHONDONTWRITEBYTECODE=1 python3 tools/test_view_integrity.py -v
sha256sum ARTIFACT_INVENTORY.json environment/VIEW_POLICY.json
```

All commands exited 0. Verification printed:

```json
{"credential_pattern_findings": 0, "learner_file_count": 26, "learner_sha256": "d7bd60f36ed8e69d9e3cfc5fd8705bb05b98712a9183c8c87a0a6cc84b45f8f2", "required_path_count": 23, "sensitive_fragment_collisions": 0, "sensitive_hash_collisions": 0, "validator_file_count": 74, "validator_payload_sha256": "9bd92b6d6f9c2e4e949df801afc7aa4ac415799357b324dad49f37885aad00af"}
```

The isolation suite reported `Ran 4 tests in 0.231s` and `OK`. File hashes were:

```text
781d4405cb00dd73e385a49174e09b0639d48c1d5a00bf1ea3c722b73573856e  ARTIFACT_INVENTORY.json
512c2b4ebbaa522f7c0df1c348abc4761f7a8c0caa5403766bf2df5e5ed5a28b  environment/VIEW_POLICY.json
```

`ARTIFACT_INVENTORY.json` records generator/job identity, a per-file payload
inventory, and separate learner/validator digests. It explicitly excludes
itself and this mutable validation narrative to avoid a circular self-hash.
The immutable `PROVENANCE.json` machine-local `source.path` is explicitly
classified there as historical metadata, not a dependency or reproduced path.

The verifier's `export-learner` action uses the same allowlist, requires a new
destination, and rehashes each copied file. It was deliberately **not invoked**:
the authoritative repair task forbids this worker from creating a student
workspace. Therefore the virtual/export-source boundary was checked, but no
claim of independently validated exported bytes is made.

Preservation of the prior pack was checked separately with:

```sh
python3 -c 'from pathlib import Path; prior=Path("PRIOR_BUILD"); expected=sorted(p.relative_to(prior) for p in prior.rglob("*") if p.is_file()); missing=[str(p) for p in expected if not Path(p).is_file()]; assert not missing, missing; print("prior_regular_files_preserved={} missing=0".format(len(expected)))'
```

Observed exit 0 and `prior_regular_files_preserved=68 missing=0`.

## Informative unavailable check

Exact AddressSanitizer probe:

```sh
timeout --signal=TERM --kill-after=2s 30s \
  cc -std=c11 -Wall -Wextra -Wpedantic -O0 -g \
  -fsanitize=address -fno-omit-frame-pointer \
  debugging/token_vector/sealed/fixed.c -o .repair-tmp/asan-fixed
```

Observed exit 1; no output binary was produced. The linker reported:

```text
/usr/bin/ld: cannot find /usr/lib64/libasan.so.5.0.0
collect2: error: ld returned 1 exit status
```

No sanitizer, leak, fuzzer, syscall-fault-injection, cross-platform, external
license, production-readiness, or independent acceptance claim is made. The
repair job also supplied no authority to add a redistribution license, so the
generated-material license limitation remains explicit in
`LICENSE_BOUNDARY.md`.
