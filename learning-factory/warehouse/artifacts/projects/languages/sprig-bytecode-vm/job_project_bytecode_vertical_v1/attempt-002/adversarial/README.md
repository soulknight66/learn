# Deterministic grammar/property fuzzing

The bounded generator records its seed and corpus hash, computes an independent value oracle,
and compares both execution architectures across expressions, variables, bounded loops,
branches, division/remainder, and short circuit. Expand it with malformed syntax and shrinking.
