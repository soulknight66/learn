# Sealed adversarial suite

This directory contains evaluator-only programs and their expected
observations. Do not copy individual cases into the revealable stage.

The suite checks the same source through the tree interpreter and stack VM. A
passing run requires the expected output array or expected Pebble error from
each backend, plus backend agreement. Error cases reject raw JavaScript
exceptions even when their message happens to match.

When Node.js is available from the repository root, run:

```sh
node sealed/adversarial/run.mjs
```

Use `--case <id>` to isolate one case or `--list` to print identifiers. The
authoring environment did not provide Node.js, so this command has not been
executed here; it remains subject to independent validation.

The finite case list is not a fuzzing claim. Extend it with generated valid ASTs,
source mutations, and shrinking only after preserving deterministic seeds and
resource limits.
