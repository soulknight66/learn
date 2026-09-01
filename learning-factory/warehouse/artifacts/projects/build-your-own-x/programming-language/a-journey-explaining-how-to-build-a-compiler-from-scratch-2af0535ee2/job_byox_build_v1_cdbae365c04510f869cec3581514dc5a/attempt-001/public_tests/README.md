# Public tests

`test_cli.py` checks only behavior stated in `REQUIREMENTS.md`, through the executable boundary. Point
it at any implementation with `PEBBLE_BIN`:

```sh
PEBBLE_BIN=/absolute/path/to/pebble python3 public_tests/test_cli.py
```

These cases intentionally omit several integer boundaries, malformed-token combinations, limit
settings, API ownership checks, and malformed-bytecode defenses. Passing them is not a completeness or
security claim.
