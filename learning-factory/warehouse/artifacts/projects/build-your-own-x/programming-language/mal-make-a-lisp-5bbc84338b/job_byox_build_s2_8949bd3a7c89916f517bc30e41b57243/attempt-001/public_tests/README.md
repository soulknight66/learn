# Public tests

These tests are executable examples of the reader, evaluator, state, error, and CLI contracts. Run:

```bash
PYTHONPATH=starter python3 -m unittest discover -s public_tests -v
```

They intentionally omit many malformed strings, special-form shape errors, built-in type failures,
closure lifetime cases, and deep tail calls. Passing them does not replace the normative requirements or
learner-authored tests.
