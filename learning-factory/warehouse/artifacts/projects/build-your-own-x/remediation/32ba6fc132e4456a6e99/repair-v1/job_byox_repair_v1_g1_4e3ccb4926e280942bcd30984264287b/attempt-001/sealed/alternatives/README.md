# Alternative designs

These alternatives are not additional requirements. They show how changing one
assumption changes the state machine and proof obligations.

## Majority-replicated log with terms

Replace the single trusted coordinator with replicas that elect a leader using
terms and votes. Each entry carries a term; leaders replicate a preceding
offset/term pair and advance commit only after a voting majority stores an entry.
Persisted term and vote state, quorum intersection, and leader completeness would
replace the reference model's implicit single-authority assumption.

This is the appropriate direction for independently failing processes, but it is
substantially more than adding sockets. Election safety, retransmission,
conflicting suffix truncation, membership changes, and crash-atomic metadata all
need executable specifications and fault tests.

## Asynchronous primary/backup

Let the leader append locally, return according to a selected acknowledgement
level, and replicate in the background. Track a match offset for each follower;
derive a commit point from the ordered match offsets and the acknowledgement
policy.

This improves latency and can isolate slow followers, but creates observable
stored-yet-uncommitted data. Failover must use epochs and reconcile suffixes.
Acknowledging before a durable intersecting quorum can lose acknowledged writes.

## Segmented persistent log

Store immutable segment files plus sparse offset indexes. Roll segments by size,
checksum every record or batch, recover by scanning and truncating only a damaged
tail, and persist the committed position with a specified ordering relative to
data flushes.

This removes the heap-only limit and enables retention, but introduces partial
writes, corrupt indexes, disk-full behavior, directory atomicity, fsync semantics,
and file lifecycle races. A storage implementation should be tested with forced
process termination, not only Java exceptions.

## Single-owner event loop

Instead of synchronized public methods, enqueue commands to one partition owner.
The owner serializes state transitions and emits futures when replication or disk
conditions are met. This can avoid lock contention and makes asynchronous
completion explicit.

The cost is queueing, cancellation, shutdown, overload handling, and careful
ownership of payload buffers. Blocking disk or network work cannot run on the
owner without stalling the partition.

## Immutable state machine

Represent each operation as a pure function from State and Command to a new State
and Result. This is attractive for model checking, generated traces, replay, and
auditability. Structural sharing can limit copying.

It is less direct for large byte payloads and durable I/O, and allocation cost may
be high. A useful hybrid keeps a pure metadata state machine while storage owns
append-only pages.

## Recommendation by goal

- For teaching offsets and recovery invariants, retain the current synchronous
  deterministic model.
- For teaching consensus, build a new term-based project rather than describing
  minimum ISR as consensus.
- For storage engineering, isolate a segmented local log and define a crash
  matrix before adding replication.
- For production, combine a formally reviewed leader protocol, persistent
  segments, bounded asynchronous I/O, and an operational control plane. None of
  those properties are supplied by this reference.

