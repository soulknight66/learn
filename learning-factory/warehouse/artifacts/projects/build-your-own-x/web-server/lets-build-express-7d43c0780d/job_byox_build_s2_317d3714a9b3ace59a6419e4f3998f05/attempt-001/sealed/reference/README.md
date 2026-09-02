# Sealed reference implementation

This CommonJS package is an independently generated, dependency-free implementation of the written
challenge contract. It is evaluator material, not learner guidance.

When Node.js 18 or newer is available, run from the repository root:

```sh
SUBMISSION_ROOT=sealed/reference node --test public_tests/*.test.js
node --test sealed/reference_tests/*.test.js
```

The build host used to create this artifact had no Node.js executable, so these commands are
prescribed but were not executed here. Independent validation remains mandatory.
