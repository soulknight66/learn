# Adversarial evaluation inventory

This directory is evaluator support and is excluded from the learner-visible
allowlist. The executable cases live under `sealed/reference_tests/` so expected
answers and boundary details remain sealed.

The executable inventory includes one- through seven-byte partial length
headers, truncated payloads, a plausible length-field bit flip, CRC damage,
impossible lengths, unknown markers/versions/flags, inconsistent key metadata,
invalid segment names, record-offset and segment-base gaps, locale-sensitive
filename pressure, stale and future terms, regressing and over-leader
acknowledgements, mutable-array attempts, undersized read budgets,
closed-resource calls, and an ISR minority that must not become a quorum.

`sealed/harness_tests/` separately verifies that a timed-out command cannot
leave a descendant process alive to continue writing.

These are deterministic examples rather than a claim of exhaustive fuzzing.
