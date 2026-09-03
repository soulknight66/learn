# Learner and agent guide

Learners work only in a generated learner view and only modify `starter/`. Before starting, run
`environment/export_views.py verify . --role learner`. If `sealed/`, `adversarial/`, `debugging/`,
`review_exercises/`, or `benchmarks/` exists, this is the instructor/source artifact rather than a
learner view; ask for the separate learner export. Do not distribute the complete source artifact
as a learner checkout.

Preserve the public interfaces documented in `REQUIREMENTS.md`. Use only the Python standard
library. Runtime subprocesses must use argument arrays, bounded timeouts, captured output, and a new
process session; never invoke a shell. Do not run a real container unless you created the rootfs and
have explicitly opted in. Unit tests must use temporary directories and fake process launchers.

Run from the repository root:

```bash
PYTHON311="${PYTHON311:-/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3}"
"$PYTHON311" -c 'import sys; print(sys.version.split()[0]); sys.exit(0 if sys.version_info >= (3, 11) else "Python 3.11+ required")'
TMPDIR="${TMPDIR:-$PWD}" PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=starter \
  "$PYTHON311" -m unittest discover -s public_tests -v
"$PYTHON311" environment/export_views.py verify . --role learner
"$PYTHON311" environment/check_host.py
```

The public tests are examples, not a complete security test suite. A passing local run is not proof
that namespace or filesystem isolation is safe.
