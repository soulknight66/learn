# Learner agent guide

Work only in `starter/` and tests you create outside protected instructor material. Treat
`REQUIREMENTS.md` as normative and public tests as examples, not a complete specification.

## Commands

From the repository root:

```bash
PEBBLE_PYTHON=/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3
TMPDIR=environment "$PEBBLE_PYTHON" environment/check_runtime.py
PYTHONDONTWRITEBYTECODE=1 TMPDIR=environment PYTHONPATH=starter \
  "$PEBBLE_PYTHON" -m unittest discover -s public_tests -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=starter \
  "$PEBBLE_PYTHON" -m pebble.cli -e '(+ 20 22)'
```

## Constraints

- Use only the Python standard library.
- Do not import, copy, inspect, or modify `sealed/` or any exercise-local `sealed/` directory.
- Keep parsing separate from evaluation and keep environment lookup separate from both.
- Preserve the public names and exception hierarchy in the scaffold.
- Do not use Python `eval`, `exec`, `compile`, or a shell to execute Pebble programs.
- Do not turn recursion-limit increases into a substitute for tail-call handling.
- Emit language errors, not raw `KeyError`, `IndexError`, `TypeError`, or Python tracebacks.

When you add tests, prefer exact input/output assertions and table-driven malformed cases. A prose claim
that something works is not evidence; record the command and observed result.
