# Public tests

These tests exercise the learner-visible Minibox contract without starting Linux
namespaces or requiring elevated privileges.  They use only Python's standard
library.

From the repository root, run them against the starter implementation with:

```bash
PYTHONPATH=starter python3 -m unittest discover -s public_tests -v
```

All filesystem fixtures are created in temporary directories.  In particular,
the plan tests inspect argument vectors but never invoke `unshare`.
