# Starter guide

Implement TODOs in this order:

1. `paths.py`: normalize archive names and prove resolved paths remain beneath a root.
2. `layer.py`: preflight tar metadata, implement whiteouts, then stream ordinary entries.
3. `store.py`: initialize the schema, register images, create records, and claim transitions.
4. `image.py`: hash ordered layers, build privately, and atomically publish snapshots.
5. `runner.py`: validate process inputs, bound logs, and terminate a process group on timeout.
6. `engine.py`: copy a rootfs and coordinate claim/run/finish.
7. `__main__.py`: expose the API without leaking tracebacks for expected domain errors.

`models.py` and `errors.py` define the contract and are complete. Search for `TODO(` to find the
implementation sites. Do not solve later stages by importing evaluator code.

Run one public module at a time while iterating:

```bash
PYTHONPATH=starter python3 -m unittest -v public_tests.test_paths
PYTHONPATH=starter python3 -m unittest -v public_tests.test_layers
PYTHONPATH=starter python3 -m unittest -v public_tests.test_engine
```
