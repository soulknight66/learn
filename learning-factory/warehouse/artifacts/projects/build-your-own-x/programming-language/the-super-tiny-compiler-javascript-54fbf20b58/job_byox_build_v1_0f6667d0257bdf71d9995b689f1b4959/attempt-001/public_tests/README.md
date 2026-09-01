# Pebble public tests

These zero-dependency tests describe the learner-visible Pebble contract in small stages:

1. tokenization and locations;
2. parsing and operator precedence;
3. tree-walking execution and program-wide variables;
4. compiler/VM execution and backend parity;
5. stable runtime error categories and bounded execution.

Run every stage from the repository root with:

```sh
node --test public_tests/*.test.mjs
```

Or run `npm test` from `starter/`. A single stage can be run by naming its file. The supplied starter
is intentionally incomplete, so failures ending in `NOT_IMPLEMENTED` are expected until the
corresponding `TODO` is finished.

These are examples, not an exhaustive specification. Also test boundary cases while implementing:
comments at end-of-file, nested control flow, invalid token sequences, all operator type errors,
and both execution backends.
