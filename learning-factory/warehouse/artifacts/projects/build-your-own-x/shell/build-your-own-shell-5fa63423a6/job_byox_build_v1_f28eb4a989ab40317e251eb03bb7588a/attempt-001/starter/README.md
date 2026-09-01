# Starter Workspace

Implement the shell in this directory. The scaffold defines the build shape and public interfaces;
TODO comments mark intended learner work, not necessarily the order in which it must be completed.

## Public executable contract

From this directory:

```sh
make
./byosh -c 'pwd'
printf 'pwd\nexit\n' | ./byosh
```

The scaffold builds immediately, but the two execution examples are expected to report the deliberate
Milestone 2 placeholder until execution is implemented.

The build must produce `./byosh`. Preserve its two supported invocation forms:

```text
./byosh
./byosh -c COMMAND
```

Read [../REQUIREMENTS.md](../REQUIREMENTS.md) for exact behavior. If source names or internal function
signatures differ from examples in prose, the checked-in headers and Makefile are the source of truth
for the scaffold; keep the executable behavior unchanged.

## Scaffold map

- `include/byosh.h` exposes the parser result types, capacity constants, and milestone hooks used by
  the public C tests.
- `src/main.c` supplies the command-line and input-loop baseline.
- `src/parser.c` begins with plain whitespace-separated words; quoting and operators are Milestone 1.
- `src/execute.c` is the execution milestone hook and initially returns a deliberate “not implemented”
  status.

`byosh_parse_line` receives writable input. In the initial contract, successful argument and path
pointers borrow storage from that input buffer, so they remain valid only while the buffer does. The
pipeline must always have a null-terminated `argv`, and capacity overflow must be diagnosed rather than
silently truncated.

Public parser tests compile against the existing names and fields in `include/byosh.h`. Preserve that
surface. You may add internal types, fields, functions, and source files as later milestones require,
provided the existing contract and Makefile targets remain compatible.

## Recommended order

1. Confirm a clean scaffold build and locate the input loop, shared types, and cleanup paths.
2. Complete tokenization and parsing. Test these without launching processes.
3. Add standalone built-ins and one external foreground command.
4. Add file redirections, then two-command and longer pipelines.
5. Add background job records and reliable child collection.
6. Enable terminal process groups and implement `jobs`, `fg`, and `bg` behavior.
7. Exercise failures, repeated commands, and cleanup under diagnostic builds.

Do not solve several stages in one large edit. A parser defect is much easier to isolate before process
and terminal state are involved.

## Build discipline

Use the provided Makefile rather than replacing it with an unrelated build system. Keep strict compiler
warnings enabled. If you add source files, add explicit dependencies and ensure `make clean` removes
only generated build products.

Common local checks are:

```sh
make clean
make
make check
make check-milestones
make -C ../public_tests cli SHELL_UNDER_TEST=../starter/byosh
```

`make check` is the scaffold's baseline parser test and should pass before learner changes.
`make check-milestones` describes the later parser target and initially fails. The `cli` target is a
black-box smoke test for a completed shell, so it also is not an initial baseline. Run the narrow tests
for your current milestone before using later targets as a progress check.

Optional sanitizer, debugger, or tracing tools vary by environment; see
[../environment/README.md](../environment/README.md). Do not make an optional tool a normal build
dependency.

## Testing notes

- Keep parser tests independent of host command output.
- Use temporary directories for redirection and `cd` cases.
- Use absolute paths or a controlled `PATH` when a test needs a fixture executable.
- Put deadlines around process and pipe tests.
- Use a pseudo-terminal for prompt, signal, and foreground-process-group behavior.
- On failure, terminate and collect every process started by the test.

The terminal is shared state. Manual experiments should use harmless commands and must return terminal
control to the invoking shell before they finish.

## Before declaring completion

Start from `make clean`, rebuild, run all public tests, and record any unsupported behavior. Check that
no test relies on fixed sleeps, prompt content beyond the prescribed `byosh$ ` text, the current
username, a global working directory, or commands that may not exist on another POSIX host.
