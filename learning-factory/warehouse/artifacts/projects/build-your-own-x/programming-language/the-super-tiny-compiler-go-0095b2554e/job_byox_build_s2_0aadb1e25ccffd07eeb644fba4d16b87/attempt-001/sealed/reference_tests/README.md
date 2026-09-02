# Reference tests

This sealed module targets `../reference` through a local module replacement. It
covers phase boundaries, byte positions, limits, every built-in, lazy effects,
checked arithmetic, hostile bytecode, deterministic differential generation,
fuzz seeds, and opt-in benchmarks.

Normal deterministic suite:

```bash
go test ./...
```

Optional dynamic campaigns, which must only be claimed when actually observed:

```bash
go test -fuzz=FuzzPipelineNeverPanics -fuzztime=10s
go test -bench=. -benchmem
```

These tests are reference evidence, not learner-visible answers and not a claim
that an independent validator has accepted the artifact.
