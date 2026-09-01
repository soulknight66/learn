# Benchmark plan

Executable benchmark functions live in `sealed/reference_tests/benchmark_test.go`. They separately measure scanning, complete building, and repeated validated execution on a deterministic 500-statement expression program, with allocation reporting.

Intended command:

```bash
cd sealed/reference_tests
GOTOOLCHAIN=local go test -run '^$' -bench=. -benchmem -count=5
```

No benchmark was run during generation because Go was unavailable. Consequently this artifact contains no timings, allocation counts, comparisons, or `BENCHMARKED` claim. A future report should preserve Go version, architecture, OS, command, repetitions, raw output, and whether CPU scaling/noise was controlled.
