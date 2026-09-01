# Sealed reference tests

This directory contains framework-free tests for the sealed reference implementation. They are not
learner hints and are not part of the public suite. The runner applies both the public contract tests
and these sealed cases to the reference. The sealed cases emphasize constructor validation, aliasing,
idempotence, failure atomicity, deterministic elections, durable lag, recovery, one explicit
transition scenario, and a fixed-seed 1,024-operation trace checked after every operation against a
separate state model. This is deterministic model-based testing, not fuzzing.

On a host with JDK 17 or newer, run from the repository root:

```sh
sh sealed/reference_tests/run.sh
```

The runner compiles only the sealed reference sources, writes classes to a fresh temporary directory,
and removes that directory on exit. Generation-host execution was blocked because `javac` and `java`
were unavailable; see `VALIDATION.md`.
