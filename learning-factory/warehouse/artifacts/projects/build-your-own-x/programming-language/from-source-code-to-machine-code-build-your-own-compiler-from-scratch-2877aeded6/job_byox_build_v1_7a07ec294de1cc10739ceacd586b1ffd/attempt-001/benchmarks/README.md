# Benchmark harness

`benchmark.py` is a reproducible micro-harness for local engineering, not evidence of a benchmark
validation label. It measures compile time and execution time separately with `perf_counter_ns`, uses a
fresh output sink for every execution, warms up once, and reports median nanoseconds as JSON.

Run against whichever implementation is first on `PYTHONPATH`:

```bash
PYTHONPATH=sealed/reference /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 benchmarks/benchmark.py --iterations 7 --loop-count 1000
```

Compare only runs made on the same machine under controlled load. The harness does not measure peak
memory, validation of hostile inputs, startup/import time, output devices, or production workloads.
No threshold or baseline is asserted.
