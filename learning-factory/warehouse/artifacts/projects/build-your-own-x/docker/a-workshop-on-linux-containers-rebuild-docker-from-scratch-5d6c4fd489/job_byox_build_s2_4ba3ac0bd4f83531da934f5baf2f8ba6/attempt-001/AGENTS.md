# Learner and agent guide

Work only in `starter/`. Treat `sealed/`, `adversarial/`, `debugging/`, `review_exercises/`, and
`benchmarks/` as evaluator-controlled material unless an instructor explicitly reveals a stage.
Do not read a sealed directory to solve a learner stage.

Preserve the public interfaces documented in `REQUIREMENTS.md`. Use only the Python standard
library. Runtime subprocesses must use argument arrays, bounded timeouts, captured output, and a new
process session; never invoke a shell. Do not run a real container unless you created the rootfs and
have explicitly opted in. Unit tests must use temporary directories and fake process launchers.

Run from the repository root:

```bash
PYTHONPATH=starter python3 -m unittest discover -s public_tests -v
python3 environment/check_host.py
```

The public tests are examples, not a complete security test suite. A passing local run is not proof
that namespace or filesystem isolation is safe.
