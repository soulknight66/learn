# Static review of the reference

Review scope: all files under `sealed/reference/` and the supplied tests. This is a source review,
not an executed validation result; Node.js was unavailable on the generation host.

## Findings addressed in the implementation

- Request state is allocated inside `handle` or route invocation, never in a module-level “current
  request” slot.
- Route compilation validates parameter names and duplicate names before accepting a layer.
- Middleware mount matching uses a slash boundary rather than raw `startsWith`.
- Body limits are checked both from the header and for every incoming chunk.
- Body stream listeners are removed on success, limit, abort, and stream error paths.
- Response byte counts use Buffer length, preserving multibyte correctness.
- Error messages default closed for 5xx status and unsafe framing headers are not copied.
- The server callback observes the promise returned by `handle`.

## Residual risks

- Runtime behavior has not been observed here. Version-specific `node:http` handling, socket-abort
  timing, and syntax must be checked independently on Node.js 18 or newer.
- Linear routing and per-request wrapper creation have not been benchmarked.
- No slow-client deadlines, header timeouts, graceful shutdown coordinator, logging, metrics, proxy
  trust policy, or distributed tracing are provided.
- Draining an over-limit body allows the connection to remain reusable but still consumes bandwidth.
- Unicode normalization is intentionally not performed; visually similar paths remain distinct.
- The implementation is educational and is not asserted to be production-ready.

## Independent review checklist

Run both suites, then add raw-socket cases for aborted and conflicting framing, fuzz pattern
registration and encoded request-targets, inspect active handles after tests, and load-test on
loopback while tracking latency and memory. Promotion labels must come from that independent
evidence, not from this review.
