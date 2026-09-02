# Adversarial validator suite

This non-learner-visible suite probes hostile boundaries that the public smoke
tests omit: exact source-size edges, embedded/non-ASCII bytes, deep flat trees,
unary recursion, forbidden declaration placement, and failed atomic
publication.

```bash
make -C sealed/reference
PEBBLE_BIN="$PWD/sealed/reference/pebble" python3 adversarial/run_tests.py
```

The tests operate only in fresh temporary directories and invoke subprocesses
with argv arrays, captured streams, and bounded timeouts.
