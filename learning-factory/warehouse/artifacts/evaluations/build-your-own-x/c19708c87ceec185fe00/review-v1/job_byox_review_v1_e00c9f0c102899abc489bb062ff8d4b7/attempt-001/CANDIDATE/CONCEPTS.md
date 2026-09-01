# Concepts to learn

## A byte stream has no messages

TCP may split one request across reads or combine several requests in one read. Parser state
therefore owns an input buffer and emits only frames proven complete by syntax and length.
Limits are part of correctness: a parser that waits forever for an advertised terabyte body
is operationally incorrect even if its grammar is elegant.

## Concurrency is a resource policy

A worker pool bounds threads and queues work, per-connection threads simplify local control
flow but require an admission limit, and an event loop makes connection state explicit while
forbidding blocking handlers. None is universally best. Compare code complexity, tail
latency, overload response, shutdown, and failure isolation using the same service contract.

## Delivery and application semantics differ

A client can lose a response after a mutation commits and retry. An idempotency key lets the
application recognize that retry. Its scope, retention, capacity, authentication identity,
and durable lifetime are product decisions, not an HTTP parser feature.

## Observability changes debugging cost

Health is not readiness, counters are not traces, and a process-local metric is lost on
restart. Still, explicit fault counters, bounded error responses, environment capture, and
raw benchmark samples provide much stronger evidence than “it seemed fast.”
