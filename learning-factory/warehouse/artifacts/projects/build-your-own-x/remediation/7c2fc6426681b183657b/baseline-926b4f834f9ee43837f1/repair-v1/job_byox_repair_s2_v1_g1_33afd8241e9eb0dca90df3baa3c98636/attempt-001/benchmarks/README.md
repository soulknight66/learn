# Benchmark harness

`run.py` measures whole-process execution of a generated definition-and-evaluation workload. It uses
argv-based subprocesses, captured streams, a timeout, one unreported warmup, and reports nanoseconds
as JSON labeled `UNVALIDATED_MEASUREMENT`.

Example (not run as artifact validation):

```text
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 benchmarks/run.py /path/to/cinder
```

No benchmark result is checked in, and no `BENCHMARKED` claim is made. Process startup and host load
dominate small settings; use pinning, environment disclosure, repeated independent runs, and a
separate VM-only harness before drawing performance conclusions.
