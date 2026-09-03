# Sealed reference tests

`reference.test.mjs` verifies direct language examples, syntax and runtime diagnostics, compiler
shape, tree/VM parity, and malformed-bytecode rejection. `adversarial.test.mjs` concentrates on
state leaks and control-flow edges. These are instructor tests and must not be copied into learner
views.

From the repository root:

```bash
node --test sealed/reference_tests/*.test.mjs
```

`benchmark.mjs` is an optional deterministic-workload harness. Its elapsed time is host-dependent;
no stored performance result or benchmark validation label is asserted by this artifact.
