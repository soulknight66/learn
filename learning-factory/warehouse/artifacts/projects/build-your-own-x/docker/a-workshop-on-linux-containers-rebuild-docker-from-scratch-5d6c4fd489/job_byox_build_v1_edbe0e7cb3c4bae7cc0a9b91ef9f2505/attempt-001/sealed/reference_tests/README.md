# Reference tests

This directory contains validator-owned edge-case tests for the Minibox challenge.
It is intentionally kept under `sealed/`; do not copy it into a learner view.
The suite uses temporary files and fake execution backends.  It does not execute
a real namespace plan.

Run the reference implementation and all reference tests from the repository root:

```bash
PYTHONPATH=sealed/reference python3 -m unittest discover -s sealed/reference_tests -v
```

The tests can also be pointed at a learner implementation for deterministic local
validation:

```bash
PYTHONPATH=starter python3 -m unittest discover -s sealed/reference_tests -v
```
