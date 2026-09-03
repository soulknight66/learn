# Sealed reference implementation

This directory contains the instructor reference for the independently designed Mica language. It
is an ES-module implementation with separate lexer, parser, semantic helpers, tree evaluator,
compiler, VM, pipeline, and CLI modules under `src/`.

Run only in an instructor context, from the repository root:

```bash
node --test sealed/reference_tests/*.test.mjs
node sealed/reference/src/cli.mjs --backend vm program.mica
```

The code has no third-party dependencies and performs no network or subprocess operations. It is a
teaching reference, not a claim of production readiness.
