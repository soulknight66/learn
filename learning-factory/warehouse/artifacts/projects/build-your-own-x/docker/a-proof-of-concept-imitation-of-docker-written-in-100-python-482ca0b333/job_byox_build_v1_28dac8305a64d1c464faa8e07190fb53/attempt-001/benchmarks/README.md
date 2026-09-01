# Benchmark harness (not executed for labels)

`bench_layer_apply.py` measures repeated application of a synthetic regular-file layer to fresh temporary rootfs directories. It reports actual JSON only when invoked; this artifact contains no fabricated timing or throughput result.

Example:

```bash
PYTHONPATH=sealed/reference python3.11 benchmarks/bench_layer_apply.py --files 100 --bytes-per-file 4096 --repeats 5
```

The harness is a local microbenchmark, not a production workload or `BENCHMARKED` validation label. Filesystem cache and storage backend strongly affect results.
