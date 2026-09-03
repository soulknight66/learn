# Public tests

These deterministic `unittest` examples exercise the supplied specification and path-boundary
warm-up. They never start a namespace, use the network, or modify host files outside temporary
directories.

```bash
PYTHON311="${PYTHON311:-/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3}"
"$PYTHON311" -c 'import sys; print(sys.version.split()[0]); sys.exit(0 if sys.version_info >= (3, 11) else "Python 3.11+ required")'
TMPDIR="${TMPDIR:-$PWD}" PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=starter \
  "$PYTHON311" -m unittest discover -s public_tests -v
```

The discovery suite intentionally stays green against the untouched starter. After implementing a
stage, run its executable checkpoint; each command is expected to fail before that stage is done:

```bash
TMPDIR="${TMPDIR:-$PWD}" PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=starter \
  "$PYTHON311" -m unittest public_tests.checkpoints.Stage3PlannerCheckpoint -v
TMPDIR="${TMPDIR:-$PWD}" PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=starter \
  "$PYTHON311" -m unittest public_tests.checkpoints.Stage4RegistryCheckpoint -v
TMPDIR="${TMPDIR:-$PWD}" PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=starter \
  "$PYTHON311" -m unittest public_tests.checkpoints.Stage5RunnerCheckpoint -v
```

These are happy-path and interface checkpoints, not evaluator coverage. They omit strict flag
order, concurrent SQLite claims, invalid transitions, timeout cleanup, and path-race cases.
