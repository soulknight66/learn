# Sealed reference implementation

This directory contains the complete Java 17 reference for the Kafka-like
partition exercise.  It is solution-bearing material and must not be exposed
in a learner view.

The implementation has no external dependencies.  Its three public classes
mirror the starter API in package `io.learningfactory.kafkalite`:

- `LogRecord` is an immutable offset/value pair.  Payload arrays are copied at
  both boundaries.
- `PartitionLog` is an append-only in-memory log with contiguous offsets and
  bounded reads from an inclusive offset. A read exactly at the end is empty;
  a read beyond the end is invalid.
- `ReplicatedPartition` owns one log per replica, synchronously replicates to
  the current ISR, advances an exclusive committed high watermark only after
  the configured acknowledgement quorum is present, elects the lowest
  eligible replica ID after leader failure, and catches durable failed logs up
  when replicas recover.

`endOffset()` and `highWatermark()` are exclusive offsets.  Thus a new log has
both values at `0`; after committing offsets 0 and 1, both are `2`.  Reads on a
replicated partition are capped at the high watermark, so consumers never see
an uncommitted suffix.

`minInSyncReplicas` is the exercise's explicitly configured acknowledgement
quorum.  The model does not silently replace it with a majority calculation.
An append below that threshold fails before any log changes.  Election itself
does not imply that enough replicas exist to accept writes: a surviving leader
can serve committed reads while new appends remain unavailable.

## Compile and run the sealed suite

From the repository root:

```sh
sh sealed/reference_tests/run.sh
```

The runner invokes `javac --release 17 -Xlint:all -Werror`, applies the public and sealed suites to
the reference, and cleans its unique temporary build directory.

The state is intentionally in memory.  Replica failure preserves that
replica's `PartitionLog` object, which deterministically models durable local
storage without adding filesystem timing and corruption behavior to this
exercise.  It is not a production broker: there is no network protocol,
controller quorum, disk format, batching, authentication, or concurrent
multi-process recovery.

At generation time the workspace host did not provide `javac` or `java`, so
the compile command above could not be executed here (`javac: command not
found`).  The source targets Java 17, but independent validation in an
environment with a JDK remains required.
