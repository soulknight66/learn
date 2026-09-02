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
PYTHONPATH=starter python3 -m unittest discover -s public_tests -v
python3 environment/check_host.py
```

Public tests cover the supplied warm-up, immutability, and interface shape. They intentionally do
not disclose all planner, concurrency, timeout, or path-race cases used by independent validation.
