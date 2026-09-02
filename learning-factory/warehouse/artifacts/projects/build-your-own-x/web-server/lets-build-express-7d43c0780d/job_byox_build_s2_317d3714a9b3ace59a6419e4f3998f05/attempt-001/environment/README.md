# Environment

The project requires Node.js 18 or newer and no external packages. It uses CommonJS, `node:http`,
`node:test`, `node:assert/strict`, `Buffer`, `URL`, and `URLSearchParams`.

Expected check from the repository root:

```sh
node --test public_tests/*.test.js
```

To exercise the sealed reference in an authorized evaluator environment:

```sh
SUBMISSION_ROOT=sealed/reference node --test public_tests/*.test.js
node --test sealed/reference_tests/*.test.js
```

This build host reported `node: command not found` and `npm: command not found`; therefore no claim
that JavaScript was executed is made in this artifact.
