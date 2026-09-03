# Mica: a tiny language from source to bytecode

This repository is a dependency-free JavaScript challenge about building a small programming
language. The language is called **Mica**. Its surface area is deliberately compact, but the project
still crosses the important boundaries: tokenization, recursive-descent parsing, tree-walk
evaluation, bytecode generation, and execution on a stack virtual machine.

This is independently generated educational material. The catalog link recorded in
`PROVENANCE.json` identifies the topic that inspired the assignment; no linked tutorial text or
code was copied into this pack.

## How to work through it

1. Read `REQUIREMENTS.md` for the observable language and API contracts.
2. Read `CONCEPTS.md` for implementation techniques without code-level answers.
3. Start in `starter/src/`. The lexer and diagnostics are supplied; the parser, interpreter,
   compiler, and VM contain explicit completion points.
4. Run the public tests frequently. They are examples, not an exhaustive validator.
5. Answer `DESIGN_QUESTIONS.md` as you make representation and error-handling choices.
6. Treat every directory named `sealed` as instructor-only material.

The intended progression is parser → tree interpreter → compiler → VM → parity hardening. Keep the
tree and bytecode backends behaviorally identical for every valid program and for documented error
classes.

## Running the challenge

With Node.js 22 or another current Node.js release:

```bash
node --test public_tests/*.test.mjs
node starter/src/cli.mjs --backend tree examples.mica
node starter/src/cli.mjs --backend vm examples.mica
```

No package installation is required. The starter is intentionally incomplete, so the untouched
baseline does not pass the whole public suite. That is why this generated artifact remains marked
`PARTIAL`; only an independent harness may award stronger validation labels.

## Completion target

A completed submission should:

- accept the full grammar and reject malformed input with stable diagnostic codes and spans;
- implement lexical block scope, nearest-scope assignment, and the specified value rules;
- produce the same result, output, and runtime-error code from both execution backends;
- compile control flow with validated jump targets and finish with exactly one result value;
- add focused tests without placing answers or solution code in learner-visible documentation.

See `LICENSE_BOUNDARY.md` for the provenance and reuse boundary.
