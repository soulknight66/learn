# QuorumLog: build a Kafka-like replicated log

QuorumLog is a dependency-free Java 17 challenge about the small, difficult core of a distributed
log: offsets, ordered append, replication, a commit boundary, leader loss, and replica recovery. It
is deliberately an in-process deterministic model. There are no sockets, threads, disk segments, or
claim of Kafka protocol compatibility. Those omissions keep the safety rules visible and testable.

## Your goal

Complete the code under `starter/src/main/java/io/learningfactory/kafkalite/`. Do not change its
public API. A correct implementation maintains one ordered partition across several replicas and
exposes only committed records to consumers, including while replicas fail and recover.

Read these in order:

1. `REQUIREMENTS.md` defines the observable contract.
2. `CONCEPTS.md` supplies the vocabulary without prescribing an implementation.
3. `starter/README.md` maps the milestones to the source files.
4. `public_tests/README.md` explains the executable examples.
5. `DESIGN_QUESTIONS.md` helps you justify choices after the tests pass.

The challenge is progressively revealable. Start with milestone 1 and open the next section only
after the current public-test group passes.

<details>
<summary>Milestone 1 — one append-only partition</summary>

Implement immutable records, monotonically increasing zero-based offsets, bounded reads, and byte
array ownership in `PartitionLog`.

</details>

<details>
<summary>Milestone 2 — synchronous replication and commit visibility</summary>

Implement `ReplicatedPartition` construction, append replication, the in-sync replica set, and the
exclusive high watermark. Reads must stop at that watermark.

</details>

<details>
<summary>Milestone 3 — faults and deterministic leadership</summary>

Model replica availability. Reject writes when the configured minimum in-sync replica count cannot
be met. On leader loss, elect only an eligible replica and make the result deterministic.

</details>

<details>
<summary>Milestone 4 — recovery without exposing divergent data</summary>

Catch a recovered replica up safely before it rejoins the in-sync set. Exercise repeated failure,
recovery, append, and read sequences while preserving committed-prefix agreement.

</details>

## Running the public checks

Run one milestone without triggering any later group:

```sh
sh public_tests/run.sh milestone-1
sh public_tests/run.sh milestone-2
sh public_tests/run.sh milestone-3
sh public_tests/run.sh milestone-4
```

After all four groups pass, run the complete suite:

```sh
sh public_tests/run.sh
```

The runner requires a JDK 17 or newer, a POSIX-compatible shell, `dirname`, `mktemp`, and `rm`.
A JRE alone is insufficient. It uses `$TMPDIR` when set, otherwise `/tmp` when writable, and finally
the repository root when writable. Set `TMPDIR` to an existing writable directory if none of those
defaults is suitable. The generation host did not contain Java, so no included result establishes
that these sources compile or pass; this artifact therefore remains `PARTIAL` pending independent
validation on a JDK 17+ host.

## Boundaries

- The model has one partition and fixed replica membership.
- Failures are explicit method calls, not a timing or network simulation.
- `highWatermark()` and `endOffset()` are exclusive offsets.
- Consumer-group coordination, persistence, batching, authentication, compression, and wire
  protocols are out of scope.
- The production pack contains `sealed/` reference and validator material. It must never be handed
  directly to a learner. Delivery tooling must copy only the exact paths in
  `environment/student-view-files.txt`; a sealed validator rejects extra or changed export files.

## Learner-safe provenance and license notice

This exercise was generated independently from catalog metadata about the topic. The linked
tutorial was treated only as an identifier: its license is `NOASSERTION`, and none of its code,
examples, prose, or layout was copied into this pack. The catalog metadata is identified as
CC0-1.0. To the extent the pack builder holds copyright in this independently generated code and
prose, that material is made available under CC0 1.0 Universal
(SPDX-License-Identifier: CC0-1.0). This grant does not apply to the linked tutorial, immutable
third-party metadata, third-party names, or third-party software.

“Kafka-like” describes the learning goal and does not claim protocol compatibility or affiliation
with Apache Kafka. The production pack retains separate immutable provenance, license-boundary, and
validation records; those operational records are intentionally not part of the learner export.
