# Sealed benchmark harness

`benchmark.mjs` uses the same harness-controlled binding as the adversarial
suite. It fingerprints the fixed learner and oracle trees, prepares deterministic
arithmetic, loop, and branch workloads, runs candidate and oracle separately,
checks both backends against expected observations and one another, and only then
measures namespaced candidate and oracle operations.

From the repository root on a host with Node.js:

```sh
node sealed/benchmarks/benchmark.mjs
node sealed/benchmarks/benchmark.mjs --samples 15 --iterations 100 --warmup 25
```

The command writes the artifact-identity event to standard error before any
correctness gate and writes a JSON report to standard output after successful
measurement. Redirect it to a dated
artifact if results need to be retained, and record the commit plus machine load
alongside it. Do not commit a generated report as universal performance
evidence.

The repair host did not provide Node.js, so no command was run and no timing
claim is made. The harness itself still requires independent validation before
use. It intentionally reports raw per-sample durations as well as summaries so
that suspicious distributions are not hidden behind one aggregate.
