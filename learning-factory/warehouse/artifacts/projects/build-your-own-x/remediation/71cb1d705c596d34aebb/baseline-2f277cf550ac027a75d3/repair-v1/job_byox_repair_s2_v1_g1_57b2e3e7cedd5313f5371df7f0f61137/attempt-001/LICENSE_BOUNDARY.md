# License and provenance boundary

The catalog snapshot in `PROVENANCE.json` is CC0-1.0 metadata. It identifies an
external tutorial whose license is recorded as `NOASSERTION`. That link is
provenance only: the external repository was not fetched, inspected, copied,
or paraphrased while generating this artifact.

The authoritative manifest field named `provenance_sha256` is the immutable
source-snapshot identifier repeated as `PROVENANCE.json.snapshot_sha256`; it is
not the byte digest of the provenance document. The separately pinned SHA-256
of the exact `PROVENANCE.json` file is
`8aa702b8b64241bda70f3a63e3d1b9a681e7dc87f4d5930b9b4f764f584e5dad`, and
`environment/audit.py` verifies that document digest directly.

All instructional prose, C code, tests, and diagrams in this workspace were
created independently for this challenge. They are intended for personal
educational use. No claim is made that the generated material inherits a
license from the linked resource, and no generated validation result changes
that boundary.
