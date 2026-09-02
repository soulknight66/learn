# Environment

The project requires Python 3.11 or newer and only its standard library. The factory-observed interpreter
is:

```text
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3
Python 3.11.5
```

The configured Java 21 toolchain is available but unused; Pebble's supplied scaffold and reference are
Python. No network access or package installation is needed.

Initialize and verify the runtime before test discovery:

```bash
PEBBLE_PYTHON=/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3
TMPDIR=environment "$PEBBLE_PYTHON" environment/check_runtime.py
```

The check reports the selected version and effective temporary directory, or exits 2 with a controlled
error. Use `PYTHONPATH=starter` so imports resolve to your implementation. In restricted workspaces, keep
`TMPDIR=environment` on test commands; this existing directory is writable and avoids dependence on host
`/tmp` policy. `PYTHONDONTWRITEBYTECODE=1` prevents cache artifacts. If omitted, Python may create
`__pycache__` scratch directories, which are not project artifacts and may be removed explicitly.
