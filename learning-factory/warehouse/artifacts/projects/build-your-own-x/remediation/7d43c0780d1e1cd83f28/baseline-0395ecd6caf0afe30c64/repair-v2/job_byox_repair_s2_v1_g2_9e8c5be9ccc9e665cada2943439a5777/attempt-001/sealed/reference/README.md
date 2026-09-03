# Sealed reference implementation

This CommonJS package is an independently generated, dependency-free implementation of the written
challenge contract. It is evaluator material, not learner guidance.

When Node.js 18 or newer is available, run from the repository root:

```sh
SUBMISSION_ROOT=sealed/reference node --test public_tests/*.test.js
node --test sealed/reference_tests/*.test.js
```

The repair host provided Node.js 22.21.0. Syntax checks and socket-free regressions ran, but the
sandbox rejected loopback listeners with `EPERM`, so the HTTP integration commands did not complete.
Independent execution in a network-capable validator remains mandatory.
