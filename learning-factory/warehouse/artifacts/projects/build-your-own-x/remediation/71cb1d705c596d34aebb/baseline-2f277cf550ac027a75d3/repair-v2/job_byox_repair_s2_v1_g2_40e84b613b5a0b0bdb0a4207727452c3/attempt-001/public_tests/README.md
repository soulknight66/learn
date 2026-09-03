# Public black-box tests

`test_shell.py` exercises only behavior stated in `REQUIREMENTS.md`. It does
not import or assume a source layout. Set `MSH_BIN` to an absolute or relative
executable path:

```sh
MSH_BIN=starter/msh \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  public_tests/test_shell.py
```

Python 3.9 or newer is required. Ordinary targets run in new sessions; on a
timeout the harness sends bounded TERM/KILL escalation to the target process
group and captures its output. The suite also uses bounded PTY deadlines. It includes positive
background-pipeline, `jobs`, and `fg` coverage for M5. On POSIX hosts with
Python PTY support it also checks foreground terminal handoff and Ctrl-C; that
case is skipped when PTY support is unavailable. A failing starter is expected;
individual tests should turn green as milestones are implemented.
