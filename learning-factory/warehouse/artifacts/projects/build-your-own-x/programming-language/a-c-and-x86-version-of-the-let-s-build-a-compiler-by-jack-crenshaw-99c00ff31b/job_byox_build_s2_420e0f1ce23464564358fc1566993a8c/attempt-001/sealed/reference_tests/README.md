# Sealed reference tests

This validator-only suite exercises the complete implementation through its
public process boundary. It checks exact statuses and diagnostics, static name
resolution, limits, arithmetic traps, atomic output preservation, and
interpreter/compiler equivalence.

```bash
make -C sealed/reference
PEBBLE_BIN="$PWD/sealed/reference/pebble" \
  python3 sealed/reference_tests/run_tests.py
```

Each subprocess uses an argv array, captured streams, a five-second timeout,
and a fresh temporary directory. Generated assembly is linked only inside that
directory.
