# Sealed reference tests

This validator-only suite exercises the complete implementation through its
public process boundary. It checks exact statuses and diagnostics, static name
resolution, limits, arithmetic traps, atomic output preservation, and
interpreter/compiler equivalence. It also injects a `/dev/full` output failure
into both backends and verifies capture bounds plus descendant cleanup in the
shared process runner.

```bash
make -C sealed/reference
PEBBLE_BIN="$PWD/sealed/reference/pebble" \
  python3 sealed/reference_tests/run_tests.py
```

Each subprocess uses an argv array, a fresh session, at most 65,536 retained
bytes per stream, a bounded timeout with group-wide TERM/KILL cleanup, and a
fresh temporary directory. Generated assembly is linked only inside that
directory.
