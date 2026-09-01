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

The repository uses only `javac`, `java`, and a POSIX shell. From the repository root, run:

```sh
sh public_tests/run.sh
```

You need a JDK 17 or newer; a JRE alone is insufficient. The generation host did not contain Java,
so this artifact is labeled `PARTIAL`: its source was statically checked, but compilation and test
execution still require independent validation on a JDK-equipped host. See `VALIDATION.md` for the
exact observed commands and results.

## Boundaries

- The model has one partition and fixed replica membership.
- Failures are explicit method calls, not a timing or network simulation.
- `highWatermark()` and `endOffset()` are exclusive offsets.
- Consumer-group coordination, persistence, batching, authentication, compression, and wire
  protocols are out of scope.
- Do not inspect `sealed/`; it contains validator and reference material, not learner guidance.

This independently generated exercise was inspired only by the catalog topic recorded in
`PROVENANCE.json`. See `LICENSE_BOUNDARY.md` for the provenance and licensing boundary.
