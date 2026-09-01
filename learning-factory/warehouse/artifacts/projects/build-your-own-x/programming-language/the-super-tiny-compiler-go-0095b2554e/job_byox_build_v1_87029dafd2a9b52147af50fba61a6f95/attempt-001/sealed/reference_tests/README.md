# Sealed reference tests

This independent module imports only `example.com/pebble-reference` through a local replacement. It contains black-box pipeline tests, hostile exported-value tests, fuzz targets, and benchmarks.

Intended commands with Go 1.21+:

```bash
GOTOOLCHAIN=local go test ./...
GOTOOLCHAIN=local go test -race ./...
GOTOOLCHAIN=local go test -fuzz=FuzzExecuteNeverPanics -fuzztime=10s
GOTOOLCHAIN=local go test -run '^$' -bench=. -benchmem
```

These commands were not executed during generation because this host had no Go executable. In particular, the presence of fuzz and benchmark functions does not earn `FUZZED` or `BENCHMARKED`; only independently observed runs can do that.
