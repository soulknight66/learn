# Sealed reference design

This document describes the intended reference architecture for QuorumLog. It is
solution material, not an additional learner-facing contract. If this document and
REQUIREMENTS.md differ, REQUIREMENTS.md controls observable behavior.

The implementation is an educational, deterministic, in-memory model. It is not a
Kafka broker, a consensus protocol, a persistence layer, or production-ready
distributed-systems software. In particular, method calls stand in for networking
and an explicit failure flag stands in for failure detection.

## Design target

The model must make five ideas directly inspectable:

1. a partition is a contiguous, zero-based ordered log;
2. replication and commitment are different facts;
3. successful writes are copied synchronously to the current in-sync replicas;
4. only a replica containing the committed prefix may lead; and
5. recovery copies missing history before restoring eligibility.

All state belongs to one Java object graph. Public methods on mutable objects are
synchronized, making each completed call one linearized state transition. There is
no background thread, clock, retry loop, or nondeterministic scheduler.

## State model

### LogRecord

A record contains:

- a non-negative offset; and
- an owned byte array.

The constructor clones the supplied array. The value accessor clones it again.
The two copies close both aliasing directions: changing the append buffer later
cannot change history, and changing a returned buffer cannot change history.
Equality compares the offset and byte contents rather than array identity.

### PartitionLog

A local log contains a partition ID and an ArrayList of immutable LogRecord
instances. Its representation invariant is:

- the element at list index i has offset i;
- records are never removed or replaced;
- endOffset equals the list size; and
- no stored record exposes its internal byte array.

Appending assigns the current list size, constructs an owned record, adds it once,
and returns that assigned offset. A read validates the range, computes the
half-open slice [fromOffset, min(endOffset, fromOffset + maxRecords)), and returns
a list snapshot. A zero-sized read and a read at endOffset are valid empty reads.
An offset beyond endOffset is invalid rather than silently clamped.

The implementation uses an int-indexed ArrayList while the API exposes long
offsets. This is acceptable for the bounded educational model, but it means heap
capacity and Integer.MAX_VALUE are practical limits long before the long offset
space is exhausted.

### ReplicatedPartition

The coordinator owns:

- a sorted map from replica ID to a Replica object;
- one PartitionLog per configured replica;
- an availability bit per replica;
- a sorted in-sync replica set, abbreviated ISR;
- an optional leader ID;
- a fixed minInSyncReplicas threshold; and
- an exclusive highWatermark.

Sorted structures are a correctness aid, not merely presentation: initial
selection and every election choose the lowest eligible ID without depending on
caller list order or hash iteration order.

Immediately after construction every replica is available and in sync, every log
is empty, the high watermark is zero, and the lowest configured ID is leader.

## Offset and commit algebra

Both endOffset and highWatermark are exclusive:

- an empty range is [0, 0);
- after records at offsets 0, 1, and 2, endOffset is 3; and
- a high watermark of 2 makes offsets 0 and 1 consumer-visible.

In this synchronous reference model, a successful append completes on every
current ISR member and then advances the watermark. Consequently, after every
ordinary completed operation, each ISR end offset and the leader end offset equal
the high watermark. The API nevertheless keeps storage position and commit
position separate because that distinction becomes essential with asynchronous
replication, crash recovery, or speculative suffixes.

The configured minimum ISR value is an acknowledgement policy. It is allowed to be
any value from one through the replica count; it should not be mistaken for a
majority-consensus proof. Safety in this model also relies on a single coordinator
that never produces concurrent leaders.

## Append transition

Replicated append executes as one coordinator transition:

1. Validate the payload and clone it before changing state.
2. Require a leader that is available and in the ISR.
3. Require the ISR size to meet minInSyncReplicas.
4. Read the leader end offset and require it to equal highWatermark.
5. Preflight every ISR member: it is available and has the expected end offset.
6. Append the same payload snapshot to every ISR log and verify each assigned
   offset.
7. Advance highWatermark from the assigned offset to assigned offset plus one.
8. Return the assigned offset.

The quorum, leadership, and alignment checks all occur before the first log
mutation. Thus expected validation and availability failures have no write-side
effect. As in most ordinary Java code, unrecoverable virtual-machine failures such
as OutOfMemoryError are outside the transactional guarantee; production storage
would need a durable prepare/commit protocol rather than a sequence of heap
updates.

