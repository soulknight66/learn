# Productionization gap analysis

This artifact is **not production-ready** and validators must retain `PARTIAL`. The reference
demonstrates useful production habits—strict bounds, overload response, explicit lifecycle,
idempotency semantics, fault containment, health, minimal metrics, adversarial checks, and raw
benchmark evidence—but important requirements remain deployment-specific and unimplemented.

Before exposure beyond loopback, choose a maintained HTTP/TLS stack or fund protocol security
ownership; test parsing agreement with every proxy; define authentication, authorization,
tenant isolation, request IDs, audit logs, secret handling, and abuse limits. Decide whether
counter/idempotency state is durable and how retries behave across restart. Add structured
logging, latency/error/saturation metrics, tracing context, readiness, SLOs, alerts, and
dashboards. Exercise rolling shutdown, saturation, dependency failure, restore, migration,
clock issues, and rollback. Package reproducibly and patch dependencies/toolchains.

The selector alternative also needs a bounded application executor before any handler may
block. The thread-per-connection version needs memory/stack capacity measurements. The worker
pool needs representative slow-client and queue-policy testing. None has been fuzzed at scale,
audited, load-tested on a target host, or operated through an incident.
