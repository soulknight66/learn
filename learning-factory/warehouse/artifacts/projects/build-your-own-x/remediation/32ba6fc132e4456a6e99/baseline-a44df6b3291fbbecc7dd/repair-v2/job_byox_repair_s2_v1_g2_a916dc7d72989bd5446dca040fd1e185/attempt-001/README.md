# MiniLog: build a Kafka-like replicated partition

MiniLog is a dependency-free Java 21 challenge about the hard core of a
Kafka-like broker: an ordered durable log, recovery after partial writes,
leader epochs, majority commit, and read isolation. You will implement one
partition rather than networking, a protocol parser, or a production cluster.
That narrow boundary keeps the safety properties observable and testable.

The starter compiles but deliberately throws `UnsupportedOperationException`
at incomplete behavior. Public tests are a small executable contract and are
expected to fail before you implement the milestones. Evaluator-controlled
tests may probe every requirement.

## Suggested reveal order

1. **Immutable records** — make byte-array ownership and offsets unambiguous.
2. **Framed persistence** — encode records with an integrity-checked length
   header and CRC32-protected body.
3. **Recovery and segments** — rotate files, reopen them, repair only a torn
   final write, and reject durable corruption.
4. **Election state** — apply term fencing and log-freshness voting rules.
5. **Replication state** — track follower progress and advance a majority high
   watermark without allowing it to regress.
6. **Partition integration** — expose leader and committed reads with distinct
   visibility, while making the partition the exclusive mutation owner of its
   log and replication tracker.

Read `REQUIREMENTS.md`, then `CONCEPTS.md` and `DESIGN_QUESTIONS.md`. The exact
source layout and build commands are in `starter/README.md` and
`public_tests/README.md`.

The exact learner-distribution allowlist is machine-readable in
`environment/learner_view.json`. The acceptance harness can build that view
with `environment/project_learner_view.py`; the evaluator-only roots are never
copied by that projection.

## Scope and status

This is an educational state-machine model, not a production broker. There is
no network transport, authentication, metadata quorum, compaction, consumer
groups, or multi-partition transaction protocol. The artifact stays marked
`GENERATED` and `PARTIAL`; only an independent validator may award stronger
labels.
