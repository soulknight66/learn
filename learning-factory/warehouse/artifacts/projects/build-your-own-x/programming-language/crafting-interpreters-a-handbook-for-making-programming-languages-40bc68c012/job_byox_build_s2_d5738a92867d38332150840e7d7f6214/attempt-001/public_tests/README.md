# Public tests

`MicaPublicTest.java` is a dependency-free smoke and contract suite. It checks representative scanning,
precedence, scope, control flow, diagnostics, short-circuit behavior, VM parity, and malformed bytecode.
It is intentionally not exhaustive.

From the repository root:

```bash
public_tests/run.sh
```

To exercise another source tree implementing the same package/API:

```bash
SOURCE_ROOT=sealed/reference public_tests/run.sh
```

The script compiles into a temporary directory and removes it on exit. A nonzero exit means at least
one assertion failed or compilation did not succeed.
