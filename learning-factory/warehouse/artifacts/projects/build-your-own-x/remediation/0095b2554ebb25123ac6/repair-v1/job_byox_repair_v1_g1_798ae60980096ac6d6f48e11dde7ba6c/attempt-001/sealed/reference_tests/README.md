# Sealed oracle self-tests

This module imports only `example.com/pebble-reference` through a local replacement. It contains black-box pipeline tests, hostile exported-value tests, fuzz targets, and benchmarks for assessing the supplied oracle. It does **not** validate a learner submission and is never counted as learner acceptance evidence. Candidate-targeted tests live separately in `sealed/learner_tests/` and are retargeted by `sealed/validation/run_learner_validation.py`.

Intended commands with Go 1.21+:

```bash
GOTOOLCHAIN=local go test ./...
GOTOOLCHAIN=local go test -race ./...
GOTOOLCHAIN=local go test -fuzz=FuzzExecuteNeverPanics -fuzztime=10s
GOTOOLCHAIN=local go test -run '^$' -bench=. -benchmem
```

The bytecode fuzz target derives opcodes, operands, source spans, and slot counts from independent fuzz arguments and includes structurally valid halt and push/pop/halt seeds. These commands were not executed during repair because this host had no Go executable. In particular, the presence of fuzz and benchmark functions does not earn `FUZZED` or `BENCHMARKED`; only independently observed runs can do that.
