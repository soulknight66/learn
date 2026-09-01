# Generation-time validation

Date: 2026-08-31 (America/Chicago). Workspace: allocated attempt root. No network request was made and
the provenance link was not fetched. These are worker-observed checks, not independent factory labels.

## Environment discovery and preserved failed attempt

Command:

```bash
python3 --version
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
```

Observed: `Python 3.6.8` and `Python 3.11.5`, respectively.

The first reference-suite attempt used the unqualified interpreter:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference python3 -m unittest discover -s sealed/reference_tests -v
```

Observed exit: 1. It ran eight discovered test entries and ended `FAILED (errors=8)`. Imports failed
because Python 3.6 lacks the standard-library `dataclasses` module; CLI tests also showed that this
version's `subprocess.run` lacks the `text` argument. This is an environment/toolchain blocker, not a
claim about the reference. Learner commands now name the available Python 3.11 interpreter explicitly.

## Reference tests

Command:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest discover -s sealed/reference_tests -v
```

Observed exit: 0. `Ran 39 tests in 0.698s` followed by `OK`. The suite includes front-end positions and
grammar, lexical scopes, every arithmetic/comparison operation, signed-64 faults, generated expression
matrices, binary control-flow/stack rejection, published adversarial cases, API types, limits, and CLI
atomic-output behavior.

## Public tests against the sealed reference

Command:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest discover -s public_tests -v
```

Observed exit: 0. `Ran 13 tests in 0.453s` followed by `OK`.

An earlier cross-run of this command exited 1 with two CLI failures because the CLI test helper
overrode the selected `PYTHONPATH` with `starter`. The helper was corrected to preserve the outer
implementation selection; the final result above is from the corrected harness.

## Intentional starter state

Command:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=starter /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest discover -s public_tests
```

Observed exit: 1. `Ran 13 tests in 0.292s` and `FAILED (failures=2, errors=11)`. Failures terminate at
the documented `NotImplementedError` boundaries in lexer or bytecode validation; the two CLI assertions
likewise observe the unfinished lexer traceback. This is expected challenge incompleteness and is the
reason for the `PARTIAL` label, not a passing-test claim.

## Benchmark harness smoke run

Command:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 benchmarks/benchmark.py --iterations 3 --loop-count 100
```

Observed exit: 0 and output:

```json
{"bytecode_bytes": 88, "compile_median_ns": 229655, "iterations": 3, "loop_count": 100, "run_median_ns": 1291606}
```

This short, uncontrolled smoke result proves only that the harness executed and checked its program
output. It is not a performance baseline and does not establish `BENCHMARKED`.

## Structure, metadata, and hygiene audit

The final shell audit checked every authoritative required path with `test -e`, every forbidden path
with the same exact-path semantics, and all artifact roots with `find ... ! -type f ! -type d`. Observed
exit: 0, with:

```text
structure_status=0
non_regular_entries=0
artifact_regular_files=70
```

Python 3.11 strict-JSON parsing compared `MANIFEST.yaml` to the required object and checked the immutable
provenance snapshot field against the manifest binding. Observed exit: 0, with
`manifest_exact=true` and `provenance_manifest_binding=true`.

A filename-only recursive scan over the 70 generated files checked private-key headers, common AWS,
GitHub, OpenAI, and JWT token shapes, plus assignments to password/API-key/client-secret/access-token
names. Observed exit: 0, with `known_credential_pattern_matches=0` and
`credential_assignment_matches=0`. Pattern scanning is a hygiene check, not a formal secret-detection
guarantee.

## Final status

The generated reference and tests execute on the available toolchain, while the learner starter remains
deliberately incomplete. Independent validation is still required. `MANIFEST.yaml` therefore remains
exactly `GENERATED` + `PARTIAL`; no `BUILDS`, `TESTED`, `FUZZED`, `BENCHMARKED`, `REVIEWED`,
`TRANSFER_VERIFIED`, or `PRODUCTIONIZED` label is claimed here.
