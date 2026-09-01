# Independent review

Verdict: **REVISE**.

The candidate is a strong, carefully scoped teaching pack, and its validation
labels are appropriately conservative. It should not be promoted yet: one
reference-dispatch edge case contradicts the written contract, evaluator
material is only separated by convention in the submitted tree, and several
claims of absolute test boundedness exceed what the in-process timers enforce.

## Prioritized findings

### P1 — A capture-decoding failure bypasses an error handler in the same route registration

`REQUIREMENTS.md:69-75` says handlers in a registration run in order and errors
skip normal handlers until a matching error handler; lines 136-139 say a
decoding failure enters that error dispatch like a thrown `URIError`.

In `sealed/reference/src/index.js`, `decodeURIComponent` can throw at line 104.
The dispatcher catches that at lines 421-425 and changes `errorState`, but it
does not store a match or failure state in `paramsByRegistration`. On the next
arity-four handler in the same registration, lines 417-422 invoke the same
matcher again. It throws again before the handler can run, and exhaustion
produces the default 500.

Thus this contract-shaped case cannot be handled as declared:

```js
app.get(
  '/value/:id',
  (req, res) => res.send(req.params.id),
  (error, req, res, next) => res.status(422).send(error.name),
);
```

For `/value/%ZZ`, the route-local error handler should be reached just as it
would be if the preceding route handler threw. Separate raw-pattern matching
from capture materialization, or cache the registration's match/error result so
later handlers do not redo the failing decode. Add a sealed regression covering
both a route-local error handler and a later global error handler. This finding
is a deterministic static trace; behavioral confirmation was unavailable
because Node is absent.

### P1 — Progressive disclosure depends on an unproven external control

The artifact contains 21 directly readable files under sealed paths, including
the complete reference, sealed tests, expected adversarial outcomes, fixed
debugging implementations, and review answers. `README.md:38` and
`AGENTS.md:3-7` ask learners not to inspect them, but prose is not an isolation
boundary. `environment/verify-structure.py` explicitly traverses the top-level
`sealed` tree and does not build or validate a reduced learner export.

If the learning-factory delivery layer masks these paths, that mechanism may
resolve the risk, but no learner-view artifact or transfer evidence is present
here and the manifest correctly does not claim `TRANSFER_VERIFIED`. Before
release, generate a deterministic learner view from an explicit allowlist,
verify the absence of all sealed/reference/answer paths in that view, and record
the independently checked artifact digest.

### P2 — “Absolute” deadlines do not bound synchronous learner code

`public_tests/README.md:27-30` says an incomplete handler cannot leave the suite
running forever, and `sealed/DESIGN.md:77-78` calls the operation deadlines
absolute. The timeout callbacks in the public and sealed helpers run on the
same Node event loop as the implementation under test. A synchronous infinite
loop, or a microtask loop that starves timers, prevents those callbacks from
running. The benchmark calls the target synchronously and caps iterations, but
has no wall-clock watchdog at all.

Keep the internal request deadlines and byte ceilings, but run untrusted targets
under an outer process-level timeout/process group, or narrow the documentation
to say that the deadlines bound yielding/pending operations. The benchmark
should document an external timeout command if it remains in-process.

### P2 — Generated-material reuse rights are not explicit

The provenance boundary is candid: the catalog is CC0, the linked tutorial is
`NOASSERTION`, and the linked content is claimed not to have been fetched or
copied. However, “independently generated for personal educational use” is a
purpose statement, not an explicit license or grant for the generated prose,
code, and tests. Neither package declares a license, and the only license-named
file is `LICENSE_BOUNDARY.md`.

If this artifact will be copied or redistributed, add an explicit SPDX license
for the generated material, or state clearly that no reuse grant is provided.
The upstream/no-copy claims could not be independently compared in this
workspace and remain provenance assertions rather than validated facts.

### P3 — The design-question editing instruction conflicts with the workspace rule

`README.md:16` calls the root `DESIGN_QUESTIONS.md` a decision log “to complete
as you work,” while `AGENTS.md:7` restricts learner edits to `starter/` and line
26 instead suggests a copy. Make the main README point to a learner-owned copy
under `starter/` so following the progressive path does not violate the stated
scope.

## Positive evidence

- The builder makes no behavioral validation claim. The manifest remains
  `GENERATED`/`PARTIAL`, independent validation remains required, and the
  production document expressly remains a gap analysis.
- Independent execution reproduced the structural PASS output and every
  published SHA-256 value. The source counts of 21 public and 33 sealed tests
  also match the validation record; they are not represented as pass counts.
- The runtime is pinned to Node 20.19.5, the project has no third-party runtime
  dependencies, and local/container reproduction commands are supplied.
- The requirements are precise about route grammar, error-state/value
  separation, prototype-safe plain objects, HEAD semantics, defaults, and
  request isolation. Public tests progress in a useful order and use black-box
  HTTP behavior.
- Static inspection found bounded response collection, server cleanup paths,
  no subprocess execution in candidate JavaScript, no symlinks or special
  nodes, and no high-confidence credential signatures.
- The provenance text does not incorrectly transfer the catalog's CC0 status to
  the linked tutorial, and the productionization limitations are frank.

## Evidence boundary

No Node-compatible runtime or container runner exists in this review
environment. Therefore no JavaScript suite, harness, exercise, or benchmark is
reported as passing, and no `BUILDS`, `TESTED`, `FUZZED`, `BENCHMARKED`,
`REVIEWED`, `TRANSFER_VERIFIED`, or `PRODUCTIONIZED` promotion is warranted.
The detailed commands and observations are in `VALIDATION.md`.
