# Sealed reference shell

This directory contains an independently written reference implementation for
the challenge. It is sealed because its structure and behavior reveal a full
solution.

Build it with:

```sh
make -C sealed/reference
```

The result is `sealed/reference/byosh`. Its only valid invocation forms are
interactive/input mode or one command-line pipeline:

```sh
sealed/reference/byosh
sealed/reference/byosh -c 'printf hello | tr a-z A-Z'
```

## Implemented language

Input is one pipeline per line. Spaces and tabs delimit words. Single quotes,
double quotes, and backslash preserve literal characters. Backslash escapes the
next character only outside quotes; it is an ordinary literal character inside
both quote styles. There is intentionally no variable expansion, command
substitution, globbing, comment syntax, or semicolon command list.

The parser recognizes `|`, `<`, `>`, `>>`, and a trailing `&`, including when
operators touch adjacent words. Redirections may occur among arguments. A
command may have at most one input and one output redirection (`>` and `>>`
both occupy the output slot); duplicates are syntax errors. An explicit
redirection is installed after pipe endpoints, so it overrides the associated
pipe endpoint. Empty commands, missing redirection paths, misplaced `&`, a
missing command beside a pipe, trailing escapes, and unclosed quotes are clear
parse errors with status 2.

## Execution and job control

Every external pipeline receives its own process group. All internal pipe and
launch-gate descriptors are moved above standard descriptors 0, 1, and 2, so a
caller may initially close stdin or stdout without corrupting pipeline wiring.
All pipes are created before forking; each child resets inherited signal
dispositions, installs pipe and file descriptors, closes unused descriptors,
and then calls `execvp`.

Interactive foreground children wait on a close-on-exec launch gate after
joining their process group. The parent publishes every PID, assigns the
terminal to that group, and only then releases the children. The shell waits
for the whole group, records stop/exit/signal state per child, then takes the
terminal back. Background state is updated only from `waitpid` evidence.
`SIGCHLD` stays blocked during state publication; an async-signal-safe handler
writes to a nonblocking self-pipe, and `pselect` atomically unblocks the signal
while waiting for either input or child activity. This removes the idle-input
lost-wakeup window without mutating the job table inside a signal handler.

The prompt is exactly `byosh$ ` on standard error and is shown only when stdin
is a terminal. Diagnostics and asynchronous job notices also use standard
error. A missing executable returns 127; other execution failures return 126;
a pipeline returns the status of its last command.

Supported built-ins are:

- `cd [DIR]` (`HOME` is used when no directory is supplied)
- `pwd`
- `exit [STATUS]`
- `jobs`
- `fg [%N|N]`
- `bg [%N|N]`

A single foreground built-in runs in the shell so state changes persist and
redirections still work, including when a standard descriptor was initially
closed. Output built-ins return failure when their write fails. In a pipeline
or background command, ordinary built-ins run in the child and cannot mutate
the parent. `fg` and `bg` reject that child-only context. `jobs` prints active
jobs as `[N] Running COMMAND` or `[N] Stopped COMMAND`; completed jobs receive
one `Done` notice and are removed. Omitted `fg` selects the highest active job
ID; omitted `bg` selects the highest stopped job, and `bg` rejects a running
job. A job is marked running only after `SIGCONT` succeeds. At normal shell
shutdown, remaining jobs receive `SIGHUP` and stopped jobs also receive
`SIGCONT`.

Run the private reference suite with:

```sh
make -C sealed/reference test
```
