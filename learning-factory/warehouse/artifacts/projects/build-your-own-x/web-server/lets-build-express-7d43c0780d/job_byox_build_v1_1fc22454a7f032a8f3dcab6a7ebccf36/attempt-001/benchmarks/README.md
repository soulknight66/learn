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

The count must be between 1 and 100,000. Warmup is also bounded (at most 2,000
requests), no network connection is opened, and the process terminates after a
single sample. The script prints live measurements only; no benchmark output is
committed to this repository.

This is a microbenchmark, not a load test or a validation label. Results from
different Node versions, machines, power states, or instrumentation settings
are not directly comparable. See `sealed/exercises/BENCHMARK_INTERPRETATION.md`
for instructor guidance.
