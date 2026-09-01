# Deterministic microbenchmark sources

The benchmarks measure only configuration validation and child-argument parsing. They do not create
containers or make performance claims about namespace startup.

```text
go test -run '^$' -bench . -benchmem
```

No benchmark was run on the generator host because Go was unavailable. Results vary by toolchain,
filesystem, CPU, and host load; record those inputs when running them independently.
