# Public tests

These black-box `unittest` cases define representative API behavior. Run them with:

```bash
PYTHONPATH=starter python3 -m unittest discover -s public_tests -v
```

An untouched starter is expected to fail. The tests intentionally omit many hostile cases, including
some tar types, decompression limits, database corruption, cross-process races, and descendant process
cleanup. Passing them is a milestone, not proof of sandbox security or production readiness.
