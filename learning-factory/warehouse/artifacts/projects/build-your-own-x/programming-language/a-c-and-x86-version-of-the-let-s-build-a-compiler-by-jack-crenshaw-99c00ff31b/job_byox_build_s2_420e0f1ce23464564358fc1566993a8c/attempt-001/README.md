# Pebble: a tiny C interpreter and x86-64 compiler

Pebble is a from-scratch learning challenge about implementing the same small
language twice: first as a tree-walking interpreter, then as a compiler that
emits GNU/AT&T x86-64 assembly. The language has integer expressions,
variables, output, conditionals, and loops. Its deliberately small surface area
lets you focus on tokenization, precedence parsing, semantic checks, execution,
and the System V AMD64 calling convention.

The linked catalog item is provenance only. This repository was independently
written and does not reproduce the linked tutorial.

## Progression

1. Read [REQUIREMENTS.md](REQUIREMENTS.md) for the observable contract.
2. Study [CONCEPTS.md](CONCEPTS.md), then answer the questions in
   [DESIGN_QUESTIONS.md](DESIGN_QUESTIONS.md).
3. Complete the TODOs in `starter/`. Keep the interpreter and compiler behind
   the supplied command-line interface.
4. Run `make -C starter` and then `python3 public_tests/run_tests.py`.
5. Add your own negative and differential tests. The public suite is only a
   smoke test; independent validation is required.

The starter intentionally builds but reports that its language pipeline is not
implemented. A complete implementation and stronger tests are sealed from the
learner view.

## CLI contract

```text
starter/pebble eval [--max-steps N] PROGRAM.pb
starter/pebble compile PROGRAM.pb -o PROGRAM.s
```

`eval` executes a source file. `compile` writes x86-64 assembly which can be
linked with `cc PROGRAM.s -o PROGRAM`. See `starter/examples/count.pb` for a
small input program.

## Repository boundary

Learner-facing content is confined to this file, `AGENTS.md`, `MANIFEST.yaml`,
`REQUIREMENTS.md`, `CONCEPTS.md`, `DESIGN_QUESTIONS.md`, `starter/`,
`public_tests/`, and `environment/`. Material under `sealed/` is validator-only.
The generated status is `PARTIAL`: local evidence is recorded, but no claim of
production readiness or independent validation is made.
