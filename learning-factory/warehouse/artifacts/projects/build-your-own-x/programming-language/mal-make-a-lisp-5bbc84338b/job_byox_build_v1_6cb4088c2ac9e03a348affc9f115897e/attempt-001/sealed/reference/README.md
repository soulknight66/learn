# Sealed reference implementation

This directory contains the evaluator-controlled reference package for Sprig. It is independently
generated from `REQUIREMENTS.md` and is not learner material.

Run the public conformance suite against it from the repository root:

```bash
PYTHONPATH=sealed/reference python3 -m unittest discover -s public_tests -p 'test_*.py' -v
```

Run the deeper reference suite with the command documented in `sealed/reference_tests/README.md`.
Neither command constitutes independent factory validation by itself.
