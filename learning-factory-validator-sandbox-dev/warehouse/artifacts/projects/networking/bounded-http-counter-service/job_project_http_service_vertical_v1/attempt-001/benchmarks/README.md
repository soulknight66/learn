# Benchmark

`benchmark.py` starts each architecture on IPv4 loopback, verifies a warm-up, then records raw
nanosecond samples for sequential and four-way burst health requests. It writes machine,
interpreter, workload, hypothesis, raw samples, summaries, and an interpretation boundary.

```sh
python3 benchmarks/benchmark.py --requests 40 --concurrency 4           --output benchmarks/results/smoke.json
```

The generated pack intentionally contains no result file before execution. Do not compare a
single smoke ratio as a capacity claim. Repeat runs, add confidence intervals, saturate queues,
vary keep-alive and handler cost, and profile before drawing an architecture conclusion.
