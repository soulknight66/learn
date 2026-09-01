# Sealed reference tests

This suite covers contract boundaries and malformed internal bytecode beyond the public milestones.
It is evaluator-only.

```bash
PYTHONPATH=sealed/reference python3 -m unittest discover -s sealed/reference_tests -p 'test_*.py' -v
```

The tests use only deterministic examples and generated finite matrices. They perform no random
fuzzing, networking, benchmarking, or external writes (CLI tests use subprocess pipes only).
