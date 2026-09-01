# Benchmark interpretation guide

The router microbenchmark deliberately measures a narrow path: allocation and
dispatch for alternating literal and parameterized GET requests, one mounted
middleware, query parsing, and response-helper serialization into an in-memory
sink. The checksum makes accidental removal of all response work visible, but
is not a proof that every response is correct.

Do not record or compare only requests per second. For a useful local
investigation, retain:

- the exact commit or artifact under test;
- Node.js version and runtime flags;
- CPU/machine identity and power-management conditions;
- iteration and warmup counts; and
- multiple independently started process samples with their distribution.

Compare implementations only under the same conditions. A speed difference
smaller than ordinary run-to-run variation is inconclusive. First use contract
tests to reject incorrect implementations; an implementation that skips
decoding, isolation, error handling, or response work is not a valid faster
alternative.

This benchmark says nothing about HTTP parsing, sockets, keep-alive behavior,
TLS, streaming, backpressure, tail latency under concurrency, memory retention,
or overload behavior. A production performance study would need bounded load
generation, latency percentiles, resource telemetry, profiles, and correctness
checks during load. No such production study or production-readiness claim is
made here.
