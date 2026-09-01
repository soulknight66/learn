# Repair provenance and reproducibility

This is repair generation 1 under remediation policy version 1 for project
`project_c305a6b70f268e23e2e48694e3604f28`. It started from the checksum-bound prior builder artifact:

```text
artifact_id: artifact_92d80c8002c64150af70868683982788
checksum_algorithm: tree-sha256-v2
artifact_checksum: 721256e2f8118d065d671e659b95897dc8afb0c7cf7e5059ae8d8a7e1f88c2dd
```

The independent review input was:

```text
artifact_id: artifact_a743ab35176c4f6ba27b0e6364897b4d
checksum_algorithm: tree-sha256-v2
artifact_checksum: 50712aaa76ac6471cdead1f780133581542ff11277e1d6cb99538b9907319459
verdict: REVISE
validation_id: validation_f2ec61fb9ec34bb0bc4d1ada48383502
evidence_sha256: ed6d15147e82405dc4cfdba43b595c722af2cc38299caa0223e215c060c069bc
```

The controller's immutable remediation snapshot digest was
`a73abb6109722ecbe6a77d5dad6ec4762347459f98f427dabbbe8468bd05e7d8`.
The repair preserved the prior safe artifact entries and changed the reference, regressions,
contracts, module scopes, and learner-view boundary described in `../REVIEW.md`.

The probabilistic worker implementation/version and a replayable original generation command were
not exposed inside this workspace. Consequently this file does not claim bit-for-bit regeneration.
The prior artifact plus archived review are controller inputs, not distributable contents of this
pack. Exact bounded checks for this repaired output are recorded in the top-level production
validation record. This unresolved regeneration limitation is one reason the artifact remains
`GENERATED` + `PARTIAL`.
