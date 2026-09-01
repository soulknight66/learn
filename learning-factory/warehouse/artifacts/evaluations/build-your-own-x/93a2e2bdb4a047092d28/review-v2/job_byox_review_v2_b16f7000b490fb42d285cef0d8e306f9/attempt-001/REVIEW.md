# Independent review

Verdict: **REVISE**. The reference is a useful teaching-sized implementation and behaved well in the bounded checks that could run, but the submitted archive is incomplete and breaks its own progressive-disclosure boundary. It should not be promoted to any validation lifecycle label.

## Prioritized findings

### 1. Blocker — the submitted artifact graph contradicts the README and manifest

`README.md` advertises `scripts/run_all.py`, `production/implementation`, and `production/PRODUCTIONIZATION.md`. None exists. `MANIFEST.yaml` nevertheless says there are two alternatives and an instrumented variant. As observed independently:

- the aggregate runner exits 2 because `scripts/run_all.py` is absent;
- both production-target unit suites and all four production-target adversarial/debug commands fail with `ModuleNotFoundError`;
- benchmark regeneration runs the reference portion, then exits 1 because `production/implementation/kvstore.py` is absent.

Consequently, `benchmarks/results/smoke.json` is not reproducible from the submission. Its arithmetic is internally consistent, but candidate-supplied JSON and the provenance phrase “created by validator” are not independent BENCHMARKED evidence.

Required resolution: either include the advertised implementation, productionization note, runner, and fresh harness-controlled evidence, or remove every stale path, artifact flag, comparison, and production measurement and provide a coherent reference-only workflow.

### 2. High — the unsealed debugging fixture reveals the sealed solution

`debugging/lost-delete/buggy/kvstore.py` and `sealed/reference/kvstore.py` differ by exactly one source line: replaying a delete is changed from `self._data.pop(key, None)` to `pass`. Thus nearly the entire reference implementation is available outside `sealed/`, despite `README.md` saying references and deeper material are revealed intentionally.

This defeats progressive disclosure for the main build exercise. Use a smaller, independent debugging fixture that does not duplicate the solution, or gate the whole debugging exercise until after the main implementation phase.

### 3. High — valid logical state can exceed the compaction format

The API permits values up to 1 MiB and does not bound total state. Compaction serializes every live key into one record, while `_encode` caps a record at 4 MiB. An independent bounded probe inserted four valid 1 MiB values and observed `compact()` raise `ValueError: batch is too large`; all four keys did remain recoverable afterward.

`sealed/REVIEW.md` candidly acknowledges this, but `REQUIREMENTS.md` promises compaction without describing a capacity limit or failure mode. That leaves learners with a contract the reference cannot satisfy. Segment snapshots/compaction, define and enforce an explicit total-state limit, or specify the exception and test it publicly.

### 4. Medium — crash durability is not established and may omit first-file directory durability

For a newly created store, `_append` fsyncs the log when `sync=True`, but construction of the new directory entry is not followed by a parent-directory fsync. On filesystems requiring directory fsync for creation durability, a successful first mutation can therefore have weaker power-loss guarantees than the “durable” framing suggests.

The available recovery checks are same-process reopen tests or mocked call failures. `torn_tail.py` appends malformed bytes during an orderly process; it is not an abrupt-process or filesystem-crash test. The candidate appropriately calls this a bounded smoke, so power-loss durability remains inconclusive. Clarify that the contract covers orderly close/reopen only, or add the missing durability operation and harness-controlled subprocess/crash-boundary tests.

### 5. Medium — adversarial tools can report false success

The three adversarial scripts use bare `assert` for correctness. A `python -O` run removes those checks but still prints “passed.” The model and stress CLIs also accept empty workloads: `--operations 0` and `--threads 0` both printed “passed” in reviewer probes.

Use explicit checks that cannot be optimized away, reject non-positive work parameters, record the exact interpreter flags/seed/workload, and have a harness determine status from structured evidence.

### 6. Medium — generated-material licensing is undefined

The provenance record usefully identifies the catalog commit/reference, labels the new material agent-generated, and states that tutorial text/code was not copied. However, there is no `LICENSE`, `COPYING`, or `NOTICE` for the generated code and teaching content. `source.license: CC0-1.0` appears to describe the catalog source, not the new artifact, and no license is recorded for the linked external tutorial.

Add explicit reuse terms for generated material, scope each dependency/reference license separately, prefer a portable public source locator, and attach durable validator identifiers/hashes for measured outputs. The recorded source and no-copy statements could not be authenticated from this archive alone.

### 7. Low — the learner start is clear but not progressive in execution

The concepts, design questions, byte-oriented contract, debugging scenario, and review exercise are useful. The starter, however, presents all major methods as stubs at once. Its public run produces four errors, and unimplemented `close()` adds a second exception that can mask the original stub failure. Staged milestones/tests and a non-masking starter lifecycle would give learners clearer feedback.

## Validation posture

Positive observations are limited to CPython 3.11.5 in this workspace: source compilation, 4/4 public reference tests, 10/10 sealed reference tests, an independent core/recovery probe, the documented reference model smoke, a reference thread smoke, and the lost-delete reproduction. These results do not establish BUILDS, TESTED, FUZZED, BENCHMARKED, REVIEWED, TRANSFER_VERIFIED, or PRODUCTIONIZED. The manifest's existing `EDUCATIONAL_CANDIDATE_REQUIRES_EXTERNAL_VALIDATION` and `NOT_PRODUCTION_READY` labels are appropriately cautious.
