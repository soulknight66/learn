# Reference design

`BEGIN IMMEDIATE` serializes the choose-and-claim transaction. A guarded update makes the
ownership assertion explicit. Every terminal transition clears lease columns, reinforced by
a table check constraint. Ingest binds a unique key to canonical JSON inside one transaction.

The effect and acknowledgement intentionally use separate transactions. The unique
`effects.message_id` constraint is the consumer idempotency fence. The injected crash after
the effect demonstrates why replay is expected, not exceptional. Retry time is persisted so
restart does not reset it. DLQ insertion shares the terminal transition transaction.

`BoundedDispatcher` is intentionally single-process and claim-on-demand. It holds at most one
lease because safe prefetch requires a concurrent lease keeper included in shutdown design.
