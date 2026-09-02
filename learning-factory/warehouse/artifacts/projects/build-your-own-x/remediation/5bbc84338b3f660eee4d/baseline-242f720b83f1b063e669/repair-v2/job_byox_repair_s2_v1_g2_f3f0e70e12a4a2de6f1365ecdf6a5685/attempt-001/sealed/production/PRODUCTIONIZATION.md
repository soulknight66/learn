# Productionization assessment

Productionization is not claimed and `MANIFEST.yaml` must remain `productionized: false`. The implementation
is a deterministic educational reference, not a multi-tenant execution service.

The reference now enforces a 256-level syntax ceiling and a 10,000-digit integer-token ceiling. Before
production use, define a threat model and add enforced budgets for total bytes, tokens, list allocation,
call steps, VM instructions, wall time, and output. Replace the remaining bounded recursive reader and
non-tail evaluator paths with explicit stacks. Use immutable boundary values or defensive deep copies.
Attach source file/span metadata to syntax and errors. Decide whether globals may be redefined and whether
interpreters are shareable across threads.

`learner_view.py` is a harness-controlled progressive-disclosure boundary. It materializes only the nine
learner-visible top-level entries. The learner README now carries a self-contained provenance and license
summary rather than pointing to combined-pack records outside that view. The exporter rejects
solution/reference path components and non-regular filesystem entries, normalizes modes, audits the
completed staging directory, and atomically renames it without overwriting an existing destination. The
sealed suite materializes the current pack into a temporary directory beneath this harness-controlled
tree, compares every copied file, audits the exact allowlist, and removes the temporary view. The
supplemental prompt roots are explicitly instructor-only; this pack defines no second learner reveal
stage. Supplying the exporter does not itself prove access isolation: a delivery harness must give
learners only its output and must retain the combined pack outside learner access.

Operational work would also require a distributable package, supported-Python policy, structured logs and
metrics without source leakage, cancellation, isolated workers, deterministic resource-exhaustion errors,
corpus/property testing, dependency and static analysis, platform tests, and an external security review.
None of those controls is present or simulated in this pack.
