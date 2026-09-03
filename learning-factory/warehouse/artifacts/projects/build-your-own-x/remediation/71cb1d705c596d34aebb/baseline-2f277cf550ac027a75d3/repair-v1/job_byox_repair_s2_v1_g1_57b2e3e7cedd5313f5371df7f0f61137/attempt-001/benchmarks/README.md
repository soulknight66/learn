# Harness-only benchmark scaffold

`run.py` can measure process/pipeline latency for engineering exploration. It
is intentionally not run as part of correctness validation: wall-clock timing
on a shared host is nondeterministic, no acceptance threshold is specified,
and this artifact does not claim the `BENCHMARKED` label.

```sh
MSH_BIN="$PWD/sealed/reference/msh" python3 benchmarks/run.py --iterations 50
```

Results are printed as JSON with the binary path, iteration count, elapsed
nanoseconds, and host Python version. Redirect output to a separately managed
evidence artifact if a later validator chooses to benchmark.
