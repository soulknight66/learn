# Independent review

- Builder job: `job_byox_build_s2_317d3714a9b3ace59a6419e4f3998f05`
- Project: `project_a35390ae473c6dda128f34db394c3f87`
- Advisory verdict: **REVISE**
- Promotion effect: none. This review does not assign `REVIEWED`; only an orchestrator-captured acceptance validator may do that.

The submission is unusually candid and pedagogically substantial for a `GENERATED` + `PARTIAL`
artifact. Its labels accurately acknowledge that Node.js never ran. It is not ready for an advisory
pass, however: static inspection found a routing contract error and an abort-lifecycle hole, and the
submitted layout does not enforce the learner/evaluator boundary.

## Prioritized findings

### P1 — Supported-method fallthrough is incorrectly translated to 405

`sealed/reference/src/application.js:173-183` computes all methods for the path and emits 405 whenever
that set is nonempty. It never asks whether `req.method` is in that set. For example:

```js
app.get('/known', async (_req, _res, next) => next());
```

With no later responding layer, `GET /known` reaches the terminal with `GET` in `allowed`, then
receives 405. R3 reserves 405 for an *unsupported* method. A route that matched both path and method
may fall through, but that cannot make its method unsupported. A matching handler that returns
without ending the response reaches the same erroneous branch when `handle` invokes the terminal.

Change terminal selection so 405 is possible only when the request method is absent from the
computed allow set (after HEAD fallback rules). Define the supported-method fallthrough outcome,
normally 404, and add deterministic integration cases for GET, HEAD, an explicit HEAD route, and a
multi-route delegation chain.

### P1 — Evaluator answers and the complete reference are readable in the submitted learner tree

The tree contains 18 files at `sealed/**` or `*/sealed/**`, including the complete reference package,
the sealed test suite, design/review notes, and both exercise answers. `README.md:40-42` says only a
whitelist is learner-facing, while `AGENTS.md:3-4` merely tells learners not to read `sealed/`.
`environment/verify_artifact.py:26-32,76` makes that material part of the same artifact. Instructions
are not an isolation control.

If an external control plane projects an allowlisted student view, no materialized view or captured
check was supplied here to demonstrate it. Store evaluator assets outside the per-attempt learner
workspace, build the learner view from a deterministic allowlist, and have a harness-controlled
validator inventory that view for `sealed`, references, tests, answers, secrets, and foreign student
files. Do not claim `TRANSFER_VERIFIED` until that evidence exists.

### P1 — A request aborted before JSON listener attachment can leave `readBody` pending

`sealed/reference/src/body-json.js:38-41` special-cases only `readableEnded`. The abort, error, and
close listeners are not attached until lines 105-109, and there is no preflight check for an already
aborted/destroyed stream. A client can disconnect while an earlier asynchronous middleware is
waiting; when that middleware later delegates to `json()`, the relevant events may already be over
and the returned promise has no remaining settlement path. That conflicts with R6's 400 behavior and
can strand request work.

Check terminal stream state before and immediately after listener installation, settle exactly once,
and preserve listener cleanup. Add a bounded regression in which abort/close occurs before parser
entry, plus a real-socket test where a prior gated middleware delays parser attachment.

### P2 — Runtime correctness evidence is still absent

The prescribed public suite, public suite against the reference, and sealed suite all stopped at
`node: command not found` (exit 127). The files contain 5 public and 15 sealed `test(...)`
declarations, but declarations and source review are not executed evidence. Syntax, Node 18 behavior,
malformed-target handling, response termination, content framing, and abort timing remain
unconfirmed.

After correcting the P1 issues, an independent harness should run both suites on every supported
Node line and add cases for supported-method fallthrough, pre-attached and pre-fired aborts, invalid
UTF-8, stream errors, errors after headers, explicit HEAD precedence, and concurrent bodies/headers.
Retain command, runtime version, exit status, and logs as validator-owned evidence.

### P2 — The provenance record does not integrity-bind the generated deliverable

Identifiers and commits cross-link consistently. However, `MANIFEST.yaml`'s `provenance_sha256`
equals `PROVENANCE.json`'s source `snapshot_sha256` (`b4a3f7...`); it is not the raw provenance-file
hash (`0b89a7...`) or its canonical JSON hash (`8830de...`). No published digest covers the generated
prose, starter, reference, or tests. The candidate verifier fixes canonical metadata values inside a
candidate-owned script but likewise does not bind each generated file.

Publish an externally captured, canonical artifact inventory or Merkle/tree digest, document what
each hash covers, and bind it to the builder job and source snapshot. That would make later content
substitution detectable and reproduction comparisons meaningful.

### P2 — Concurrency coverage is scheduling-dependent

`public_tests/framework.test.js:109-128` launches requests concurrently but uses short modulo timers
without a barrier proving that two handlers overlap. It is likely to expose shared state, but its
outcome depends on socket and event-loop scheduling. The sealed suite does not add a deterministic
multi-request gate for bodies, parameters, status, or headers.

Use latches: hold request A after it stores request-local data, admit request B, prove B reached the
critical point, then release A. Repeat for route parameters and JSON bodies, and assert per-response
status and headers as well as payloads.

### P3 — Generated-material reuse terms are not an explicit license

`LICENSE_BOUNDARY.md` and `PROVENANCE.json` correctly avoid treating the linked tutorial's
`NOASSERTION` license as CC0. They describe generated material as being for personal educational use,
but there is no SPDX license or explicit grant covering modification and redistribution of the
generated challenge. If this is intentionally restricted internal material, state that policy; if
learners or operators may copy and redistribute it, add an owner-approved license without implying
that it covers the unidentified upstream tutorial.

## What is already strong

- The manifest is limited to `GENERATED` and `PARTIAL`, requires independent validation, and sets
  `productionized` to false.
- `VALIDATION.md`, the benchmark notes, the static reference review, and the productionization
  assessment expressly avoid build, test, fuzz, benchmark, review, transfer, and production claims.
- R1-R8 form a precise learner contract, while `CONCEPTS.md`, `DESIGN_QUESTIONS.md`, staged TODOs,
  debugging material, and review exercises provide useful progression.
- Package metadata declares no dependencies, and inspected imports are Node built-ins or relative
  files. Test helpers bind loopback ephemeral ports, impose request timeouts, and close servers in
  `finally`.
- Catalog-vs-linked-resource provenance and license boundaries are clearly distinguished, subject to
  the external-verification limitation below.

## Acceptance conditions

1. Correct terminal method selection and already-aborted body handling, with deterministic
   regression tests.
2. Produce and validator-inventory an actually isolated learner view containing no evaluator or
   answer material.
3. Run public, sealed, new adversarial, and lifecycle tests under a validator-controlled Node.js 18+
   environment and retain the logs.
4. Integrity-bind the generated tree and clarify generated-material reuse rights.

Upstream contents and license evidence were not available in this workspace, so the claimed source
snapshot, linked-resource license status, and no-copy assertion remain unverified rather than
rejected.