Failed replicas have already been removed from the ISR and therefore do not
receive writes. A successful append is sent to all current ISR members, not only
the minimum number needed to pass the gate.

## Read transition

A replicated read first validates its arguments against the committed range:

- fromOffset must be in [0, highWatermark];
- maxRecords must be non-negative; and
- zero records or a start exactly at highWatermark yields an empty result.

A non-empty read requires the current leader and caps its local read limit at the
number of committed records remaining. No returned record can therefore have an
offset at or above highWatermark. The empty boundary cases do not need to inspect
a leader log and may return an empty snapshot even while no leader exists.

The records in the result are immutable snapshots in the ownership sense:
LogRecord.value returns another array copy. The list itself is also detached from
the backing ArrayList.

## Failure and election transition

Failing a known replica:

1. does nothing if it is already unavailable;
2. marks it unavailable without deleting its log;
3. removes it from the ISR; and
4. if it was leader, clears leadership and scans configured replicas by ascending
   ID for an eligible replacement.

An election candidate must be available, be in the ISR, and have an end offset
exactly equal to highWatermark. Under the reachable reference state, an ISR
member also agrees byte-for-byte on that prefix. The explicit committed-prefix
test documents the safety reason behind the eligibility rule.

If no replica qualifies, the leader remains absent. leaderId and append then fail
with IllegalStateException. The high watermark and retained logs do not move
backward, so loss of liveness does not rewrite acknowledged history.

## Recovery transition

Recovery retains a failed replica's local log and separates availability from ISR
membership.

With an active leader, recovery follows this order:

1. mark the known replica available;
2. record its current end offset;
3. read the missing committed interval from the leader;
4. append those records in order, checking their offsets;
5. require the recovered end offset to equal highWatermark; and only then
6. add the replica to the ISR.

The current leader is not replaced merely because a lower-ID replica returns.

When no leader exists, a recovered replica may seed an election only if its
retained log ends exactly at the committed watermark. Once a safe leader is found,
the coordinator catches up any other already-available lagging replicas and adds them
to the ISR after copying. A replica that is still behind while no safe source
exists can be available without being in sync and cannot lead.

This model cannot create a divergent suffix through its public API. The reference
therefore rejects a recovered log whose end lies beyond the watermark instead of
implementing truncation. Real recovery needs leader epochs or an equivalent
authority rule to identify and remove conflicting suffixes.

## Core invariants

The following assertions are useful after every state-changing method:

1. Configured membership never changes.
2. Every log has offsets exactly 0 through endOffset minus one.
3. The ISR is a subset of available replicas.
4. If a leader exists, it is available, in the ISR, and its log ends at the
   watermark.
5. Every ISR log ends at the watermark and has identical bytes below it.
6. The watermark is non-negative and never decreases.
7. A record returned by ReplicatedPartition.read has an offset below the
   watermark.
8. No failed append changes any end offset or the watermark.

The implementation directly enforces items 2 through 5 at transition boundaries
and obtains byte agreement from the fact that one cloned payload is appended at
the same offset to every ISR member.

## Concurrency and lock order

PartitionLog methods synchronize on their own log. ReplicatedPartition methods
synchronize on the coordinator and may then call a local log. Local logs never
call back into the coordinator, so the lock order is one-way:

    coordinator -> replica log

This avoids a coordinator/log lock cycle. The synchronization also prevents a
read from observing an append between replica copies and watermark advancement.
Thread scheduling is not part of the exercise contract, but this implementation
provides a simple linearizable in-process behavior for calls on one instance.

## Error taxonomy

IllegalArgumentException denotes invalid caller input: negative IDs or ranges,
null required references, duplicate membership, an out-of-range minimum ISR, an
offset beyond the visible end, or an unknown replica ID.

IllegalStateException denotes a valid request that current modeled state cannot
serve: no eligible leader, insufficient ISR, or an internally inconsistent
replication/recovery state.

No public operation silently changes configuration or discards committed data to
make progress.

## Deliberate omissions

The design has no disk, segment format, checksum, fsync policy, retention,
compaction, batching, compression, protocol, authentication, authorization,
consumer groups, controller quorum, broker epochs, fencing, network partitions,
timeouts, retries, backpressure, metrics, rolling upgrade, or multi-partition
ordering. These are not minor deployment tasks; several change the correctness
model. See sealed/production/PRODUCTIONIZATION.md for the resulting gap analysis.
