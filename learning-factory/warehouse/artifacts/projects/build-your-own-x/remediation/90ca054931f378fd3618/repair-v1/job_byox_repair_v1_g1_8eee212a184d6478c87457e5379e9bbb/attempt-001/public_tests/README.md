# Public black-box tests

Run the suite against one executable:

```sh
python3 public_tests/run_tests.py starter/build/minic
```

These smoke tests cover precedence, loops, calls, short-circuiting, one syntax error, the
command-line step budget, and rejected command-line spellings. They intentionally do not reveal
the complete validator. Add your own tests for every limit and semantic rule in `REQUIREMENTS.md`.

The runner uses only Python's standard library, reports each case, and exits nonzero on any
failure. It treats output, exit status, and selected diagnostic fragments as observable behavior.
Each case runs in a new POSIX session with wall, CPU, address-space, open-file, and output-file
limits; the whole process group is killed on timeout and after the direct child exits. Captured
stdout and stderr are each capped at 65,536 bytes, and the suite has a 90-second aggregate wall
deadline.
