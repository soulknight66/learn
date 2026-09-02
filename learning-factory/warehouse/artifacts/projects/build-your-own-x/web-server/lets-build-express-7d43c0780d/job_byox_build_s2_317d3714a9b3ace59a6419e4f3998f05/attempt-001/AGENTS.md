# Learner agent guide

Work only in this challenge workspace. Treat `sealed/` as evaluator-owned material and do not read
or modify it while producing a submission.

## Goal

Complete the dependency-free CommonJS package in `starter/` so every contract in
`REQUIREMENTS.md` holds. Preserve its public exports and use only Node.js built-ins.

## Commands

From the repository root:

```sh
node --test public_tests/*.test.js
```

Formatting and extra tests are welcome, but do not weaken or delete supplied tests. The independent
validator can check requirements not exercised publicly.

## Engineering constraints

- Never use `eval`, shell commands, or global mutable request state.
- Bound every request body before buffering it.
- Do not trust `Host`, paths, headers, declared body lengths, or decoded route parameters.
- Set status and headers before writing a body.
- Await or return `next()` when middleware delegates.
- Keep dependencies at zero; the exercise is about `node:http`, streams, and routing.
- Close every server opened by a test, including on assertion failure.
