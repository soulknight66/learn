# Learner agent guide

Work only in this challenge workspace. A correctly projected learner workspace contains only the
allowlisted roots named in `README.md`; evaluator directories such as `sealed/` are absent. If one
is present, stop and report an isolation failure without reading or modifying it.

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
- Use explicit gates, not short timer delays, when a concurrency test must prove overlap.
