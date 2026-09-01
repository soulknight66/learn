# Sealed trade-off analysis

QuorumLog chooses clarity and determinism over fidelity to a real broker. This
file records the consequences so that passing the educational contract is not
misrepresented as production readiness.

## Synchronous replication

Choice: append copies to every current in-sync replica before returning and then
advances the high watermark.

Benefits:

- acknowledgment, replica end offsets, and visibility have a short proof;
- no background delivery or retry scheduler is needed;
- a successful method call is a complete deterministic transition; and
- failure tests can compare the whole state before and after a rejection.

Costs:

- append latency grows with replica count and payload-copy cost;
- one slow replica cannot be represented separately from a failed replica;
- there is no stored-but-uncommitted suffix during normal execution; and
- this does not teach delayed, reordered, duplicated, or lost messages.

An asynchronous design would need per-replica match offsets, an acknowledgement
tracker, retransmission, ordering rules, and a watermark calculated from those
positions. It would also need leadership epochs to decide which suffix survives.

## Configurable minimum ISR instead of majority consensus

Choice: writes are gated by minInSyncReplicas, whose legal range is one through
the configured replica count.

Benefit: learners can directly observe the availability/redundancy trade-off.
Cost: a low setting is not a quorum-intersection guarantee. The model remains safe
only because one in-process coordinator controls leadership and all state
transitions. In a real partitioned network, minimum ISR alone cannot stop two
leaders.

The configuration name should therefore be read as an acknowledgement policy,
not as proof that the implementation provides consensus.

## Fixed membership

Choice: replica IDs are validated once and never added or removed.

Benefit: election, ISR, and failure traces remain small enough to reason about.
Cost: there is no joint-consensus or reassignment phase, and a permanently lost
replica occupies the configuration forever. Production membership changes must
avoid old and new groups making incompatible decisions.

## One partition and byte-array values

Choice: the model has one ordered partition per coordinator and treats values as
opaque bytes.

Benefit: ordering and ownership are explicit, with no serializer dependency.
Cost: there is no key-based routing, cross-partition behavior, record metadata,
headers, timestamps, schemas, transactions, or consumer-group state. Defensive
copying also makes large payloads relatively expensive.

## In-memory ArrayList storage

Choice: each replica uses a Java ArrayList with index equal to offset.

Benefits:

- constant-time positional lookup;
- contiguity follows naturally from append; and
- no file cleanup or host dependency is required.

Costs:

- data vanishes with the process;
- offsets are practically bounded by int indexing and heap capacity;
- recovery copies whole payloads in heap;
- there is no checksum or corruption detection; and
- pauses and allocation pressure are not controlled.

A disk-backed alternative needs segmented files, an index, recovery scanning,
checksums, flush semantics, and atomic metadata. Merely serializing the ArrayList
would not provide a sound crash contract.

## Exclusive offsets

Choice: both local end and committed watermark are exclusive.

Benefit: count and range calculations use the same half-open interval convention,
including the empty case. The next append offset equals endOffset.
Cost: users familiar with an inclusive “last committed offset” must translate
carefully. Boundary tests are essential because either convention can appear
plausible in simple examples.

## Strict out-of-range reads

Choice: reading exactly at the visible end is empty, while reading beyond it is
invalid.

Benefit: callers discover stale or malformed positions rather than having them
silently clamped. Cost: polling clients must keep accurate offsets and explicitly
handle IllegalArgumentException for invalid positions. A network API might prefer
a structured offset-range response instead of a Java exception.

## Deterministic lowest-ID election

Choice: initial and replacement leaders are the lowest eligible replica ID.

Benefit: traces and tests are reproducible and independent of input or hash order.
Cost: this is not load-aware, rack-aware, or fair, and it has no term, vote, lease,
or fencing token. The rule selects among replicas that the single coordinator has
already deemed safe; it does not establish that safety in a distributed setting.

## Conservative recovery

Choice: a returning replica is available first, catches up through the committed
prefix, and joins the ISR only afterward. A replica beyond the watermark is
rejected rather than truncated.

Benefit: a lagging copy cannot acknowledge or lead during repair, and the
transition is easy to audit. Cost: divergent suffix recovery is intentionally
unsupported. Production systems require an authoritative epoch/history check and
safe truncation or snapshot installation.

## Coarse-grained synchronization

Choice: public mutable operations synchronize on one object, with local logs
synchronized independently.

Benefit: method-level atomicity is visible and race surfaces are small. Cost:
operations serialize, payload copying occurs while holding locks, and throughput
cannot scale across cores for one partition. A production implementation would
usually use a single-owner event loop or carefully partitioned concurrency, then
move disk and network completion into an explicit state machine.

## Copies rather than zero-copy views

Choice: inputs, accessors, and read results preserve byte ownership through
cloning.

Benefit: history cannot be rewritten by an alias held by a caller. Cost: append,
replication, recovery, and read all allocate and copy. Read-only buffers or
reference-counted pages could reduce copying, but their lifetime and mutation
rules would become part of correctness.

## Exceptions rather than result types

Choice: IllegalArgumentException represents a bad request and
IllegalStateException represents temporary modeled unavailability or invariant
failure.

Benefit: the small Java API stays compact. Cost: callers cannot distinguish all
causes without parsing context or wrapping calls. A service protocol should use
stable typed error codes, retriability metadata, and request IDs.

## Availability summary

Increasing minInSyncReplicas raises the number of copies present when an append is
acknowledged but rejects writes after fewer failures. Decreasing it does the
opposite. Regardless of that setting, this model cannot claim tolerance of real
network partitions because it has no independent processes or competing leaders.

