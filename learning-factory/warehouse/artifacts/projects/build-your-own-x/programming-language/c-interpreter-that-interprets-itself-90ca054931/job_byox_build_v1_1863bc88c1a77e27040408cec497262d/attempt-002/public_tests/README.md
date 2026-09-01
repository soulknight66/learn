# Public black-box tests

Run the suite against one executable:

```sh
python3 public_tests/run_tests.py starter/build/minic
```

These smoke tests cover precedence, loops, calls, short-circuiting, one syntax error, and the
command-line step budget. They intentionally do not reveal the complete validator. Add your own
tests for every limit and semantic rule in `REQUIREMENTS.md`.

The runner uses only Python's standard library, reports each case, and exits nonzero on any
failure. It treats output, exit status, and selected diagnostic fragments as observable behavior.
