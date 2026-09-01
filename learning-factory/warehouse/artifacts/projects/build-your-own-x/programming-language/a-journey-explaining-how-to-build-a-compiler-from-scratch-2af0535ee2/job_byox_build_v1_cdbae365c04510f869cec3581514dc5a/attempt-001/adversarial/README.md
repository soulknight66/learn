# Adversarial evaluator corpus

This directory is evaluator-owned. Its deterministic driver probes oversized literals, compile-before-
execute behavior, operator fragments, deep but bounded grouping, source-size enforcement, and step
exhaustion. These are robustness cases, not proof of fuzzing.

Run with PEBBLE_BIN pointing at an executable:

    PEBBLE_BIN=sealed/reference/build/pebble python3 adversarial/test_adversarial.py

The driver creates only a named temporary regular file through Python's standard temporary-file API
and removes it in a finally block.
