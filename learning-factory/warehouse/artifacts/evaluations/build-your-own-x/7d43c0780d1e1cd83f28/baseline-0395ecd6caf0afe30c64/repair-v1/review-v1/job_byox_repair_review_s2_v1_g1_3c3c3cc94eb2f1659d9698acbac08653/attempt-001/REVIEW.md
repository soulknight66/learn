# Independent review

Verdict: REVISE.

The pack is thoughtfully structured and unusually candid about its partial validation state, but
the sealed reference still violates several normative response and body-lifecycle requirements.
Those defects can make an otherwise correct learner submission appear wrong or leave request work
unsettled, so the artifact should not receive an advisory PASS yet.

This verdict is advisory only. It does not confer REVIEWED or any other validation label.

## Prioritized findings

### P1 — The error translator can emit conflicting framing and a falsely encoded JSON body

In sealed/reference/src/application.js:84-96, sendError overwrites Content-Type and Content-Length
but does not remove headers already placed on the response. copySafeErrorHeaders filters only
headers copied from the thrown error; it does not sanitize existing response state.

A handler that sets Transfer-Encoding: chunked and Content-Encoding: gzip and then throws produces a
native Node ServerResponse containing both Transfer-Encoding and Content-Length, while the bytes are
plain JSON rather than gzip. The independent socket-free native-response check observed:

    native_error_framing: FAIL TE+CL and stale gzip emitted

This breaks the R7 promise of a deliberate JSON error response and creates ambiguous HTTP framing.
Clear pre-existing framing and representation-encoding headers before constructing the error
response, then copy only explicitly safe error metadata. Add a native ServerResponse regression
that checks the serialized header block without opening a socket.

### P1 — Destruction after body-parser attachment can leave the middleware pending

sealed/reference/src/body-json.js:121-125 ignores close whenever req.complete is true, even if
req.readableEnded is still false. R6 requires destruction before readable end to settle with 400.

The bounded reproduction marked a PassThrough request complete, entered the parser, destroyed it
before readable end, and received no resolution or rejection:

    destroy_before_end: FAIL pending

The complete flag describes HTTP parser completion; it is not a substitute for readable-stream
completion. Treat any close/destruction before readableEnded as BODY_ABORTED, and add a regression
covering post-attachment destruction with complete true plus listener cleanup.

### P2 — Body-forbidden statuses retain entity encoding headers

sealed/reference/src/response.js:15-19 removes Content-Type, Content-Length, and Transfer-Encoding
only. A 204 sent after res.set("content-encoding", "gzip") retains Content-Encoding even though no
encoded representation is sent. The independent check observed:

    bodyless_entity_headers: FAIL {"content-encoding":"gzip"}

R5 says statuses that forbid bodies must remove entity headers. Define the intended entity-header
set explicitly and test at least Content-Encoding on 1xx, 204, and 304 responses.

### P2 — A list containing only identity encodings is rejected as unsupported

sealed/reference/src/body-json.js:156-164 compares the entire Content-Encoding field to the single
string identity. The field value identity, identity contains no non-identity coding, but the
middleware returns 415:

    identity_encoding_list: FAIL 415 UNSUPPORTED_CONTENT_ENCODING

R6 says a non-identity Content-Encoding produces 415. Parse the comma-separated coding list and
reject when any member is non-identity; also define behavior for empty or malformed members.

### P3 — The learner projection includes a full-pack verifier

The directory-level environment allowlist selects environment/verify_artifact.py. That program
requires and names sealed reference, review, productionization, provenance, and validation files
which are intentionally absent from a learner view. It therefore cannot succeed in that view and
unnecessarily exposes evaluator-pack structure, although it does not expose the sealed contents.

Use a file-level allowlist for environment, move the full-pack verifier outside the learner root, or
make its learner-visible purpose and behavior explicit. The current projection otherwise excludes
the sealed, adversarial, debugging-answer, review-answer, benchmark, provenance, license-boundary,
and validation roots.

## Evidence and quality assessment

- The starter is intentionally incomplete rather than a failed reference. Requirements are
  detailed, staged, and useful; concepts and design questions provide good scaffolding without
  giving away the implementation.
- Public tests use an explicit overlap gate and deterministic server cleanup. Sealed tests cover
  meaningful edge cases, but the independent failures above show gaps in lifecycle and header-state
  coverage.
- All 22 JavaScript files parse. Five socket-free regressions, four filtered reference tests, three
  learner-view tests, and the public export test passed independently on Node.js 22.21.0 / Python
  3.11.5.
- Metadata identifiers are internally coherent, and canonical MANIFEST.yaml and PROVENANCE.json
  values match the verifier's recorded hashes. No whole-pack digest is supplied inside the pack;
  the prose correctly assigns content-addressed inventory to the factory.
- The license boundary is clear: the catalog snapshot is identified as CC0-1.0, the linked
  repository remains NOASSERTION, linked content is said not to have been copied, and no general
  redistribution license is asserted for generated material.
- Validation claims are appropriately conservative. The manifest remains GENERATED + PARTIAL,
  productionized is false, and no BUILDS, TESTED, FUZZED, BENCHMARKED, REVIEWED,
  TRANSFER_VERIFIED, or PRODUCTIONIZED claim is made. The reported Node/Python versions,
  socket-free passes, and loopback EPERM outcome were independently reproduced.

## Required before reconsideration

1. Correct the two P1 defects and add deterministic regressions for both.
2. Resolve the bodyless-header and Content-Encoding-list contract mismatches.
3. Clarify or narrow the learner projection so pack-only validation tooling is not accidentally
   presented as learner material.
4. Run the full public and sealed network suites in a harness that permits ephemeral loopback
   listeners, and retain the orchestrator-captured results.
5. Materialize and inventory the learner view under harness control. Keep validation labels
   unchanged until separate validators establish them.

## Review limitations

Loopback listen failed with EPERM, so network integration, real-socket abort handling, and
app.listen remain inconclusive. No benchmark, fuzzing, cross-version run, or production-readiness
assessment was performed. The source catalog baseline, linked tutorial repository, external
artifact inventory, actual transferred learner view, and PRIOR_BUILD staging tree were unavailable;
their associated provenance, originality, transfer, and preservation claims were not independently
established.
