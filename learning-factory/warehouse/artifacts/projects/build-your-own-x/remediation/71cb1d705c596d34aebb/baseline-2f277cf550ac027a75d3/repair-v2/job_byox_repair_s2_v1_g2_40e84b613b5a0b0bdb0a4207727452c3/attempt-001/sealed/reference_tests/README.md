# Sealed reference tests

These instructor-side tests extend the public contract checks with malformed
grammar, byte-exact CR/LF tokenization, descriptor precedence and closed
standard descriptors, inherited signal dispositions and masks, strict numeric
operands, process statuses, job lifecycle, and PTY signal tests. They remain black-box
tests even though they are sealed.

```sh
MSH_BIN="$PWD/sealed/reference/msh" \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  sealed/reference_tests/test_reference.py
```

All subprocess, PTY reads, and child reaping use bounded deadlines. PTY cleanup
captures and signals the shell and foreground process groups with TERM/KILL
escalation. One PTY regression starts the shell with all six specified signals
blocked and verifies that Ctrl-C still interrupts a foreground child. PTY
checks are skipped if the host lacks the needed Python APIs or a usable
controlling terminal.
