# Benchmarks

Benchmark code and methodology are sealed because they exercise the reference implementation. The deterministic driver is `sealed/benchmarks/compiler.bench.js`.

On Node.js 18+ run:

```text
node sealed/benchmarks/compiler.bench.js 200 25
```

Arguments are declarations per generated program and timed iterations. The driver performs five untimed warmups, checks each result, and reports JSON containing runtime identity plus tokenize/parse, optimized compile, interpret, and generated-execution durations. It uses a fixed generated program and monotonic `hrtime.bigint`.

No benchmark was run on the generation host because Node.js was unavailable. There are intentionally no claimed timings or `BENCHMARKED` label.
