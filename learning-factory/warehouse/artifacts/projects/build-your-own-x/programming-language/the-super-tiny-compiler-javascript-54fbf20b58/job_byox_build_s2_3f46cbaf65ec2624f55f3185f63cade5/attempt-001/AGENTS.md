# Learner-agent instructions

Work only in `starter/` unless a test explicitly asks you to add a learner-owned fixture there. Do not inspect or modify `sealed/`, provenance records, validation evidence, or exercise answer directories.

## Constraints

- Use only JavaScript built-ins; do not add network dependencies.
- Preserve the exported API in `starter/compiler.js`.
- Keep scanning, parsing, analysis, optimization, generation, and interpretation as distinct stages.
- Treat source text as untrusted data. Never interpolate a source identifier into generated JavaScript.
- Do not use `eval` or `Function` in the interpreter.
- Add tests for every bug you fix.
- Run `node --test public_tests/compiler.test.js` from the repository root.

Public tests are examples, not a full specification. Hidden validation may construct ASTs, vary whitespace and line endings, and check errors and source locations.
