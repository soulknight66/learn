# Deterministic adversarial harness

`test_stress.c` drives fixed-seed mixed byte streams through the reference decoder, small guarded
terminal surfaces, and a model-checked queue. It checks invariants and memory boundaries; it is not a
coverage-guided fuzzer and no `FUZZED` label is claimed.

```sh
make -C sealed/adversarial run
make -C sealed/adversarial sanitize
```
