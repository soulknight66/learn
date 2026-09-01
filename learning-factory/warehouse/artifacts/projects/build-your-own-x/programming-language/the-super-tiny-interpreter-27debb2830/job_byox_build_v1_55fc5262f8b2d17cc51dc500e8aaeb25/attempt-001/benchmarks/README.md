# Benchmark harness

`run.mjs` compares the two engines on one deterministic loop workload after warmup. It reports raw
sample durations and runtime metadata as JSON; it does not declare winners or readiness.

Run from the repository root after implementing the starter:

```sh
node benchmarks/run.mjs
```

An optional first argument is an implementation module path relative to `benchmarks/run.mjs`. The
module must export `execute`. Use a dedicated idle machine, retain the JSON output with commit and
hardware provenance, and compare distributions rather than a single sample.

No benchmark was run during generation because the host had no compatible Node.js runtime. No performance
numbers are claimed.
