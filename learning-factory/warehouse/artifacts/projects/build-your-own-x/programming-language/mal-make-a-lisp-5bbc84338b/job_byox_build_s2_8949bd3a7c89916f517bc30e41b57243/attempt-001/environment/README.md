# Environment

The project requires Python 3.11 or newer and only its standard library. The factory-observed interpreter
is:

```text
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3
Python 3.11.5
```

The configured Java 21 toolchain is available but unused; Pebble's supplied scaffold and reference are
Python. No network access or package installation is needed.

Use `PYTHONPATH=starter` so imports resolve to your implementation. Python may create `__pycache__`
scratch directories while testing; they are not project artifacts and may be removed explicitly.
