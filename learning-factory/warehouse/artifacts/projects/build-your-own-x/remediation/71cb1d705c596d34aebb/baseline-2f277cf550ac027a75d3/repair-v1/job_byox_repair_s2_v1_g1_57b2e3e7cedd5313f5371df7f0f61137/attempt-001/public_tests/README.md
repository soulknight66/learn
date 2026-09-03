# Public black-box tests

`test_shell.py` exercises only behavior stated in `REQUIREMENTS.md`. It does
not import or assume a source layout. Set `MSH_BIN` to an absolute or relative
executable path:

```sh
MSH_BIN=starter/msh python3 public_tests/test_shell.py
```

The suite uses bounded subprocess and PTY deadlines. It includes positive
background-pipeline, `jobs`, and `fg` coverage for M5. On POSIX hosts with
Python PTY support it also checks foreground terminal handoff and Ctrl-C; that
case is skipped when PTY support is unavailable. A failing starter is expected;
individual tests should turn green as milestones are implemented.
