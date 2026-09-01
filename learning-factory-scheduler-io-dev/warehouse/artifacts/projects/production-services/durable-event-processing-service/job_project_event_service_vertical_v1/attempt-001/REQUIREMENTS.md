# Requirements

## Durable data model and migrations

Use numbered SQL migrations recorded durably. A restart may re-run the migration driver but
must not reapply an already recorded migration. Enforce states and lease-column consistency
in the schema. Do not use in-memory process identity as ownership.

## Ingest contract

`ingest(key, payload) -> (message_id, created)` atomically inserts one message. Repeating the
same key and canonical JSON is a successful duplicate; reusing it for different JSON is an
error. Limit key shape and encoded payload bytes. No caller assertion is evidence of commit.

## Delivery contract

`claim(owner, lease_seconds)` must use a write transaction and guarded update. At most one
concurrent caller obtains each lease. Expired leases are recoverable after a dead process.
Attempts increment on claims, not on ingest. Heartbeats may extend only a live owned lease.

Delivery is **at least once**. Apply the supplied local effect idempotently, then acknowledge
in a distinct transaction. A crash after the effect but before ack must cause redelivery and
suppress a duplicate effect. Document why a remote API needs its own idempotency protocol.

## Failure policy

Transient failures enter `RETRY_WAIT` using `base_backoff * 2^(attempt-1)`. The configured
final attempt atomically transitions the message and its diagnostic snapshot to `DEAD`.
An administrator can inspect and explicitly requeue a dead letter; requeue resets attempts
while preserving the audit row.

## Backpressure, lifecycle, and operations

Claim only when dispatch is ready so queued work never holds an unmaintained lease. Any future
prefetcher must be strictly bounded and heartbeat every outstanding lease. Shutdown stops new
claims, drains already-owned work, or explicitly releases it—never silently drops it. Emit
machine-readable log records and
monotonic counters. Provide keyset pagination for queue/DLQ inspection and a local admin CLI.
Never return an unbounded result set or use offset pagination for a mutating queue.

## Constraints

Python 3.11 standard library and SQLite only; no external network. Parameterize SQL. Tests
must use temporary databases. Preserve explicit `PARTIAL` / `NOT_PRODUCTION_READY` labels.
