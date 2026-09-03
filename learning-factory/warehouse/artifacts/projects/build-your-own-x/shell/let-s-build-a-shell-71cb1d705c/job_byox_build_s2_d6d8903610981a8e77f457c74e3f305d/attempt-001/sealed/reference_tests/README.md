# Sealed reference tests

These instructor-side tests extend the public contract checks with malformed
grammar, descriptor precedence, process statuses, job lifecycle, and a PTY
signal test. They remain black-box tests even though they are sealed.

```sh
MSH_BIN="$PWD/sealed/reference/msh" \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  sealed/reference_tests/test_reference.py
```

All subprocess and PTY reads use bounded deadlines. The PTY check is skipped
if the host lacks the Python `pty` module or a usable controlling terminal.
