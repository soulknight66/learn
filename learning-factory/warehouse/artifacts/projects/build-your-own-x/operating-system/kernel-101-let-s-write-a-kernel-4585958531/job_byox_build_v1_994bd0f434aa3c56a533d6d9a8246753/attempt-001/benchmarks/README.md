# Benchmark harness

`bench_core.c` is an optional micro-workload for comparing completed frame and filesystem operations.
It has no pass threshold and is not evidence of whole-kernel performance. Build it with:

```sh
make -C benchmarks SOURCE_DIR=../sealed/reference build
./benchmarks/build/bench_core
```

Elapsed `clock()` ticks are host- and load-dependent. `VALIDATION.md` records one raw generation-host
sample only; it is not a benchmark validation label. Independent validators should record compiler
flags, host details, raw output, and repeated samples if they choose to assess performance.
