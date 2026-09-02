# Sealed reference tests

This suite tests the oracle independently of the learner starter. It covers token locations, every precedence tier, structured diagnostics, binding resolution, built-in validation, runtime semantics, pure optimization, code-injection resistance, optimized/unoptimized equivalence, and interpreter separation.

Run on Node.js 18 or newer:

```text
node --test sealed/reference_tests/compiler.test.js
```

The generation host lacked Node.js, so this command is supplied but was not claimed as run; see `VALIDATION.md`.

`gjs-smoke.js` is a smaller compatibility smoke suite for hosts with GJS but no Node. It does not replace the authoritative Node suite.

`validate_artifact.py` checks immutable JSON, required and forbidden paths, regular-file types, and common credential signatures without reading factory-owned dot directories.
