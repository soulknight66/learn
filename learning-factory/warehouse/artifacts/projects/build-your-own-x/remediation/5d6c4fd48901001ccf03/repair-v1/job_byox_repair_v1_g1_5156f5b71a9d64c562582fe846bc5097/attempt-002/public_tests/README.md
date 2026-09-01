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

For staged feedback, substitute one filename at a time:

```bash
PYTHONPATH=starter python3 -m unittest discover -s public_tests -p 'test_public_config.py' -v
PYTHONPATH=starter python3 -m unittest discover -s public_tests -p 'test_public_rootfs.py' -v
PYTHONPATH=starter python3 -m unittest discover -s public_tests -p 'test_public_plan.py' -v
PYTHONPATH=starter python3 -m unittest discover -s public_tests -p 'test_public_state.py' -v
PYTHONPATH=starter python3 -m unittest discover -s public_tests -p 'test_public_runtime.py' -v
```

Runtime tests depend on the earlier configuration and state stages. The API
surface check is in `test_public_api.py`. The untouched starter is expected to
report scaffold errors until the corresponding stages are implemented.
