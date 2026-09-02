# Sealed reference tests

This suite validates behavior beyond the public examples: source locations, malformed forms, built-in
type boundaries, the total `empty?` predicate, lexical capture, 6,000 tail calls, bounded integer/nesting
behavior, compiler/evaluator equivalence, deep runtime data, controlled non-tail stack exhaustion,
malformed bytecode, CLI failures, exercise focus, and learner-view isolation.

Run from the repository root with the pinned interpreter:

```bash
PEBBLE_PYTHON=/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3
TMPDIR=environment "$PEBBLE_PYTHON" environment/check_runtime.py
PYTHONDONTWRITEBYTECODE=1 TMPDIR=environment PYTHONPATH=sealed/reference "$PEBBLE_PYTHON" \
  -m unittest discover -s sealed/reference_tests -v
```
