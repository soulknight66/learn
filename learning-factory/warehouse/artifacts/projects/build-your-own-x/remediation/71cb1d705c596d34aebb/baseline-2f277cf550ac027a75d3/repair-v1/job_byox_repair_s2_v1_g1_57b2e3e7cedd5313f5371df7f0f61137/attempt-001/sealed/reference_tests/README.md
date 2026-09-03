# Sealed reference tests

These instructor-side tests extend the public contract checks with malformed
grammar, byte-exact CR/LF tokenization, descriptor precedence and closed
standard descriptors, inherited signal dispositions, strict numeric operands,
process statuses, job lifecycle, and a PTY signal test. They remain black-box
tests even though they are sealed.

```sh
MSH_BIN="$PWD/sealed/reference/msh" \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  sealed/reference_tests/test_reference.py
```

All subprocess, PTY reads, and child reaping use bounded deadlines. PTY cleanup
captures and signals the shell and foreground process groups with TERM/KILL
escalation. The PTY check is skipped if the host lacks the Python `pty` module
or a usable controlling terminal.
