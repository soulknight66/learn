# Starter guide

Implement the `TODO` markers in this order:

1. `minibox/models.py`
2. `minibox/archive.py`
3. `minibox/state.py`
4. `minibox/runtime.py`
5. `minibox/workspace.py` and `minibox/cli.py`

The migration is intentionally supplied: study how its trigger complements, but does not replace, application-level checks. Keep the public API stable. You may add private helpers and additional tests.

Run one test module while iterating, for example:

```bash
PYTHONPATH=starter python3 -m unittest -v public_tests.test_models
```

Do not use `tarfile.extract()`/`extractall()`, shell strings, inherited caller environments, or unbounded subprocess waits.
