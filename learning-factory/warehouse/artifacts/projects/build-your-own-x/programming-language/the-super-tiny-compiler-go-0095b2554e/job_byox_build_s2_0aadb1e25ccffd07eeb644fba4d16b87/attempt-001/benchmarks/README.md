# Benchmark protocol

Benchmarks are opt-in evidence, never inferred from ordinary tests. The sealed
suite defines tokenizer and compile-plus-run benchmarks with deterministic
inputs. On a host with Go, run from `sealed/reference_tests`:

```bash
go test -run='^$' -bench=. -benchmem -count=5
```

Record the exact Go version, OS/architecture, CPU identity, power/container
constraints, command, all samples, and whether output is warm-cache. Compare
distributions rather than a single best value. Do not commit invented numbers or
label this pack `BENCHMARKED` merely because benchmark functions exist.
