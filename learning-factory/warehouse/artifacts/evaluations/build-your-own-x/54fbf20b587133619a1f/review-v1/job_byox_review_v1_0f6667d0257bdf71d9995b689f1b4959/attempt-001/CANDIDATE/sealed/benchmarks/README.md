# Sealed benchmark harness

`benchmark.mjs` prepares deterministic arithmetic, loop, and branch workloads;
checks their expected observations through both backends; and only then measures
isolated stages and end-to-end pipelines.

From the repository root on a host with Node.js:

```sh
node sealed/benchmarks/benchmark.mjs
node sealed/benchmarks/benchmark.mjs --samples 15 --iterations 100 --warmup 25
```

The command writes a JSON report to standard output. Redirect it to a dated
artifact if results need to be retained, and record the commit plus machine load
alongside it. Do not commit a generated report as universal performance
evidence.

The authoring host did not provide Node.js, so no command was run and no timing
claim is made. The harness itself still requires independent validation before
use. It intentionally reports raw per-sample durations as well as summaries so
that suspicious distributions are not hidden behind one aggregate.
