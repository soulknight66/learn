# Sealed reference tests

This suite extends the public sample with lexer failure cleanup, parser deep ownership, duplicate-redirection rejection, exit-status propagation, missing-command behavior, background reaping, redirection precedence, initially closed standard-descriptor cases, parent-side `cd`, common process groups, descriptor pressure under `RLIMIT_NOFILE=32`, and foreground Ctrl-C through a PTY.

Run it with a reference implementation directory:

```sh
sealed/reference_tests/run.sh sealed/reference
```

The PTY test covers one terminal-handoff path only. It is not proof against all scheduling races, stopped-job states, hostile environments, or long-running resource leaks.
