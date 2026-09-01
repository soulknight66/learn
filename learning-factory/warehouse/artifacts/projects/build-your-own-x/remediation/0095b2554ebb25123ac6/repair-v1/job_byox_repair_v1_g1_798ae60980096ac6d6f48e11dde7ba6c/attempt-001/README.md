# Pebble: a tiny compiler challenge in Go

Build a complete compiler pipeline for **Pebble**, a deliberately small prefix-expression language. Your implementation will scan source text, construct a positioned abstract syntax tree, perform name analysis, emit stack-machine bytecode, validate that bytecode, and execute it in a virtual machine.

This is a standalone challenge inspired only by the catalog topic “The Super Tiny Compiler.” It does not reproduce the linked tutorial. The production archive records the immutable source metadata and reuse boundary in `PROVENANCE.json` and `LICENSE_BOUNDARY.md`; those evaluator records are deliberately omitted from the constructed learner view.

## What you build

Pebble accepts programs such as:

```text
(let width 6)
(let height (+ width 4))
(print (* width height))
```

The observable output is the integer sequence `[60]`. The compiler must reject malformed tokens, malformed syntax, undefined or redeclared names, invalid bytecode, division by zero, and arithmetic overflow with useful stage and source-position information.

The public API and buildable scaffolding live in `starter/`. The behavioral contract is in `REQUIREMENTS.md`. `CONCEPTS.md` supplies background without implementation answers, and `DESIGN_QUESTIONS.md` asks the decisions you should be able to defend. Public black-box tests are in `public_tests/`.

## Suggested progression

1. Scanner and source spans.
2. Parser and AST shape.
3. Static name analysis and deterministic slot assignment.
4. Bytecode generation.
5. Bytecode validation and VM execution.
6. End-to-end diagnostics and robustness.

With Go 1.21 or newer available:

```bash
cd starter && go test ./...
cd ../public_tests && go test ./...
```

The starter intentionally returns `NOT_IMPLEMENTED` from core stages, so its API/scaffolding tests pass while the public behavioral suite is expected to fail until you implement the stages. The permanent starter tests do not require stub behavior and remain satisfiable by a completed implementation. No third-party modules are required. This build host did not expose a Go executable; the production validation record captures that limitation. Independent validation is mandatory.

## Completion target

Treat all requirements marked **MUST** as mandatory. Preserve the exported starter API. A good submission passes public tests plus harness-controlled tests that probe error precedence, positions, integer boundaries, bytecode tampering, stack safety, determinism, and concurrent use. Passing only the examples is not sufficient.
