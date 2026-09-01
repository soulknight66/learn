# Benchmark harness (unexecuted)

`BenchmarkMain.java` is a deterministic micro-harness for exploratory compiler
throughput. It warms up, compiles the same generated 200-statement program 200
times, checks successful outputs for byte equality, and reports elapsed
nanoseconds plus an output digest. It does not claim statistically rigorous
results and was not run on the generation host because Java is unavailable.

On a Java 17+ JDK, use `./sealed/run-benchmark.sh`. Treat any result as local
diagnostic evidence only: record JVM version, CPU/container limits, warmup,
sample count, source digest, and full command. Use JMH before making comparative
performance claims; do not award `BENCHMARKED` from this harness alone.

