# `minish` reference implementation

This directory contains the sealed, independently written reference for the C
shell challenge. It is intentionally compact enough to audit while still using
real Unix processes, pipes, file descriptors, process groups, and terminal job
control.

Build and run it from the repository root:

```sh
make -C sealed/reference
sealed/reference/minish -c 'printf "hello\\n" | tr a-z A-Z'
printf 'pwd\nexit 7\n' | sealed/reference/minish
```

The accepted command-line forms are `minish`, `minish -c COMMAND`, and
`minish --help`. With no `-c`, commands are read one line at a time from
standard input. A prompt is printed only when both standard input and standard
output are terminals and input is being read; `-c` never prints a prompt or
prompt-only job notices.

## Implemented language

- A word can contain unquoted text, single-quoted literal text, double-quoted
  text, and backslash-escaped characters. Adjacent pieces form one word, and
  empty quotes form an empty argument.
- `|` creates a pipeline. `;` and `&` end pipelines; `&` runs the preceding
  pipeline in the background. Pipelines bind more tightly than list
  separators.
- `<`, `>`, and `>>` redirect standard input or output. Redirections are
  applied from left to right after pipe endpoints are installed, so a command
  redirection can override its pipe endpoint.
- `cd`, `pwd`, `exit`, `jobs`, `fg`, and `bg` are built in. A standalone
  foreground builtin executes in the shell process; a builtin in a pipeline or
  background job executes in a child and cannot change the parent shell.
- Every external pipeline gets one process group. When standard input controls
  a terminal, the foreground group owns the controlling terminal while it runs,
  and the shell
  ignores terminal-generated stop/interrupt signals. Per-process wait state is
  retained for background and stopped jobs.

This exercise language deliberately does **not** implement variables, command
substitution, globbing, comments, `&&`, `||`, here-documents, or stderr
redirection. Those tokens are not silently expanded; except for the recognized
operators, they remain ordinary word characters.

## Deterministic noninteractive behavior

Runs without a visible prompt print no launch line containing a volatile PID,
including job-control sessions whose stdout is redirected. `jobs` prints stable rows of the form
`[N] Running command`; completed jobs are reaped and omitted. `bg` prints
`[N] command`. A signal-safe self-pipe wakes an idle shell to collect background
state changes. At shell shutdown, remaining background process
groups receive `SIGHUP` and are reaped; a short grace period is followed by
`SIGKILL` so an abandoned child cannot hold a test pipe open indefinitely.
The first stage of a batch background pipeline reads `/dev/null` unless it has
an explicit `<` redirection, so it cannot race the shell for command input.

A job is `Done` only after every member is done, `Running` while any member is
running, and otherwise `Stopped` (a mixture of done and stopped members is
therefore stopped). Completed jobs are discarded rather than printed by
`jobs`. If a foreground job stops, the shell status is `128 + stop_signal` for
the rightmost stopped member, even if a later pipeline stage already exited.

Syntax errors are diagnosed before any command on that input line starts and
return status 2. A command that cannot be located returns 127; a located
command that cannot execute, including a script with a missing shebang
interpreter, returns 126. A completed pipeline's result is the status of its
last command. A valid
decimal operand to `exit` is reduced modulo 256; an invalid operand is an error
but does not itself terminate a still-running command loop. With no operand,
`exit` uses the most recent foreground pipeline status, so launching a later
background job does not overwrite it. An input line containing a NUL byte is
rejected in full with syntax status 2.

Run the sealed deterministic suite with:

```sh
python3 sealed/reference_tests/test_reference.py -v
# or
make -C sealed/reference test
```
