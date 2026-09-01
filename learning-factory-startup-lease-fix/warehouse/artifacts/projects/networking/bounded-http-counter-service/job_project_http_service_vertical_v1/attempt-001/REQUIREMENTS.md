# Requirements

## Protocol boundary

Implement an incremental HTTP/1.1 request parser. It must tolerate arbitrary TCP
fragmentation and multiple requests in one read. Require origin-form targets and exactly one
nonempty `Host`; reject obsolete folding, duplicate headers, bare-newline framing, unsupported
versions, and `Transfer-Encoding`. Accept decimal `Content-Length` only. Enforce header and
body bounds before allocating or waiting for unbounded input. Never interpret a partial body
as a complete request.

Responses must include an accurate `Content-Length` and explicit connection policy. Support
bounded keep-alive and close malformed connections after one structured error. This exercise
deliberately omits chunked coding, request trailers, upgrades, TLS, proxies, and HTTP/2; do
not silently pretend those features work.

## Application contract

- `GET /healthz` returns JSON health.
- `GET /metrics` exposes minimal process-local counters.
- `PUT /v1/counters/{name}` accepts exactly `{"value": integer}` and returns a version/ETag.
- `GET /v1/counters/{name}` returns its value and version.
- `DELETE /v1/counters/{name}` removes it.
- `POST /v1/counters/{name}/increment` accepts exactly `{"delta": integer}`.
- A bounded `Idempotency-Key` cache makes repeated increments with the same key and operation
  return the same response without applying twice. Reusing a key for a different counter or
  delta returns deterministic `409 Conflict` rather than another operation's response.
- `If-Match` on PUT prevents stale writers from overwriting a newer version.

Names and integers are bounded. Invalid media types, JSON, methods, routes, and versions must
return stable 4xx results. Internal exception details must not cross the protocol boundary.

## Server/lifecycle contract

Export `ServiceConfig`, `Request`, `Response`, `ProtocolError`, `HTTPParser`, `CounterApp`, and
`Server` from `http_service`. `Server.start()`, `.address`, `.close()`, and context management
form the shared architecture contract. Bind only IPv4 loopback in this pack. Capacity,
queued work, body size, header size, per-connection requests, and read time must be bounded.
Slow partial requests must eventually release capacity. `close()` must actively unblock idle
accepted clients and stop within the configured `shutdown_timeout`, even when `read_timeout`
is longer. The shutdown deadline is a total budget, not a fresh wait for every thread.

## Definition of done

Syntax is not completion. A candidate must pass public and withheld behavioral tests in an
independent implementation path, survive deterministic parser/fault/slow-client probes, and
produce benchmark evidence by actual execution. Record limitations. These bounded checks
remain `PARTIAL`; deployment needs threat modeling, real load tests, persistence decisions,
TLS/proxy policy, telemetry integration, and operational drills.
