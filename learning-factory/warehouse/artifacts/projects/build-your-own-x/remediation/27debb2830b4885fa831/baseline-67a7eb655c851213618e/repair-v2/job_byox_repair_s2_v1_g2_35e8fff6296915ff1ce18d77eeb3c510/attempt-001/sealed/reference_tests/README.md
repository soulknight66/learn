# Sealed reference tests

`reference.test.mjs` verifies direct language examples, syntax and runtime diagnostics, compiler
shape, tree/VM parity, and malformed-bytecode rejection. `adversarial.test.mjs` concentrates on
state leaks, control-flow edges, hostile opcode values, malformed span records, and accessor-backed
bytecode fields. `learner-view.test.mjs` checks strict path classification, source inventory, and
materialized-view rejection behavior. These are instructor tests and must not be copied into
learner views.

From the repository root:

```bash
node --test sealed/reference_tests/*.test.mjs
```

`benchmark.mjs` is an optional deterministic-workload harness. Its elapsed time is host-dependent;
no stored performance result or benchmark validation label is asserted by this artifact.
