# Productionization assessment

Productionization is not claimed and `MANIFEST.yaml` must remain `productionized: false`. The implementation
is a deterministic educational reference, not a multi-tenant execution service.

Before production use, define a threat model and add enforced budgets for bytes, tokens, nesting, integer
width, list allocation, call steps, VM instructions, wall time, and output. Replace recursive reader and
data walkers with explicit stacks. Use immutable boundary values or defensive deep copies. Attach source
file/span metadata to syntax and errors. Decide whether globals may be redefined and whether interpreters
are shareable across threads.

Operational work would also require a distributable package, supported-Python policy, structured logs and
metrics without source leakage, cancellation, isolated workers, deterministic resource-exhaustion errors,
corpus/property testing, dependency and static analysis, platform tests, and an external security review.
None of those controls is present or simulated in this pack.
