# Public smoke tests

The test driver checks a small, disclosed subset of the contract against
`starter/pebble`. It covers precedence, variables, control flow, one static
error, one runtime error, and a compile/link/run round trip.

Before the parser exists, an independent lexer milestone gives earlier
feedback on trivia skipping, token kinds, lexemes, values, and locations:

```bash
python3 public_tests/run_lexer_tests.py
```

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
validation. Every invoked binary is isolated in a fresh process session;
timeouts clean up its process group, and retained output is capped per stream.
