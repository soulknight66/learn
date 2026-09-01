# Public tests

`test_public.py` is a deterministic black-box suite for token positions,
accepted and rejected whitespace bytes, one-line diagnostic phases and CLI
usage failures, precedence, 64-bit behavior, declarations, control flow, and
native/interpreted equivalence.

Run it against the learner build:

```bash
python3 public_tests/test_public.py
```

The untouched starter is expected to pass the lexer tests and fail tests that
need unfinished stages. To check another build without modifying the suite:

```bash
MICA_BIN=path/to/mica python3 public_tests/test_public.py
```

Tests create short-lived files only below `environment/.test-work` because this
host may not provide a system temporary directory. No sealed fixture is loaded.
