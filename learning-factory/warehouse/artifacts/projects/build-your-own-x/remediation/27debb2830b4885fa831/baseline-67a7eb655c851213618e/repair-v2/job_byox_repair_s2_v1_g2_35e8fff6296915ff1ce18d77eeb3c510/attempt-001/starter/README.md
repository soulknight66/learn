# Starter guide

The starter deliberately gives you the lexical layer and leaves four implementation stages. All
files are ES modules, and there are no install steps.

## Suggested order

1. Implement `parse` in `src/parser.mjs`. Start with literals and precedence, then statements,
   blocks, and assignment. Preserve token-derived spans.
2. Implement `interpret` in `src/interpreter.mjs` with a scope stack and centralized value rules.
3. Implement `compile` in `src/compiler.mjs`. Document stack effects while adding opcodes, and patch
   forward jumps only after their destination is known.
4. Implement `run` in `src/vm.mjs`. Treat chunks as untrusted data: check opcode names, operands,
   stack depth, jump targets, and lexical-scope balance.
5. Use `src/pipeline.mjs` and public parity tests to compare backends.

Each unfinished export currently throws an error beginning with `TODO`. Replace that error; do not
change the public signature. The supplied lexer is part of the starter rather than a hidden answer,
so you may refactor it while retaining its observable contract.

Run from the repository root:

```bash
node --test public_tests/*.test.mjs
node starter/src/cli.mjs --backend tree starter/example.mica
```

The supplied `example.mica` is input data, not implementation code. The CLI command reaches an
explicit `TODO` until the tree backend is implemented. An untouched checkout has passing lexical
tests and failing later-stage tests. That failure is an intentional starting state, not evidence
that the test runner is broken.
