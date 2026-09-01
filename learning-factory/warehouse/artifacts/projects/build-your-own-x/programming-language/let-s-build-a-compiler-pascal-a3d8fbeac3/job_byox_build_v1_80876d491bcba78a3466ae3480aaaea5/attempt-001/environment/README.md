# Reproducible environment

The intended native toolchain is Free Pascal 3.2.x on a POSIX-like host, plus
Python 3.6 or newer for black-box tests. The implementation uses only standard
Free Pascal units (`SysUtils` and `Classes`); no network dependencies are needed.

Run the complete public check from the repository root:

```bash
environment/check.sh
```

`FPC` can select a compiler binary and `MICA_BIN` can select an already-built
executable. The script does not install software. It exits 2 when the compiler is
unavailable and no executable was supplied, keeping an unavailable dependency
distinct from a failed build or failed test.

Expected build products are `starter/bin/mica` and `starter/units/*`. They are
scratch artifacts, not source or evidence by themselves.
