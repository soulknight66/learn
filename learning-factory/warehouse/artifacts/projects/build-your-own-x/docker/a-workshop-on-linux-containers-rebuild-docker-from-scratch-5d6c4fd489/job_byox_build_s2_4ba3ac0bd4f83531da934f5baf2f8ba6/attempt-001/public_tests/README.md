# Public tests

These deterministic `unittest` examples exercise the supplied specification and path-boundary
warm-up. They never start a namespace, use the network, or modify host files outside temporary
directories.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=starter python3 -m unittest discover -s public_tests -v
```

The suite intentionally does not reveal evaluator cases for planner flag order, executable
validation, concurrent SQLite claims, invalid transitions, oversized payloads, or timeout cleanup.
Add focused tests for those requirements while implementing the TODO stages.
