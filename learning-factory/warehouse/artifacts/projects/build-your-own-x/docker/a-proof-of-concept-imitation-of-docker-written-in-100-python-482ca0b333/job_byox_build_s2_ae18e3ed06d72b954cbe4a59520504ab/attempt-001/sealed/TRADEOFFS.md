# Tradeoffs

## Copy snapshots versus overlay mounts

Recursive copies are slow and consume space, but are portable, observable, and require no privilege.
Overlay mounts better resemble production containers but introduce kernel support, mount lifecycle,
whiteout encoding, propagation, privilege, and cleanup risks. The baseline chooses copies so the
filesystem lesson can be validated in an ordinary temporary directory.

## Strict tar subset versus compatibility

The importer rejects links, devices, FIFOs, sparse files, and ambiguous duplicates. Real OCI images
can contain links and richer metadata. Supporting those safely requires a more complete extraction
model, including link-target validation and platform metadata policy. Strict rejection makes the
educational security invariant small enough to reason about.

The standard `tarfile` reader supports compressed inputs, but the quotas constrain declared expanded
members rather than CPU spent decompressing headers. A hostile compressed stream still warrants an
outer byte/time budget or a supervised helper.

## SQLite versus directory metadata

SQLite provides transactions, cross-process locks, foreign keys, and trigger-enforced transitions in
one standard-library dependency. It cannot atomically commit a filesystem rename and a state row, so
crash reconciliation remains necessary. Per-container JSON files would make that problem worse and
make concurrent claims harder.

## Monotonic IDs versus unpredictable IDs

Monotonic IDs make tests and local operations legible. They reveal object counts and are not globally
unique. A multi-host service should add a stable runtime identity or random external identifier while
retaining a database primary key.

## File-backed capture versus streaming logs

Temporary files cap Python memory use and allow independent stdout/stderr limits. They still permit a
child to consume disk rapidly before timeout. Production needs write quotas, streaming rotation, and
backpressure in a supervisor. Merging streams would preserve only one ordering and lose separation;
the reference retains two streams without claiming cross-stream chronology.

## Catching launch failures

After `RUNNING` is committed, launch errors become `EXITED` with reserved code 125 so the durable state
does not remain stuck during ordinary failures. A hard crash can still leave `RUNNING`; solving that
requires leases and reconciliation, not a broader exception handler.
