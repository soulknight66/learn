# Concepts

## An ordered log is indexed history

An append-only log stores records in one total order. The offset is a position in that order, not a
timestamp and not a globally unique message ID. Using an exclusive end offset makes empty logs and
ranges convenient: the readable interval is `[start, end)`.

## Replication separates storage from commitment

Copying a record to one machine makes it stored there; it does not by itself define whether a client
may rely on that record surviving leadership change. A replicated system needs an explicit rule for
acknowledgment and a commit boundary. This exercise names that boundary the high watermark. A
consumer sees only the prefix below it.

## Leaders define an order, followers preserve it

For one partition, a leader serializes appends and followers reproduce the same offsets and values.
If different replicas could independently assign the same offset, their histories might diverge.
Leadership is therefore coupled to an eligibility rule: a replacement must contain the committed
prefix before it may continue the log.

## In-sync is stronger than available

Availability answers “can this replica participate right now?” In-sync membership answers “does its
history satisfy the replication contract?” A recovered node can be reachable but still need catch-up
before it is safe to count toward acknowledgments or elect as leader.

## Minimum ISR is an acknowledgment policy

`minInSyncReplicas` trades write availability for redundancy at acknowledgment time. A larger value
survives more immediate losses of individual copies, but rejects writes sooner during outages. It is
not a full consensus algorithm: this deterministic single-process model has no messages, timeouts,
terms, or competing leaders.

## Safety and liveness are different questions

Safety means nothing bad becomes observable—for example, an acknowledged prefix does not change.
Liveness means useful work can eventually continue. Rejecting an append during a large outage can
preserve safety while sacrificing liveness. Production systems must additionally handle delayed,
duplicated, and reordered messages and must distinguish a slow node from a failed one.

## Recovery is state reconciliation

A returning replica cannot merely flip an availability flag. It may have missed records, and in a
richer model it might contain a speculative suffix. Recovery establishes a common safe prefix,
copies required history, and only then restores election and acknowledgment eligibility.

## This model's boundary

The challenge teaches log and replication invariants, not the Kafka protocol or a production
consensus protocol. Real brokers add persistent segments, checksums, epochs, membership protocols,
flow control, batching, retention, snapshots, authentication, observability, and carefully specified
crash recovery.
