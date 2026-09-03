# Ember-C: a tiny C interpreter with a self-interpretation tower

Ember-C is a build-it-yourself challenge about the smallest useful slice of C:
lex it, parse it, compile it to a documented stack bytecode, and execute that
bytecode safely.  The final milestone writes a bytecode interpreter *in the
guest language* and uses it to execute its own compiled bytecode.

This is an independent educational project.  It does not contain or mirror the
linked catalog tutorial.  Ember-C is intentionally not ISO C; the exact subset
is specified in [REQUIREMENTS.md](REQUIREMENTS.md).

## Reveal order

1. Read `REQUIREMENTS.md` and `CONCEPTS.md`.
2. Build `starter/` and run the lexer smoke test.
3. Implement expressions, statements, bytecode patching, and the VM.
4. Run `public_tests/` against your executable.
5. Answer `DESIGN_QUESTIONS.md`, then attempt the tower milestone.

The `sealed/` tree is validator-owned and is not learner material.  It contains
the independent reference, private tests, review notes, and design answers.
Publication must use a factory-validated learner projection containing only the
documented learner-visible paths; distributing this full builder archive would
disclose the sealed oracle.

## Starter quick start

```sh
make -C starter
starter/build/emberc --tokens public_tests/cases/precedence.ec
MICROC_BIN="$PWD/starter/build/emberc" public_tests/run.sh
```

The starter intentionally implements tokenization only.  `--check` and normal
execution return a clear `not implemented` diagnostic until you complete the
compiler and VM.  Therefore the full public suite initially fails by design.

## Completion target

A conforming submission:

- builds without warnings under the documented C17 command;
- accepts exactly the grammar and deterministic limits in `REQUIREMENTS.md`;
- produces stable diagnostics and never invokes undefined signed arithmetic;
- passes the public suite plus independent tests; and
- can run the tower program described by the bytecode ABI.

Generated status is `GENERATED` + `PARTIAL`.  No claim in this repository is a
validation label; only the learning-factory validators can promote it.
