# Learner-side agent rules

These rules govern learners and coding agents implementing the learner submission. Reference builders and independent validators explicitly assigned to evaluator material may inspect `sealed/` for that work; they must never move its contents into learner-visible paths.

## Scope

Implement the learner solution only under `starter/`. You may add tests under `starter/test/`, but do not weaken, delete, or rewrite `public_tests/`. Learner-side work must not inspect or modify `sealed/` or factory-control files.

## Constraints

- Use Node.js built-ins only; do not add third-party runtime packages.
- Preserve the CommonJS entry point and public API specified in `REQUIREMENTS.md`.
- Never use `eval`, dynamic code generation, shell command strings, or global request state.
- Bound request-body experiments and test timeouts. Close every server opened by a test.
- Treat URL text, route parameters, header values, and handler errors as untrusted input.
- Do not commit credentials, environment files, generated dependency trees, coverage output, or benchmark output.

## Workflow

Run commands from the repository root:

```bash
node --test public_tests/*.test.js
```

Keep changes small and use the test-name filter described in `README.md` to work one capability at a time. Record design decisions in your own notes or in a copy of `DESIGN_QUESTIONS.md`; the questions are part of assessment and have no learner-visible answer key.

Passing visible tests is not evidence of completion. Check every requirement, especially double `next()` calls, rejected promises, malformed percent encoding, `HEAD`, response finalization, and concurrent request isolation.
