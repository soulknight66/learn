# Benchmark harness

This evaluator-side microbenchmark times pure plan construction and a complete SQLite lifecycle in
a temporary directory. It is exploratory, not a production capacity test: it has no warmup policy,
confidence interval, concurrent writers, kernel launch, I/O isolation, or fixed CPU allocation.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference \
  python3 benchmarks/benchmark_reference.py --iterations 100
```

Do not infer throughput or set a `BENCHMARKED` label from one run. Exact observed output, if the
harness is run during generation, belongs in `VALIDATION.md` with these limitations.
