# Environment

The project uses only Python's standard library and requires Python 3.10 or newer. The generation host
provides CPython 3.11.5 at `/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3`. Its unqualified
`python3` is CPython 3.6.8 and cannot import dataclasses or parse modern union annotations. No network
access, package installation, compiler toolchain, or environment variables are required.

Run commands from the repository root. The package is intentionally not installed:

```bash
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
PYTHONPATH=starter /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest discover -s public_tests -v
```

Set `PYTHONDONTWRITEBYTECODE=1` if the workspace must remain free of `__pycache__` directories. Locale
must not affect the language because identifiers, digits, encoding, and number output are explicitly
defined.
