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

## Deterministic learner projection

The full pack contains evaluator assets and must never be handed to a learner as-is. From a
harness-controlled location, create a new destination outside the source tree and then verify it:

```sh
python3 environment/learner_view.py project \
  --source /path/to/full-pack --destination /path/to/new-learner-view
python3 environment/learner_view.py verify \
  --source /path/to/full-pack --view /path/to/new-learner-view
```

Projection refuses an existing or overlapping destination, traverses only the authoritative
learner allowlist, rejects symlinks and special entries, and verifies every selected file by SHA-256
after copying. The `environment/` selection is file-level: only this README and `learner_view.py`
are included; full-pack validation tools in that directory remain evaluator-only. Verification also
rejects any extra path in the materialized view. A
harness-controlled validator must capture the verification output before transfer; including this
tool alone does not establish `TRANSFER_VERIFIED`.

On this build host, the configured Node.js 22.21.0 executable was available. Socket-free regression
tests and syntax checks ran, while every loopback `listen` attempt failed with `EPERM`; therefore the
network suites remain unconfirmed. Exact commands and outcomes are in `VALIDATION.md` in the full
production pack.
