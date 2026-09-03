# Public tests

These dependency-free `node:test` cases demonstrate the public API, middleware ordering, routing,
JSON parsing, HTTP status selection, supported-method fallthrough, and request isolation. The
concurrency case uses explicit gates to prove two requests overlap rather than relying on timer
scheduling. The suite intentionally does not cover every edge case in `REQUIREMENTS.md`.

Run from the repository root:

```sh
node --test public_tests/*.test.js
```

Evaluators can point the same examples at another package directory:

```sh
SUBMISSION_ROOT=sealed/reference node --test public_tests/*.test.js
```

Passing these examples is necessary but not sufficient. Do not encode special cases for test paths
or inspect evaluator-only material.
