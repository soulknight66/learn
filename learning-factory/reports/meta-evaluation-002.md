# Meta-evaluation 002 — bounded HTTP service pack

Date: 2026-08-30

Scope: independent adversarial review of the generated bounded HTTP/1.1 counter-service
challenge before durable publication.

## Defects found before publication

1. The event-loop architecture dispatched two pipelined requests when the configured
   per-connection budget was one; the other two architectures stopped at one.
2. Reusing an idempotency key for a different counter returned the first counter's
   cached response and failed to apply the second operation.
3. Worker-pool shutdown used a fixed two-second join even though a valid client read
   timeout could be longer, allowing a partial client to make `close()` fail.

The original generated validator set passed despite these defects. The artifact was
therefore withheld rather than promoted.

## Corrections and regression evidence

- All three architectures now enforce the request budget before dispatching additional
  pipelined requests. A real-socket regression observes exactly one response for a budget
  of one in the worker-pool, bounded-thread-per-connection, and event-loop variants.
- Idempotency entries bind the key to the operation fingerprint. Reuse for another
  resource or delta returns `409 Conflict` and cannot reveal another operation's response.
- Shutdown has an explicit bounded total budget and actively unblocks accepted sockets.
  A regression uses a 3-second read timeout and a 0.75-second shutdown budget; the
  reference closes in approximately 0.05 seconds in the review probe.

The corrected focused suite passed five consecutive runs. The scheduled artifact then
passed 20/20 independent validators and was published with framed checksum
`3b8e2a403082ae3ee92806a0692f74d43df4c08f5d58f492eb08407990c230f9`.

The validation run also produced measured loopback results for 40 requests at concurrency
four: event-loop 3078.78 requests/s, worker pool 2254.88 requests/s, and bounded
thread-per-connection 1897.97 requests/s. These are raw results from this host and workload,
not universal architecture rankings; the full nanosecond samples and environment remain in
`benchmarks/results/smoke.json` inside the artifact.

## Judgment

The pack is useful for production-engineering study because it preserves three comparable
architectures, public and withheld tests, parser adversaries, slow-client and fault tests,
one proven debugging challenge, one review exercise, and actual benchmark evidence. It is
correctly labeled `PARTIAL` and `NOT_PRODUCTION_READY`: persistence, authentication,
multi-process coordination, richer telemetry, deployment, and security hardening remain
explicit non-goals.
