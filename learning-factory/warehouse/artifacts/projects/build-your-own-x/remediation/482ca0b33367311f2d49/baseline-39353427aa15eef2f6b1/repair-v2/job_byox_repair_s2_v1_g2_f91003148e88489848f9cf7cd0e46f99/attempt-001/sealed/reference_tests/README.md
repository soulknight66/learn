# Sealed reference tests

These evaluator-only tests extend the public contract with hostile archives, quota boundaries,
whiteout ordering, durable state enforcement, concurrent claims, launch failure recording, and CLI
serialization. Repair regressions also cover destination-ancestry links, pre-mutation target-type
validation, stage/hash identity, racing tag publication cleanup, published-tree integrity,
marker-inclusive output bounds, injectable log scratch, and the exact student-view allowlist. They
are deterministic unit/integration checks, not a sandbox penetration test.

The exact command and observed result are recorded in `VALIDATION.md`.
