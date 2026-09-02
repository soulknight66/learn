# Independent review

Verdict: **REVISE** (advisory). The pack is well scoped and unusually candid,
but the sealed reference has one reproducible R6 atomicity hole. Only an
orchestrator-captured acceptance validator can publish `REVIEWED`.

## Prioritized findings

### P1 — A partition append can durably mutate before failing

`PartitionLeader` retains the caller's `SegmentedLog` and `ReplicationTracker`
objects, checks their offsets only in its constructor, and exposes no ownership
rule. The tracker also retains a public `advanceLeaderEndOffset` mutator. In
`sealed/reference/.../PartitionLeader.java:37-38`, append writes the record
before asking the tracker to advance.

The independent probe used only public, single-threaded calls:

1. Construct a log and tracker at end offset 0, then construct the partition.
2. Call `tracker.advanceLeaderEndOffset(2)` through the caller's retained alias.
3. Call `leader.append(4, 1, null, new byte[] {9}, true)` with the active term.

The record was written at offset 0. The subsequent tracker update tried to move
from 2 to 1 and threw `IllegalArgumentException`. Observed final state was local
log end offset 1 and tracker end offset 2; reopening the log independently
recovered end offset 1. The caller therefore saw failure after a durable file
mutation, contrary to R6's statement that caller errors must not partially
mutate offsets, replica progress, or files. It also breaks the constructor
invariant and makes retry semantics unsafe.

Revision should make component ownership and mutation ordering enforceable, not
merely conventional. At minimum, specify any exclusive-use precondition and
check alignment before writing; a robust design should prevent aliased tracker
mutation (including between checks) or coordinate both components under one
state transition. Add a deterministic regression that asserts both file bytes
and both end offsets remain unchanged on misalignment.

### P2 — Learner-view isolation is asserted but not independently demonstrable

The evaluator pack appropriately contains `sealed/reference`, sealed tests, and
sealed answers. Several documents say those trees are excluded from a
learner-visible allowlist, but neither `MANIFEST.yaml` nor another candidate
artifact defines or builds that view. `sealed/validate_layout.py` validates the
combined evaluator pack; it does not prove what a learner receives or can read
at runtime.

This review workspace is explicitly evaluator-only, so the presence of sealed
files here is not itself a disclosure. Before release, the acceptance harness
should materialize the actual learner view and deterministically assert that
`sealed/`, `adversarial/`, evaluator answers/tests, and the source pack are not
readable from learner code. The candidate honestly makes no
`TRANSFER_VERIFIED` claim, so the present result is inconclusive rather than a
fabricated failure.

### P3 — Public feedback skips the codec milestone

The suggested implementation order starts with `LogRecord` and `RecordCodec`,
but `PublicTestMain` directly checks only `LogRecord` before moving to an
end-to-end `SegmentedLog` case. A learner can complete the detailed frame codec
and still remain at 1/5 until much of the next milestone is implemented. A small
package-local public round-trip/boundary test would give more useful progressive
feedback without revealing anything beyond the already-public R2 contract.

## Evidence that held up

- Absolute-path tool versions matched the builder record: Python 3.11.5,
  Temurin 21.0.5+11, and javac 21.0.5.
- The incomplete starter compiled and failed transparently at 1/5. The sealed
  reference run completed at public 5/5 and sealed 15/15.
- Two process-runner regressions passed, including intentional timeout code 124
  and descendant cleanup. Sequential runner use removed its scratch root.
- Strict metadata identity/linkage, expected raw hashes, required/forbidden
  layout, regular-file boundaries, and the credential-pattern scan all passed.
- Six additional behavioral probes passed, covering null versus empty keys,
  validation before rotation, oversized first frames, a five-node majority,
  stale-position contact refresh, and partial-header repair.
- Static inspection found only Java standard-library imports and no internal
  wall-clock reads in the starter or reference implementation. Starter and
  reference public source signatures are compatible.
- The requirements, trade-off analysis, and productionization notes clearly
  distinguish this deterministic teaching model from Kafka, a complete
  consensus protocol, or a production broker.

## Claim and provenance assessment

| Claim or label | Independent assessment |
| --- | --- |
| `GENERATED`, `PARTIAL` | Consistent with the manifest and incomplete starter. |
| `BUILDS`, `TESTED` | Not awarded; compile/suite observations are evidence, not promotion. |
| `FUZZED`, `BENCHMARKED` | Not claimed. The manual benchmark was inspected but not run. |
| `REVIEWED` | Not awarded by this advisory review. |
| `TRANSFER_VERIFIED` | Not claimed; learner-view transfer was unavailable. |
| `PRODUCTIONIZED` | Correctly false, with concrete missing mechanisms documented. |

The license boundary consistently distinguishes the CC0 catalog metadata from
the linked tutorial whose license is `NOASSERTION`, declares that linked content
was not copied, and uses no third-party dependencies. Because the immutable
catalog snapshot and linked source were unavailable and intentionally not
fetched, this review could check internal consistency but could not independently
prove the upstream license evidence, authorship, or non-copy assertion. The
generated material also states only “personal educational use,” not a standard
redistribution license; downstream redistribution rights should therefore not
be inferred.

## Review limitations

No fuzzing, performance run, crash campaign, filesystem fault injection,
network/security test, deployment, or transfer verification was performed.
Short-channel and write-failure paths were inspected but not forced. Dynamic
results cover only the configured Linux/Temurin 21 environment. `git` and `rg`
were unavailable; bounded standard-tool fallbacks were used.
