# Sealed reference tests

These host-side tests extend the public contract with exhaustion, stale state,
PID wrap exhaustion, top-of-address-space translation, raw-byte mutation
snapshots, canonical padding checks, and full-capacity scrubbing checks. They
intentionally compile only the portable C units. Target-only behavior is
validated by the separate QEMU run recorded in `VALIDATION.md`.

Failure snapshots use `memcpy` into unsigned-byte arrays rather than structure
assignment, so their evidence does not depend on unspecified padding stores.

The tests are deterministic and use compiler sanitizers in the factory run.
Their passing result evaluates this generated reference, not arbitrary learner
submissions and not production fitness.
