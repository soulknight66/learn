# Bounded router microbenchmark

`router-benchmark.js` measures synchronous in-process dispatch through one
mounted middleware, a literal route, and a parameterized route with duplicate
query keys. It uses a small ServerResponse-compatible sink so socket and parser
cost do not dominate the router measurement.

From the repository root:

```bash
node benchmarks/router-benchmark.js
```

The default target is `sealed/reference/src/index.js` and the default measured
request count is 20,000. A different CommonJS implementation and count can be
provided explicitly:

```bash
node benchmarks/router-benchmark.js starter/src/index.js 50000
```

The count must be between 1 and 100,000. Warmup is capped at 2,000 requests and
no network connection is opened, but the in-process iteration caps cannot stop
a target that never returns synchronously. Run untrusted targets with an outer
wall-clock and output boundary:

```bash
python3 environment/run-bounded.py 30 -- node benchmarks/router-benchmark.js starter/src/index.js 20000
```

The wrapper terminates the process group after 30 seconds and captures at most
2 MiB of combined output. The benchmark prints live measurements only; no
benchmark output is committed to this repository.

This is a microbenchmark, not a load test or a validation label. Results from
different Node versions, machines, power states, or instrumentation settings
are not directly comparable. See `sealed/exercises/BENCHMARK_INTERPRETATION.md`
for instructor guidance.
