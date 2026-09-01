# Benchmark harness

`run.py` is a reproducible microbenchmark driver for comparing candidate shell executables. It reports raw per-iteration wall-clock samples as JSON and makes no performance threshold or production claim.

Example (not part of correctness validation):

```sh
python3 benchmarks/run.py --shell sealed/reference/msh-reference --iterations 20
```

Scenarios measure process startup, a three-stage pipeline, and parser growth. They primarily measure host process creation and utilities, so compare only runs on the same unloaded host with the same compiler and environment. Keep raw output, warmup policy, iteration count, and executable hash when using results.

No benchmark result is checked into this pack and no `BENCHMARKED` label is claimed.
