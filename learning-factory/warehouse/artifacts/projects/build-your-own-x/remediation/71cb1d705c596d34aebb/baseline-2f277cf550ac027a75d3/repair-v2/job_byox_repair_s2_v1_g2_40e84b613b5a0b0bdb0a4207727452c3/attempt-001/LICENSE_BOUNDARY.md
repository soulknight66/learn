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

## Generated-material license

SPDX-License-Identifier: CC0-1.0

Unless an individual file states otherwise, all independently generated
instructional prose, C code, tests, and diagrams in this challenge pack are
made available under the Creative Commons CC0 1.0 Universal dedication. To the
extent possible under law, the authors waive copyright and related rights in
that generated material. It may be copied, modified, combined, redistributed,
and used for any purpose, including commercial use, without attribution. It is
provided without warranty. The provenance phrase “for personal educational
use” describes why the material was generated; it is not a restriction on
this CC0 grant.

This grant does not cover the externally linked tutorial or any content at
that URL. No linked content was included here, its license remains
`NOASSERTION`, and no claim is made that this generated material inherits
rights from it. No generated validation result changes that boundary.
