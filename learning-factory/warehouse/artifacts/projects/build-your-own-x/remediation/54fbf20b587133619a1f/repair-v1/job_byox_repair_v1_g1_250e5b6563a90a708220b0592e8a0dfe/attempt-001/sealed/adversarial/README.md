# Sealed adversarial suite

This directory contains evaluator-only programs and their expected
observations. Do not copy individual cases into the revealable stage.

The harness-owned binding fixes the candidate entry to `starter/src/index.js`
and the oracle entry to `sealed/reference/index.js`; neither can be selected by
an argument or environment variable. Before importing the candidate, it rejects
symbolic links, dynamic imports, non-local imports, and relative imports that
escape `starter/`. It records path-and-content SHA-256 identities for both trees.

Each case runs the candidate and oracle separately through both backends. A
passing run requires each observation to match the sealed expectation and the
candidate to match the oracle for the same backend. Tree/VM parity is also
required unless an explicit exact-boundary case exhausts a backend-specific
`maxSteps` budget. Error cases reject raw JavaScript exceptions even when their
message happens to match.

When Node.js is available from the repository root, run:

```sh
node sealed/adversarial/run.mjs
```

Use `--case <id>` to isolate one case or `--list` to print identifiers. The first
output record identifies the candidate and oracle artifacts. The repair
environment did not provide Node.js, so this command has not been executed here;
it remains subject to independent validation.

The finite case list is not a fuzzing claim. Extend it with generated valid ASTs,
source mutations, and shrinking only after preserving deterministic seeds and
resource limits.
