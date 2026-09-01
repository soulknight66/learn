# Concepts

- **Idempotent ingest** makes a client retry safe by binding one key to one canonical request.
- **Lease, not lock forever:** durable ownership expires so another process can recover work.
- **At-least-once gap:** side effect and ack are separate commits; either ordering has a crash gap.
- **Idempotent consumer:** a unique effect key turns replay into an observable no-op locally.
- **Transactional outbox/inbox:** useful when a database commit is the durable handoff, but not
  magic atomicity across unrelated databases and APIs.
- **Poison message:** deterministic failure consumes its retry budget and needs quarantine.
- **Backpressure:** bounded admission transfers overload to the caller instead of growing RAM.
- **Keyset pagination:** a stable last-seen identity behaves better than offsets during mutation.
- **Operational evidence:** structured events, counters, runbooks, and raw measurements support
  diagnosis; a green unit test alone does not establish production readiness.
