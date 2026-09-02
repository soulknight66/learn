# Public tests

These tests are executable examples of the reader, evaluator, state, error, and CLI contracts. Run:

```bash
PEBBLE_PYTHON=/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3
TMPDIR=environment "$PEBBLE_PYTHON" environment/check_runtime.py
PYTHONDONTWRITEBYTECODE=1 TMPDIR=environment PYTHONPATH=starter \
  "$PEBBLE_PYTHON" -m unittest discover -s public_tests -v
```

They intentionally omit many malformed strings, special-form shape errors, built-in type failures,
closure lifetime cases, and deep tail calls. Passing them does not replace the normative requirements or
learner-authored tests. Keep `TMPDIR=environment` in restricted workspaces so file-mode tests have a
writable temporary location.
