# Sealed reference implementation

This directory is evaluator-only. It contains an independently authored Java
21 implementation of the learner contract. It is intentionally excluded from
the learner view and is not evidence that a learner submission is correct.

The implementation uses only the Java standard library. It prioritizes explicit
state invariants and deterministic failure behavior over throughput. See
`sealed/DESIGN.md` for rationale and `sealed/reference_tests/` for executable
evidence. A constructed partition holds exclusive mutation ownership of its
log and replication tracker so retained caller aliases cannot violate their
shared end-offset invariant.
