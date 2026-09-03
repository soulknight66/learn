# Independent review

Advisory verdict: **REVISE**. The pack is unusually careful and nearly all submitted claims were
independently reproducible, but the reference invariant checker has one contract-level gap.

## Prioritized findings

### 1. Medium — `cairn_validate` accepts an out-of-range live process entry

`REQUIREMENTS.md:23-26` requires every spawned entry to be below `CAIRN_USER_TOP`, while
`REQUIREMENTS.md:89-101` says `cairn_validate` succeeds only when all structural facts hold and must
reject any violation in arbitrarily mutated public state. The process checks at
`sealed/reference/src/cairn.c:627-646` validate state and PID but never validate `process->entry`.

An independent mutation check initialized a valid kernel, spawned PID 1, changed that live process's
entry to exactly `CAIRN_USER_TOP`, and compared it with a corrupt mapping-flag control:

```text
baseline=0 invalid_entry=0 invalid_mapping_flag=-9
```

Thus the invalid entry is reported as `CAIRN_OK`, while the control is correctly reported as
`CAIRN_ERR_CORRUPT`. A learner can implement the spawn boundary correctly yet rely on a reference
validator that accepts the same forbidden value after public-state corruption. Reject out-of-range
entries for every non-empty process and add READY/RUNNING/BLOCKED/EXITED boundary regressions. If
entry validity was intentionally excluded from structural validation, the contract must say that
explicitly instead of promising “all structural facts.”

## Other review dimensions

- **Correctness evidence:** Independent strict builds, 4 public tests, 9 focused tests, 25,000 mixed
  operations, sanitizer repeats, static analysis, 100,000 arbitrary-byte validator calls, undefined
  symbol inspection, and QEMU boot all otherwise passed. These checks do not erase the finding above.
- **Reproducibility:** Relevant pinned tools were available and invoked by absolute path. With the
  documented source-relative NASM invocation, submitted starter and reference binaries reproduced
  bit-for-bit. The candidate aggregate remained unchanged during review.
- **Progressive disclosure:** Learner-facing source contains the incomplete skeleton and public tests;
  reference code, extended tests, resolutions, and review answers are confined to `sealed/`. The full
  review bundle itself offers path separation, not access control, so publication still depends on
  the factory constructing a filtered learner view.
- **License and provenance:** The pack clearly separates CC0 catalog metadata from the linked
  resource's `NOASSERTION` license and does not claim that the link grants reuse. Manifest and
  provenance objects are internally consistent. External authorship, commit, and license evidence
  could not be authenticated without the immutable source snapshot or network access.
- **Learner usefulness:** The contract, concepts, public examples, design questions, staged debugging
  prompts, review exercises, adversarial checklist, and benchmark cautions form a coherent learning
  progression. Scope boundaries between a host model, emulator smoke test, and real OS are clear.
- **Validation honesty:** `MANIFEST.yaml` remains `GENERATED` + `PARTIAL`; the prose does not claim
  BUILDS, TESTED, FUZZED, BENCHMARKED, REVIEWED, TRANSFER_VERIFIED, or PRODUCTIONIZED from builder-owned
  evidence. The timing probe is explicitly not called a benchmark, and the mixed driver is explicitly
  not called fuzzing.

This review does not edit or promote the candidate manifest. Even after the finding is fixed, only an
orchestrator-captured acceptance validator may publish `REVIEWED`.
