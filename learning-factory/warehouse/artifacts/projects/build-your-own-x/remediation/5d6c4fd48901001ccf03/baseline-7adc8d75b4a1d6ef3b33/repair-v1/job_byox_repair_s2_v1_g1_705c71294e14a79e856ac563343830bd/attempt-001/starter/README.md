# Starter guide

The starter completes the parsing and filesystem warm-up so you can focus on the isolation boundary.
Search for `TODO(stage` in `starter/minictr`.

## Suggested checkpoints

1. Run the public suite and read `spec.py` and `paths.py`. Add your own edge-case tests before
   changing them.
2. Implement `planner.build_launch_plan` and the ordered setup in `child.py`. Test the tuple of
   arguments and mock child syscalls before launching anything.
3. Implement the three transactional methods in `registry.Registry`. Open two registry connections
   in a test and prove only one claim succeeds.
4. Implement `runner.Runner.run` with an injected `popen_factory`. Use fakes to exercise timeout and
   cleanup.
5. Wire `cli.py plan` first. Keep actual `run` behind `--allow-execution` and use only a disposable
   rootfs.

Run:

```bash
PYTHON311="${PYTHON311:-/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3}"
"$PYTHON311" -c 'import sys; print(sys.version.split()[0]); sys.exit(0 if sys.version_info >= (3, 11) else "Python 3.11+ required")'
TMPDIR="${TMPDIR:-$PWD}" PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=starter \
  "$PYTHON311" -m unittest discover -s public_tests -v
"$PYTHON311" environment/check_host.py
```

The default tool path works on the supplied host; override `PYTHON311` elsewhere. Public discovery
covers the supplied warm-up and stays green initially. `public_tests/checkpoints.py` supplies one
explicitly opt-in, initially failing checkpoint per learner-owned stage. It does not disclose all
planner, concurrency, timeout, or path-race cases used by independent validation.
