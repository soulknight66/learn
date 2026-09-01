# Mini-shell starter

This directory is an intentionally **PARTIAL** C scaffold. It builds, accepts
empty input, and connects three stages, but it does not tokenize, parse, or
execute commands yet. Every shell-semantic path is left as a `TODO` for the
learner; this is not a reference implementation.

Build and inspect the command-line interface:

```sh
make -C starter
./starter/minish --help
./starter/minish -c '   '
```

Running `minish` without arguments reads standard input. It prints `minish$ `
only when both input and output are terminals, so redirected input and an
immediate EOF are safe and deterministic. The coordinator also rejects an
embedded NUL before the incomplete language stages see that line.

## Interfaces and ownership

- `include/lexer.h` owns a `TokenList`. A successful lexer appends exactly one
  `TOKEN_END`; token text is released by `token_list_destroy`.
- `include/parser.h` owns a `CommandList` of pipelines, commands, and
  redirections. The parser validates the entire line before execution;
  `command_list_destroy` releases every nested allocation.
- `include/executor.h` consumes a command list and updates `ShellState` without
  taking ownership of the syntax tree. Each pipeline retains display text for
  a future job-table entry.
- `src/shell.c` is the coordinator and guarantees cleanup after every stage.
  It also splits an embedded-newline `-c` operand into physical command lists,
  preserving per-line validation and early-exit boundaries.

Keep stage errors in `ShellError`, including a byte offset useful to the user.
Complete one stage at a time and keep these ownership boundaries; extend the
types when job control requires it. Preserve the command-line interface and use
the public tests from the repository root as a baseline. Those tests are
deliberately small; passing them is not evidence that a shell implementation is
complete.
