# Learner-side agent rules

These rules govern learners and coding agents implementing the learner submission. Reference builders and independent validators explicitly assigned to evaluator material may inspect the full production pack for that work; they must never move evaluator contents into learner-visible paths.

## Scope

Implement the learner solution only under `starter/`. You may add tests under `starter/test/`, but do not weaken, delete, or rewrite `public_tests/`. A valid learner workspace is created from the exact policy in `environment/learner-view-policy.json`; evaluator roots such as `sealed/`, `adversarial/`, `debugging/`, `review_exercises/`, and `benchmarks/` must be absent. Their presence is a delivery failure, not permission to inspect them.

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

Keep changes small and use the test-name filter described in `README.md` to work one capability at a time. Record design decisions in `starter/DESIGN_QUESTIONS.md`; the root file is the read-only prompt.

Passing visible tests is not evidence of completion. Check every requirement, especially double `next()` calls, rejected promises, malformed percent encoding, `HEAD`, response finalization, and concurrent request isolation.
