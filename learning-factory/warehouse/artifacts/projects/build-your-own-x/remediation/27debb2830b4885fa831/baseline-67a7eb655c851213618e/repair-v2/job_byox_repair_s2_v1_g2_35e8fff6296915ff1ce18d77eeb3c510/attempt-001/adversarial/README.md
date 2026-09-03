# Adversarial validation boundary

Adversarial inputs and expected outcomes are instructor-only because they can disclose validation
strategy. They live in `sealed/reference_tests/adversarial.test.mjs`, not in this directory.

The hidden-side themes are malformed bytecode, operand underflow, hostile jumps, dead branches,
falsey boundaries, nested shadowing, and name leakage. This README contains no case answers and is
not evidence of fuzzing or security hardening.
