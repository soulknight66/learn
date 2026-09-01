# Kafka-like replicated log challenge

Build an in-memory, single-partition replicated log in Java 17. The finished
implementation must provide append-only offsets, reads that start at a requested
offset, quorum-gated replication, a committed high watermark, and deterministic
leader failover.

Only the Java standard library is allowed. Do not change the public package,
class names, constructors, or method signatures: the contract tests compile
directly against them.

## Source layout

The public API is in `src/main/java/io/learningfactory/kafkalite/`:

- `LogRecord` is an immutable offset/value snapshot.
- `PartitionLog` is one append-only partition log.
- `ReplicatedPartition` coordinates a fixed set of replicas.

The supplied classes intentionally contain no implementation.

## Required behavior

### Records and a local partition log

- Partition IDs and record offsets are non-negative.
- Record values are non-null byte arrays. Values must be isolated from later
  caller mutation, including mutation of an array returned by `value()`.
- The first appended record has offset `0`; later offsets are contiguous.
- `append` returns the assigned offset. `endOffset` is the next offset that
  would be assigned, so an empty log has end offset `0`.
- `read(offset, maxRecords)` starts at the requested offset, preserves append
  order, and returns at most `maxRecords` records. A start at the end or a
  `maxRecords` value of `0` returns an empty list.
- A negative read offset, an offset beyond the end, or a negative `maxRecords`
  value is invalid.

### Replication and availability

- A replicated partition has a non-negative partition ID, a non-empty list of
  distinct non-negative replica IDs, and a configured `minInSyncReplicas` in
  the inclusive range `1..replicaCount`.
- The initial leader is the lowest replica ID.
- An append is accepted only when at least `minInSyncReplicas` replicas are
  available and in sync. A rejected append throws `IllegalStateException` and
  does not change any replica log or the high watermark.
- An accepted append is assigned once, copied to every available in-sync
  replica, and committed before `append` returns.
- `highWatermark()` is an exclusive offset: records below it are committed.
  It starts at `0` and advances to the next offset after an accepted append.
- Replicated `read` returns only committed records and otherwise follows the
  same offset and limit rules as `PartitionLog.read`.
- `failReplica` makes a replica unavailable but preserves its log. Failing the
  leader triggers an election among available in-sync replicas; the lowest
  eligible replica ID wins. If none is eligible, there is no leader and
  `leaderId()` throws `IllegalStateException`.
- `recoverReplica` makes a known replica available, catches it up to the
  committed prefix when a leader is available, and returns it to the in-sync
  set after catch-up. Recovery does not replace a currently available leader.
- Failure and recovery calls are idempotent. Unknown replica IDs are invalid.
- `inSyncReplicaIds()` returns a snapshot. `replicaEndOffset(id)` reports the
  durable next offset even while that replica is unavailable.

Use `IllegalArgumentException` for every invalid constructor, append, read, or
replica-ID argument, including a required reference that is null.

## Run the public contract tests

From the challenge repository root:

```sh
sh public_tests/run.sh milestone-1
```

Replace the milestone number as you progress, then run `sh public_tests/run.sh` for all groups.
The runner's full tool and temporary-directory prerequisites are in `environment/README.md`.
Additional independent tests may check any behavior specified above.
