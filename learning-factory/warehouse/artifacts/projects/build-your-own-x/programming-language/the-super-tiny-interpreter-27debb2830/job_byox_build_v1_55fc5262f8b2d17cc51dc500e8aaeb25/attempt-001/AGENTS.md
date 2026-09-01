# Challenge worker guide

Work only in this challenge repository. The learner contract lives in `REQUIREMENTS.md`; do not
weaken it to make a test pass.

## Boundaries

- Implement learner work in `starter/` and add learner-owned tests beside the public tests.
- Treat `sealed/` as evaluator-only material. Do not copy it into learner-visible paths.
- Do not infer success from prose or process exit alone; inspect assertions and captured output.
- Keep the implementation dependency-free and compatible with modern ECMAScript modules.
- Preserve deterministic limits for source size, tokens, parser nesting, and execution steps.
- Do not use `eval`, `Function`, shell execution, ambient environment variables, the network, or
  host filesystem access to implement the language.

## Suggested commands

From `starter/`, with Node.js 20 or newer:

```sh
npm test
npm run test:public
```

The public suite is a floor, not the complete specification. Add cases for malformed programs,
scope, short-circuiting, step limits, bytecode validation, and parity between both engines.
