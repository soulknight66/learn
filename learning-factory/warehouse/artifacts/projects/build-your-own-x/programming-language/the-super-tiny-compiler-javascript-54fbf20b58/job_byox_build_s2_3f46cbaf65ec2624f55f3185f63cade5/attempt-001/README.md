# The Super Tiny Compiler: build Ripple

Ripple is a deliberately small expression language. Your task is to implement its complete toolchain in dependency-free JavaScript: scanner, recursive-descent parser, semantic checker, optimizer, JavaScript emitter, and tree-walking interpreter.

This is a challenge repository, not a tutorial dump. The public contract is precise enough to implement independently, while later material can be revealed by the learning harness. The linked catalog project is provenance only; Ripple has its own grammar and design.

## Quick start

Use Node.js 18 or newer. No package installation is required.

```text
node --test public_tests/compiler.test.js
```

Implement `starter/compiler.js`. A tiny Ripple program looks like this:

```ripple
let radius = 4;
let area = 3.14 * pow(radius, 2);
emit area;
emit "done";
```

Read these in order:

1. `REQUIREMENTS.md` defines observable behavior and diagnostics.
2. `CONCEPTS.md` gives non-solution background.
3. `starter/README.md` divides the work into milestones.
4. `public_tests/` provides the learner-visible checks.
5. `DESIGN_QUESTIONS.md` asks you to justify choices after implementation.

## Completion target

A complete submission tokenizes with source locations, parses precedence correctly, rejects invalid bindings and calls, preserves behavior through optimization and code generation, and interprets without evaluating generated JavaScript. It should produce stable structured errors for bad input.

Local success is not a validation label. The manifest intentionally remains `GENERATED` + `PARTIAL`; an independent harness controls all stronger labels.
