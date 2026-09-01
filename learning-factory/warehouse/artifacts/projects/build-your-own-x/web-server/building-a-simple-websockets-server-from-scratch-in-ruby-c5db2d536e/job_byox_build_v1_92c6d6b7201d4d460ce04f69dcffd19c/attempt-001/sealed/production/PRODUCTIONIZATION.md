# Productionization assessment

Status: **not productionized**. `MANIFEST.yaml` deliberately records
`productionized: false` and `GENERATED` plus `PARTIAL` labels.

## Blocking gaps

- Put the service behind reviewed TLS termination and define proxy/handoff
  semantics, authentication, authorization, and browser Origin policy.
- Replace or rigorously govern thread-per-client execution. Add callback
  deadlines, cooperative cancellation, backpressure, per-tenant quotas, and
  overload responses.
- Add structured counters for upgrades, active clients, close codes, limit
  rejections, timeouts, callback failures, and shutdown duration. Never label
  handshake keys or message payloads.
- Run independent protocol conformance, cross-version Ruby CI, TCP teardown
  tests, race stress, slowloris and memory-pressure tests, and third-party
  security review.
- Define configuration validation, safe defaults, deployment health probes,
  graceful draining, rolling rollback, dependency/runtime patching, and an
  incident response owner.

## Suggested architecture boundary

Expose the reference protocol engine only behind an adapter that owns TLS,
identity, routing, monitoring, and lifecycle. Give each accepted connection a
fixed byte budget and a cancellation token. Move application work to a bounded
executor while preserving per-connection message order. Treat output queue size
as another admission boundary.

## Evidence still absent

There are no benchmark numbers, profiler captures, fuzzing claims, independent
conformance reports, network-enabled integration results, or operational trial
records in this artifact. The supplied benchmark and adversarial files are
plans or deterministic checks, not fabricated evidence of those gates.

