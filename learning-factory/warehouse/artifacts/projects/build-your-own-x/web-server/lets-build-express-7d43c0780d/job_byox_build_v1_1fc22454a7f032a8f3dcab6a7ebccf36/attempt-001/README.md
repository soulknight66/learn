# Build a Tiny Express-Style HTTP Framework

This challenge asks you to build a small web framework directly on Node.js's `http` module. The goal is not API parity with Express. It is to understand the machinery underneath a familiar middleware-and-routing interface: request dispatch, path matching, error flow, response finalization, and isolation between concurrent requests.

The project has no runtime dependencies. Use Node.js 18.17 or newer and work only in `starter/`; `environment/` records the exact reference runtime.

## Progressive path

1. Read `REQUIREMENTS.md` sections 1–3 and make the application callable as an HTTP request listener.
2. Implement normal and error middleware dispatch, including path-prefix boundaries.
3. Add method routing, parameters, and the terminal wildcard.
4. Decorate requests and implement the response helpers.
5. Make promise rejection, `HEAD`, malformed inputs, and default 404/500 behavior deterministic.
6. Run the concurrency cases and audit every piece of mutable state for request isolation.

`CONCEPTS.md` explains the underlying Node.js and HTTP ideas without giving an implementation. `DESIGN_QUESTIONS.md` is a decision log to complete as you work.

## Run the learner checks

From this repository root:

```bash
node --test public_tests/*.test.js
```

The starter is intentionally incomplete, so the complete public suite is expected to fail at first. The test names are ordered to support incremental work. A useful loop is:

```bash
node --test --test-name-pattern="application" public_tests/*.test.js
```

Consult `public_tests/README.md` for test scope and `environment/README.md` for supported-host checks.

## Boundaries

- Do not add Express or another router; the dispatch machinery is the subject of the exercise.
- Treat the public tests as examples, not a full specification. The written requirements are authoritative.
- Do not inspect or modify `sealed/`. It contains evaluator-only reference and review material.
- No claim in this repository replaces independent validation. The artifact status remains `GENERATED` and `PARTIAL`.

The catalog link is provenance only. This challenge was independently authored and does not copy the linked tutorial.
