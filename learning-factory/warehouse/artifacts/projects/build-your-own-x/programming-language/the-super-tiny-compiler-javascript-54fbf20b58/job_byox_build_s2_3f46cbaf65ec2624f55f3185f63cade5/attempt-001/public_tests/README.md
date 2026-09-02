# Public tests

`compiler.test.js` checks the exported surface plus representative scanning, precedence, analysis, interpretation, optimization, and safe-code-generation behavior. It deliberately does not cover every malformed token, AST shape, built-in arity, or Unicode edge case.

Run from the repository root:

```text
node --test public_tests/compiler.test.js
```

The starter is expected to fail behavioral tests until implemented. Do not weaken the assertions; add learner tests for uncovered cases.
