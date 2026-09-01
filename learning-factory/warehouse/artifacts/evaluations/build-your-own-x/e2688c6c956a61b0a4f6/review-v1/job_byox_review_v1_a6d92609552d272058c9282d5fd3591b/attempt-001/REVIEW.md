# Independent review

Verdict: **REVISE**.

The host model is unusually well specified and most observed behavior is reproducible, but the sealed reference accepts a contract-invalid copy-on-write state as valid. The transferred structure verifier is also not runnable from the submitted material. No validation label should be promoted.

## Prioritized findings

### P1 — `pebble_check()` accepts a shared writable frame

`REQUIREMENTS.md:47-51` establishes that shared writable pages must have write permission suppressed and be marked copy-on-write until they become private. `README.md:19` tells the learner to reject every corrupt state described by the contract, and `REQUIREMENTS.md:71-81` makes page flags and exact derived frame references part of the invariant oracle.

A focused independent probe created a parent with a read-only page, forked it, and confirmed that the parent and child shared a frame with `refs == 2`. It then introduced a one-bit corruption by adding `PEBBLE_PAGE_WRITE` to the parent's PTE. `pebble_check()` returned `PEBBLE_OK` (`0`) and an empty reason.

The implementation at `sealed/reference/src/pebble.c:1019-1043` checks each PTE's allowed bits and accumulates references; `:1077-1087` checks the final counts. It never relates writability to sharing. Consequently, a `READ | WRITE | PRESENT` PTE can name a frame used by another process and still pass the advertised oracle. The submitted corruption tests at `sealed/reference_tests/test_reference.c:542-577` do not cover this relationship.

Fix the checker so every present PTE with `WRITE` names a frame whose derived reference count is exactly one, then add a regression based on the probe above. Also exercise mixed PTE flags for every multiply referenced frame. This is a reference-answer correctness issue, not merely missing test coverage.

### P2 — The transferred structure verifier is not reproducible

`VALIDATION.md:3` describes its observations as reproducible, and `:203-227` records `python3 sealed/validation/verify_pack.py` as a successful exact metadata/structure check. In the submitted tree, `sealed/validation/verify_pack.py:28` unconditionally reads `CANDIDATE/JOB.md`, but that file is absent. Independent execution exited `1` with `FileNotFoundError` before any declared check ran.

This does not show that the builder's recorded run was fabricated; it shows that the run depended on builder-workspace state that was not transferred. Make the verifier accept an explicit safe fixture, embed non-secret canonical expectations, or preserve a canonical metadata digest and path policy in the submitted artifact. The validation record should distinguish builder-only checks from commands reproducible after transfer.

### P2 — Progressive disclosure is specified only in prose

The static layout is sensible: all 22 answer/reference files are under `sealed/`, and the learner allowlist at `README.md:37-39` contains no sealed-path reference. However, the artifact contains no machine-readable learner allowlist, materialized student view, or harness-controlled transfer receipt. The supplied verifier checks builder-job path lists, not an exported learner view, and it is currently blocked by the missing `JOB.md` noted above.

Add a deterministic student-view manifest or export step, validate that exact output for forbidden paths/content, and record its digest. Until the harness supplies that evidence, the absence of sealed material from the actual learner view is inconclusive. The candidate correctly makes no `TRANSFER_VERIFIED` claim.

### P3 — The generated-material license grant is unclear

`LICENSE_BOUNDARY.md:3-7` correctly separates the catalog's CC0 metadata from the linked resource whose license is `NOASSERTION`, and it avoids treating the link as permission to copy upstream work. That is a strong boundary. However, “provided for personal educational use” is not an SPDX license or a complete permission grant for the generated pack itself. If these artifacts are meant to be copied, modified, or redistributed, record an authorized generated-content license or explicit distribution policy without changing the linked resource's `NOASSERTION` status.

The originality and no-upstream-access statements could not be independently corroborated because neither the upstream snapshot nor network access was available.

### P3 — Learner README names the wrong error constant

`README.md:31` says `PEB_ERR_NOT_IMPLEMENTED`; the public header defines `PEBBLE_ERR_NOT_IMPLEMENTED`. Correcting the typo would prevent needless learner confusion.

## Confirmed strengths

- The starter and reference compile cleanly under GCC 8.5.0 with strict C11 warnings. The submitted O2/O0 suites and public-reference suite reproduced their recorded passes.
- A reviewer-authored deterministic suite passed 2,048 scheduler configurations plus boundary, transactional, capacity, flag, name, access-mode, and checker-safety cases before the focused failing invariant was added.
- The incomplete starter's four public failures are intentional, accurately documented, and not presented as a passing completion gate.
- The manifest remains honestly limited to `GENERATED` and `PARTIAL`, with `productionized: false` and independent validation required. Sanitizer, fuzz, benchmark, hardware, review, transfer, and production claims are not inflated.
- The staged contract, concept notes, design questions, public sampler, debugging prompts, review exercise, and host-versus-hardware boundary are useful to an advanced C learner.
- Manifest/provenance identifiers cross-link consistently, the public and reference headers are byte-identical, and no credential-shaped value was found by the bounded searches performed.

## Decision

Revise the invariant checker and its regression coverage before treating the sealed implementation as a semantic oracle. Make structure/disclosure validation reproducible after transfer. The unavailable sanitizer, target, upstream, and transfer checks remain limitations rather than passes.
