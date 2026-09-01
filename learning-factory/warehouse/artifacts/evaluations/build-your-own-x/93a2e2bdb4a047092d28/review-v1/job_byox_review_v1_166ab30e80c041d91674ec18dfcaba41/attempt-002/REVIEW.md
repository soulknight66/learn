# Independent review: Durable Bytes KV

## Verdict

**REVISE.** The sealed reference has useful, independently reproduced behavior, but the submitted archive is internally incomplete, its production/benchmark claims cannot be reproduced, and the reference fails a stated compaction requirement for valid inputs. It should not receive a `REVIEWED`, `BENCHMARKED`, `FUZZED`, `TRANSFER_VERIFIED`, or `PRODUCTIONIZED` promotion on the basis of this submission.

## Prioritized findings

### P0 — The advertised archive and validation workflow are incomplete

`CANDIDATE/README.md:14-18,26,35-43` depends on `scripts/run_all.py`, `production/implementation/kvstore.py`, and `production/PRODUCTIONIZATION.md`. None of those paths exists. Consequently:

- the aggregate command exits 2 because its script is missing;
- both production-target unittest commands and all three production adversarial commands exit 1 because `kvstore` cannot be imported;
- the benchmark exits 1 while loading the absent production source;
- `MANIFEST.yaml:27-29` overstates the submitted artifact by declaring two alternatives and an instrumented variant.

There is also no builder `VALIDATION.md` in the submitted tree. The root README lists commands, but commands are not observed results. Repackage the complete artifact or align every manifest field, path, and command with what is actually distributed, then obtain fresh independent validation.

### P0 — The saved production benchmark is not auditable from this submission

`benchmarks/results/smoke.json:14-21,34-36` records production timings and a production/reference ratio, while the measured production source is absent. `PROVENANCE.json:10-13` calls the file validator-created but records no validator/run identity, implementation hashes, timestamp, or candidate-tree digest. This is not evidence that the submitted tree is benchmarked; it is an unsupported historical result. Preserve raw evidence only alongside the exact measured sources and immutable run provenance.

### P1 — `compact()` fails for data accepted by the public API

The reference accepts each value up to 1 MiB (`sealed/reference/kvstore.py:17-19,80-84`) but rewrites the whole database as one record capped at 4 MiB (`:86-104,222-227`). An independent probe inserted three legal 1 MiB values. The live log was 4,194,627 bytes, and `compact()` raised `ValueError: batch is too large`.

That contradicts the unconditional requirement that compaction preserve logical contents and atomically replace the log (`REQUIREMENTS.md:13`). The sealed review acknowledges the limitation, which is honest, but acknowledgment does not satisfy the contract. Either segment compaction output or state and enforce a database-size precondition in the learner-visible contract and tests.

### P1 — Progressive disclosure is advisory, not an enforced boundary

The README says learners see starter material first and solutions are revealed intentionally (`README.md:4-6`), but the same directly readable archive contains:

- `sealed/reference/kvstore.py` and `sealed/reference_tests/test_recovery.py`;
- `debugging/lost-delete/sealed/root-cause.md` and `patch.diff`;
- `review_exercises/cache-compaction/sealed/EXPECTED_REVIEW.md`.

Read-only permissions prevent edits, not disclosure. No learner-view generator, allowlist, access control, or separately delivered sealed artifact demonstrates that a learner cannot inspect answers immediately. Produce and validate a student-safe view that physically excludes sealed material until the intended reveal step.

### P1 — The learner contract and deeper tests are not implementation-neutral

`REQUIREMENTS.md` does not specify the missing-key result, sorted-key behavior, exact batch tuple rules, exact limits and exceptions, or the required corruption exception type. Yet `sealed/reference_tests/test_recovery.py:12-13` imports an undeclared `CorruptLogError`, and tests at `:76-128` replace a private `_file` attribute. Other tests assume the exact `.compact.tmp` name and patch module-level `os.replace` (`:130-162`). A correct alternative using `os.write`, a different handle name, or a different temporary-file strategy can satisfy the stated behavior and still fail these tests.

State the observable API precisely. Keep authoritative learner tests black-box, and put reference-specific white-box fault tests in a separately labeled implementation-validation suite.

### P2 — The record bound is applied too late during replay

Replay calls `Path.read_bytes()` and `splitlines()` before checking record length (`sealed/reference/kvstore.py:146-163`). It also handles an unterminated tail before the size check. A 4,194,305-byte unterminated tail—one byte over `MAX_RECORD_BYTES`—was accepted and truncated to zero. Arbitrarily larger input can therefore force whole-file allocation, contrary to the stated aim that untrusted input cannot force an unbounded single record (`REQUIREMENTS.md:15`). Stream replay with a bounded reader and define a hard maximum for incomplete tails.

### P2 — Validation scripts need stronger failure semantics and coverage labels

The fuzzer and stress/fault scripts rely heavily on `assert`, whose checks disappear under `python -O`. The fuzzer also accepts `--operations -1` and reports `model fuzz passed` without executing an operation. The positive 600-operation run was useful, but it does not cover batches, compaction, corruption, bounds, or shared-key concurrency. Validate numeric arguments, use explicit failures, and label each script as a bounded smoke check rather than evidence of exhaustive fuzzing or crash safety.

### P2 — Provenance is useful but the license boundary is incomplete

Local read-only checks confirmed that commit `aa17439b62f384511a5561ce308e9598b94d8989` is the pinned Build Your Own X commit, contains the cited DBDB entry, and states the catalog's CC0 waiver. That supports the catalog provenance.

It does not establish the license of the externally linked DBDB tutorial, and the archive supplies no separate license for the agent-generated material or per-file origin/derivation mapping. `PROVENANCE.json:3-4` asserts new generation and no copying, but that assertion is not independent evidence. Distinguish catalog license, tutorial license (`NOASSERTION` if unknown), and generated-artifact license explicitly; include immutable artifact hashes if reproducible provenance is intended.

## Positive evidence

- All 33 submitted Python/text artifacts remained unchanged during review; the candidate aggregate SHA-256 stayed `31a95c6479fa37dc9f2874679eaaf862fd4eba60206ce0309d6b7931982a1be5`.
- On the available CPython 3.11.5 POSIX host, all submitted Python sources compiled.
- The sealed reference passed 4/4 public tests and 10/10 sealed recovery tests.
- Independently executed reference fuzz (600 operations), stress (6 x 80 writes), torn-tail recovery, and debugging regression checks passed.
- The intentionally buggy lost-delete target failed with the expected returning-key symptom, making that exercise concrete and useful.
- The manifest correctly says external validation is required and the artifact is not production-ready.

Detailed commands and observed results are in `VALIDATION.md`.
