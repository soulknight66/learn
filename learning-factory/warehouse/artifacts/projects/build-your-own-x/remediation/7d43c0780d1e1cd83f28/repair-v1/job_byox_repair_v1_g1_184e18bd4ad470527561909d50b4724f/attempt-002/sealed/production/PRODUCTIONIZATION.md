# Productionization gap analysis

This file is a plan and risk register, not a production implementation. The
reference remains educational, the manifest remains `productionized: false`,
and no `PRODUCTIONIZED` or production-readiness claim is made.

## Define the supported boundary

Before deployment, specify supported Node release lines, HTTP versions, proxy
topology, maximum route count, request-target and header limits, allowed body
types and sizes, handler timeout rules, and shutdown semantics. Document the
route grammar as compatibility policy rather than implying Express parity.

## Resource and abuse controls

- Enforce bounded request-body bytes before buffering and bound decoded query
  keys and values.
- Add header, URL, per-request time, concurrent-request, and keep-alive limits
  appropriate to the deployment edge.
- Propagate disconnect/abort signals to application work and cancel work that
  no longer has a client.
- Use backpressure-aware streams; never turn an unbounded stream into a single
  Buffer for convenience.
- Establish overload behavior with admission control and small deterministic
  error responses.

## Security engineering

Create a threat model covering request smuggling across the actual proxy chain,
ambiguous path normalization, traversal in any future static-file feature,
header injection, open redirects, cache confusion, and denial of service. Add a
security contact, dependency and runtime patch policy, vulnerability response
process, and regression tests for every resolved issue. Secrets must come from
the deployment secret store and must be redacted from logs and errors.

Proxy-derived scheme, host, and client address must remain untrusted unless an
explicit trusted-proxy policy validates the immediate peer. Authentication,
authorization, CSRF defenses, CORS, cookies, sessions, and rate limiting are
application or audited-middleware responsibilities; their absence must not be
mistaken for safe defaults.

## Reliability and lifecycle

- Track accepted sockets and implement graceful stop: reject new work, allow a
  bounded drain interval, then terminate remaining connections.
- Define behavior for handler rejection after headers are sent, stream errors,
  repeated sends, client aborts, and process-level fatal errors.
- Provide readiness and liveness signals that reflect dependency and drain
  state without exposing internals.
- Exercise rolling restart, slow-client, dependency-timeout, and forced-shutdown
  scenarios.

## Observability and privacy

Emit structured request completion and internal error events with stable event
names, request correlation, duration, outcome, and byte counts. Never log raw
authorization or cookie headers by default. Define field allowlists, redaction,
retention, sampling, and access control. Metrics should expose traffic,
latency, error, saturation, abort, and rejection rates without high-cardinality
request data.

## Verification gate

Production consideration would require independent evidence for:

1. contract, integration, property, fuzz, and malformed-wire tests;
2. supported-runtime and proxy compatibility;
3. bounded concurrency/load tests with latency and memory observations;
4. CPU and allocation profiles on representative routes;
5. fault injection for abort, timeout, stream, and shutdown paths;
6. security review and threat-model closure; and
7. an operator runbook with rollback and incident procedures.

Benchmark throughput alone cannot satisfy this gate. Until these items are
implemented and independently evaluated in the intended environment, use the
reference only as a learning artifact.
