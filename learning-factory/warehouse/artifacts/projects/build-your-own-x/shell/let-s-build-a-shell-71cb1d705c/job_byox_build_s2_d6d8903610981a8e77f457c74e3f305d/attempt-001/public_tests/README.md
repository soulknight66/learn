# Public black-box tests

`test_shell.py` exercises only behavior stated in `REQUIREMENTS.md`. It does
not import or assume a source layout. Set `MSH_BIN` to an absolute or relative
executable path:

```sh
MSH_BIN=starter/msh python3 public_tests/test_shell.py
```

The suite uses bounded subprocess timeouts. A failing starter is expected;
individual tests should turn green as milestones are implemented.
