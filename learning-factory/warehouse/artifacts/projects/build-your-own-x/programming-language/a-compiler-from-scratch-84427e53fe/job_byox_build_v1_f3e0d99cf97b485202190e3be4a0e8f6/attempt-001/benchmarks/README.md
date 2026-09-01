# Benchmark protocol (not executed)

`run.rb` is a reproducible smoke benchmark for compile-plus-execute throughput. It validates the expected output before timing and emits machine-readable JSON with an explicit `UNVALIDATED_MEASUREMENT` label. It is not a statistically rigorous benchmark and was not run during artifact generation.

To measure a completed starter deliberately:

```sh
PEBBLE_LIB=starter/lib ruby benchmarks/run.rb
```

Set `PEBBLE_BENCH_ITERATIONS` to a positive integer to change the default 20 iterations. Record Ruby version, CPU/container limits, warmup policy, command, target revision, and raw samples before making comparisons. The artifact claims no `BENCHMARKED` label.
