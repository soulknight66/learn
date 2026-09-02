# Adversarial evaluation inventory

This directory is evaluator support and is excluded from the learner-visible
allowlist. The executable cases live under `sealed/reference_tests/` so expected
answers and boundary details remain sealed.

The inventory includes truncated length fields, truncated payloads, CRC damage,
impossible lengths, invalid segment names, offset/base gaps, stale and future
terms, regressing or over-leader acknowledgements, mutable-array attempts,
undersized read budgets, closed-resource calls, and an ISR minority that must
not become a quorum.

These are deterministic examples rather than a claim of exhaustive fuzzing.
