# Sealed reference review

## Review status

The reference sources were inspected statically against REQUIREMENTS.md. No known
contract violation was identified for states reachable through the public API.
The generation host has no java or javac executable, so this is not a compilation
or test result. The repository must remain labeled GENERATED and PARTIAL until an
independent JDK-equipped validator compiles and runs it.

This review is scoped to the dependency-free in-memory exercise. It does not
approve the code for deployment and does not award TESTED, REVIEWED,
PRODUCTIONIZED, or any other validation label.

## Files and responsibilities

- LogRecord validates offset/value ownership and provides content-based utility
  methods without exposing bytes.
- PartitionLog owns contiguous local history and bounded snapshots.
- ReplicatedPartition owns membership, availability, ISR, leadership, commit
  position, replication, and catch-up.

No reference code is placed in learner-visible directories.

## Static correctness walk-through

### Input and ownership

All required nulls and invalid numeric/configuration values are converted to
IllegalArgumentException as specified. Replica membership is rebuilt in a sorted
map, which detects null, negative, and duplicate IDs. Record construction clones
its payload, value access clones again, and replicated append takes a snapshot
before visiting replica logs.

Residual consideration: repeated copies are correct but expensive. Very large
arrays can cause memory pressure; resource exhaustion is not modeled as an
ordinary transactional failure.

### Local log

The ArrayList index is the assigned offset, records are append-only, and reads use
a half-open slice. Offset addition is promoted to long before adding maxRecords,
then bounded by the int-sized list. A start at end and a zero limit return empty;
negative values and a start beyond end are rejected.

Residual consideration: the long API is backed by int-sized storage. This is
documented as an educational bound and should become segmented long-indexed
storage in any larger implementation.

### Append atomicity

Replicated append validates payload, leader, ISR count, leader/watermark alignment,
availability, and every ISR end offset before the first append. It visits the
sorted ISR twice: once to preflight and once to mutate. The high watermark moves
only after all copies report the expected offset.

For normal contract exceptions this preserves no-partial-effect behavior.
OutOfMemoryError or another fatal JVM failure between local appends could leave
heap state partially updated; the model makes no crash-atomic durability claim.

### Commit visibility

The watermark is exclusive. Replicated reads validate against it, return empty at
it, and cap the leader read to the remaining committed count. Under the reachable
state invariants, leader end equals the watermark, so the local log cannot return
an uncommitted suffix.

One subtle, intentional behavior is that a zero-length or at-watermark read can
return empty with no leader, because it needs no log access. A non-empty committed
read requires a leader.

### Failure and election

Failure preserves the log, clears availability, removes ISR eligibility, and only
then runs an election if needed. TreeMap iteration gives lowest-ID selection.
Candidates must be available, present in ISR, and end at the committed watermark.
No election lowers the watermark.

The public state machine cannot manufacture equal-length divergent prefixes, so
end position plus ISR membership is sufficient inside this model. It would not be
sufficient for data imported from disk or received from an untrusted peer; a real
implementation needs epochs and content-integrity checks.

### Recovery

A recovering follower is marked available but is not placed in ISR until missing
records are copied from the current leader and its end equals the watermark. A
returning lower-ID replica does not preempt a healthy leader.

With no leader, only a replica already ending at the watermark may rejoin and seed
an election. After that election, other available lagging replicas are caught up.
This handles the trace where a stale node recovers first and an up-to-date node
recovers later.

The code rejects a follower whose retained end is beyond the watermark. Such a
state is unreachable through the public methods, but the guard makes the missing
divergent-suffix policy explicit.

### Idempotence

Failing an unavailable replica returns without changing state. Recovering an
already available ISR member also returns. An available but not-yet-synchronized
replica may be reconsidered after a leader becomes available, which is necessary
for progress and still preserves the result of repeated calls in stable state.

### Concurrency

Mutable public methods are synchronized. The coordinator may acquire a local-log
monitor, but a local log never acquires the coordinator, so static lock order has
no cycle. A caller cannot observe the interval between copying to followers and
advancing the watermark.

Threaded stress testing was not performed on this host and remains independent
validation work.

## Required independent test scenarios

An independent validator should at minimum check:

1. both byte-array aliasing directions and mutation of prior read results;
2. every invalid constructor and method argument, including null membership
   elements and unknown IDs;
3. empty, boundary, bounded, and beyond-end reads;
4. append rejection snapshots every replica end and the watermark before/after;
5. election is independent of input list order;
6. a stale replica recovering first cannot lead without the committed prefix;
7. an up-to-date later recovery can seed leadership and repair the stale node;
8. repeated fail/recover calls preserve state;
9. long generated operation traces preserve the invariants in DESIGN.md; and
10. parallel calls are linearizable if thread safety is included in validation.

The validator should compare byte content, not only offsets and counts.

## Production blockers

The following are categorical blockers, not optional polish:

- no persistent record or metadata format;
- no crash recovery or fsync contract;
- no network protocol or independent failure domains;
- no term/epoch, voting, fencing, or split-brain prevention;
- no checksums or divergent-prefix reconciliation;
- no flow control, quotas, bounded retention, or disk-capacity policy;
- no identity, authentication, authorization, or transport protection;
- no monitoring, audit events, operational controls, or upgrade plan; and
- no executed test, fuzz, fault-injection, soak, or benchmark evidence on the
  generation host.

See sealed/production/PRODUCTIONIZATION.md for a staged plan. Completion of that
plan would require a different implementation and a new independent review; it
cannot be inferred from this exercise passing its contract tests.

## Reviewer conclusion

The reference is a coherent proposed solution for the bounded learning contract,
subject to compilation and independent tests on Java 17 or newer. Its simple
safety argument depends on synchronous in-process transitions and one trusted
coordinator. Those assumptions must remain prominent whenever results are
reported.
