# Benchmark boundary

No performance result is stored and no `BENCHMARKED` label is claimed. The optional instructor
harness is `sealed/reference_tests/benchmark.mjs`. It performs 10,000 parses and executions per
backend and prints elapsed wall time plus a checksum.

Meaningful measurement would need declared hardware, Node version, warmup, repetitions, variance,
and separate parse/compile/execute workloads. Running the optional script once is a smoke
measurement, not production evidence.
