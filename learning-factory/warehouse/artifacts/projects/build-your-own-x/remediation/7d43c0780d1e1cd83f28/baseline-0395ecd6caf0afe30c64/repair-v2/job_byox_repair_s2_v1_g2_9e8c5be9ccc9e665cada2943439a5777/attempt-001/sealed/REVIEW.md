# Reference repair review

Review scope: all files under `sealed/reference/`, the supplied tests, and the learner-view
projection. This production-builder review is not independent acceptance evidence.

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
- Terminal routing checks membership of the current method in `Allow`; matching GET/HEAD handlers
  that fall through now end as 404, while unsupported methods retain 405.
- JSON parsing checks recorded abort, pre-end close/destruction, and stream-error state both before and
  immediately after listener installation.
- Public concurrency coverage uses explicit request gates and asserts independent parameters,
  bodies, statuses, and headers.
- `environment/learner_view.py` selects only the authoritative learner roots, rejects special and
  extra entries, and verifies copied bytes. The builder did not create a learner workspace; an
  external harness must run and inventory the actual transfer view.

## Residual risks

- Node.js 22.21.0 executed syntax checks and five socket-free JavaScript regressions. This sandbox
  denied loopback listeners with `EPERM`, so `node:http` integration and real-socket abort behavior
  still require an independent network-capable validator on every supported Node line.
- Linear routing and per-request wrapper creation have not been benchmarked.
- No slow-client deadlines, header timeouts, graceful shutdown coordinator, logging, metrics, proxy
  trust policy, or distributed tracing are provided.
- Draining an over-limit body allows the connection to remain reusable but still consumes bandwidth.
- Unicode normalization is intentionally not performed; visually similar paths remain distinct.
- The implementation is educational and is not asserted to be production-ready.
- The manifest's immutable provenance link is not a whole-pack digest. The factory, not this pack,
  supplies the content-addressed artifact inventory.

## Independent review checklist

Run the public, reference, regression, and raw-socket suites; add conflicting-framing cases; fuzz
pattern registration and encoded request-targets; inspect active handles; and load-test on loopback
while tracking latency and memory. Materialize and validator-inventory the learner view before
transfer. Promotion labels must come from that independent evidence, not from this review.
