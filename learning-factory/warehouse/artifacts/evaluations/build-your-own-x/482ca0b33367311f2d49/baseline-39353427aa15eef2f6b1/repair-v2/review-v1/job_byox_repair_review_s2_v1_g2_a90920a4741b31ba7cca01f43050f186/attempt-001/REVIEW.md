# Independent review

Verdict: **PASS (advisory)**. The submitted evaluator pack is internally consistent, the reference
meets the stated educational contract in the reviewed cases, the learner export enforces the intended
disclosure boundary, and the validation claims remain appropriately limited. Only the factory's
separate acceptance validator can publish `REVIEWED`.

## Prioritized findings

1. **P0–P2: no blocking findings.** Code inspection, supplied-suite reproduction, and independent
   probes found no contract, isolation, provenance-boundary, or claim-honesty defect that warrants
   revision.

2. **P3 — learner feedback is uneven across milestones.** The 11 public tests directly cover paths,
   layers, the runner, and end-to-end engine behavior, but there are no focused learner-visible tests
   for `StateStore`, `ImageStore`, or the CLI. A learner can eventually exercise these through the
   engine, but failures are harder to localize and milestone 7 has no public automated checkpoint.
   Consider adding small public smoke tests for canonical state round-trips, same-content image reuse,
   and one CLI JSON/error path without exposing sealed adversarial cases. This is non-blocking because
   the requirements, numbered TODOs, and warnings about incomplete tests are clear.

## Review basis

- **Correctness and reproducibility:** all Python compiled under the recorded CPython 3.11.5 binary.
  The reference passed 11 public and 37 sealed tests. Independent process-level probes additionally
  covered compressed layers, pre-mutation whiteout rejection, byte-exact output limits, descendant
  timeout cleanup, state-claim races, image-publication races, and CLI errors.
- **Progressive disclosure:** a real export produced exactly 28 allowlisted, byte-identical regular
  files. It excluded `sealed/`, private tests, evaluator exercises, provenance-review records, and
  validation evidence while retaining the learner copying notice.
- **License and provenance:** manifest/source/project identities agree internally. The boundary
  consistently distinguishes the CC0 catalog facts, the linked resource's `NOASSERTION` status, and
  the custom generated-material grant. Upstream similarity and factory-owned snapshot identifiers
  could not be independently checked offline.
- **Learner usefulness:** the staged requirements, concept explanations, design questions, numbered
  scaffold, and explicit non-goals form a coherent high-difficulty exercise. The P3 finding above is
  the only material usability improvement identified.
- **Claim honesty:** the candidate does not claim fuzzing, benchmarking, transfer verification,
  productionization, real containment, or independent review. `GENERATED` + `PARTIAL`,
  `productionized: false`, and `independent_validation: REQUIRED` remain accurate.

The known lack of kernel containment is high impact if the tool is misused, but it is prominently and
consistently documented as an explicit non-goal; the reference must continue to run trusted commands
only.
