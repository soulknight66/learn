# Public tests

These tests cover representative contract cases. They are intentionally incomplete: hidden validation may vary identifiers, archive ordering and metadata, state history, concurrency expectations, command arguments, and failure timing.

Run all public tests from the repository root:

```bash
PYTHONPATH=starter python3 -m unittest discover -s public_tests -v
```

Tests create isolated temporary directories and do not attempt a real namespace launch.
