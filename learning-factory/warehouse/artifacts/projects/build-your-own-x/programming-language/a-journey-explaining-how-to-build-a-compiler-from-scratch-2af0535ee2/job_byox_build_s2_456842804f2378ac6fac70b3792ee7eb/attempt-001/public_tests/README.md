# Public tests

`run_tests.py` treats the compiler as a black-box executable. It checks representative lexing, precedence, bindings, diagnostics, runtime failure, and disassembly behavior without exposing exhaustive evaluation cases.

```sh
python3 public_tests/run_tests.py --binary starter/build/sprig
```

The runner creates isolated temporary source files, starts the binary without a shell, captures both output streams, enforces a three-second timeout, and kills the process group on timeout. A nonzero runner exit means at least one contract check failed.
