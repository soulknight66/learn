# Behavioral requirements

## 1. Scope and public API

Implement the existing classes in package `io.learningfactory.kafkalite` without changing public
signatures:

- `LogRecord(long offset, byte[] value)` with `offset()` and `value()`.
- `PartitionLog(int partitionId)` with `partitionId()`, `append(byte[])`, `endOffset()`, and
  `read(long fromOffset, int maxRecords)`.
- `ReplicatedPartition(int partitionId, List<Integer> replicaIds, int minInSyncReplicas)` with
  `partitionId()`, `leaderId()`, `highWatermark()`, `inSyncReplicaIds()`, `append(byte[])`,
  `read(long fromOffset, int maxRecords)`, `failReplica(int)`, `recoverReplica(int)`,
  `isReplicaAvailable(int)`, and `replicaEndOffset(int)`.

No external dependency, process, network, clock, or random source may be required.

## 2. Values and ownership

- Partition IDs and replica IDs are non-negative integers.
- Replica IDs supplied to a replicated partition are non-null, non-empty, and unique.
- `minInSyncReplicas` is between one and the replica count, inclusive.
- Record values are non-null byte arrays. An append takes ownership by copying the input.
- A record accessor and every read result must prevent mutation of stored bytes through aliases.
- Invalid constructor or read/append arguments raise `IllegalArgumentException`. Operations naming
  an ID outside the configured replica set also raise `IllegalArgumentException`.

## 3. Local partition log

- The first appended record has offset 0. Each later append receives the previous offset plus one.
- `endOffset()` is the next offset that would be assigned, not the last existing offset.
- `read(fromOffset, maxRecords)` starts at the inclusive offset, returns records in offset order, and
  returns at most `maxRecords`.
- `fromOffset` may equal `endOffset()`, producing an empty result. It must not be negative or greater
  than `endOffset()`. `maxRecords` must be non-negative; zero produces an empty result.
- Returned collections are snapshots: callers cannot change the log by modifying a list or record.

## 4. Replicated append and commit boundary

- Construction creates one empty local log per configured replica, makes every replica available
  and in sync, and chooses a deterministic initial leader from the configured set.
- `highWatermark()` is an exclusive offset. Records below it are committed; records at or above it
  are not consumer-visible.
- An append succeeds only when a leader is available and the minimum in-sync-replica condition can
  be met. A rejected append changes no replica log, membership set, offset, or watermark.
- A successful append writes one identical logical record at one identical offset to the eligible
  in-sync replicas, commits it, advances the watermark exactly once, and returns its offset.
- `read` follows the local-log argument rules with the high watermark as its visible end. A read at
  the high watermark or with a zero limit is empty and needs no leader. Any non-empty committed read
  requires an eligible leader and otherwise raises `IllegalStateException`.
- `inSyncReplicaIds()` is a stable snapshot and cannot be used to mutate internal membership.

## 5. Failure, leadership, and recovery

- `failReplica(id)` is idempotent and makes that replica unavailable. An unavailable replica cannot
  receive appends or lead.
- If the leader fails, choose the lowest-ID replica that is both available and eligible under the
  committed-prefix rule. In this model an eligible replica ends exactly at the high watermark. If
  none exists, there is no writable leader and append must fail cleanly.
- Losing replicas must never reduce the high watermark or make an acknowledged record disappear.
- `recoverReplica(id)` is idempotent. Before the replica is declared in sync, reconcile it with the
  current committed history and catch it up to the current leader's safe log state. With no leader,
  a lagging recovered replica remains available but out of sync; recovery of a replica whose end is
  exactly the watermark may seed an election and then repair available laggards.
- Recovery must not elect an unavailable replica, roll the watermark backward, create duplicate
  offsets, or expose an uncommitted/divergent suffix.
- `isReplicaAvailable` and `replicaEndOffset` report the modeled replica state even when that replica
  is offline.

## 6. Safety invariants

After every successful public operation:

1. Offsets in every replica log are contiguous and start at zero.
2. Every available in-sync replica has the same record bytes for every offset below the high
   watermark.
3. `0 <= highWatermark <= leader end offset` whenever a leader exists.
4. No successful consumer read returns an offset at or above the watermark.
5. A failed or invalid operation has no partial externally observable effect.

The final rule covers documented `IllegalArgumentException` and `IllegalStateException` outcomes.
Process termination, JVM failure, and resource exhaustion such as `OutOfMemoryError` are outside this
in-memory model's atomicity guarantee.

The supplied public tests are examples, not an exhaustive specification. Independent validators may
generate longer state-machine traces and check these invariants after every step.
