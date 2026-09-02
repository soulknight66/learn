# Sealed reference tests

This suite validates behavior beyond the public examples: source locations, malformed forms, built-in
type boundaries, lexical capture, 6,000 tail calls, compiler/evaluator equivalence, malformed bytecode,
and CLI failures.

Run from the repository root with the pinned interpreter:

```bash
PYTHONPATH=sealed/reference /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  -m unittest discover -s sealed/reference_tests -v
```
