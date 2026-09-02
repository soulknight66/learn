# Public smoke tests

The test driver checks a small, disclosed subset of the contract against
`starter/pebble`. It covers precedence, variables, control flow, one static
error, one runtime error, and a compile/link/run round trip.

```bash
make -C starter
python3 public_tests/run_tests.py
```

To test another implementation:

```bash
PEBBLE_BIN=/absolute/path/to/pebble python3 public_tests/run_tests.py
```

These cases are not exhaustive. Passing them is not evidence of memory safety,
resource-bound enforcement, interpreter/compiler equivalence, or independent
validation.
