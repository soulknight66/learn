# Shell Requirements

This document is the behavioral contract for `byosh`. “Must” marks required behavior; “may” marks an
optional extension. Unless stated otherwise, requirements apply in both `-c` and standard-input modes.

## 1. Program interface — Milestone 0

The starter directory must build an executable named `byosh`.

```text
./byosh
./byosh -c COMMAND
```

- With `-c COMMAND`, the shell must parse and execute `COMMAND`, then exit. `COMMAND` is one argument;
  callers are responsible for quoting it for their invoking environment.
- With no arguments, the shell must read newline-delimited commands from standard input until the
  `exit` built-in or end-of-file.
- Any other argument shape must print a concise usage diagnostic to standard error and return a
  nonzero status.
- A blank line must have no effect. End-of-file must not be reported as an error.
- The shell must not call a pre-existing shell to interpret command text.
- When standard input is a terminal, the shell must write the prompt `byosh$ ` to standard error before
  accepting a new command. It must not print a prompt in non-interactive mode.
- In `-c` mode, the shell process must return the command or pipeline status. In standard-input mode,
  it must continue after a per-line syntax error and return the status of the last nonblank line at
  end-of-file. An explicit `exit` overrides that default as described below.

Input is line-oriented. A required command is contained on one logical line; multiline quoting and
line continuation are outside the required scope.

## 2. Command language — Milestone 1

The required grammar, written informally, is:

```text
line       := pipeline [ "&" ]
pipeline   := command { "|" command }
command    := { word | redirection }+
redirection := "<" word | ">" word | ">>" word
```

Here, the quoted symbols describe operators, not quote characters in the input.

### Words and quoting

- Outside quotes, spaces and tabs delimit words.
- The operators `|`, `<`, `>`, `>>`, and `&` must be recognized without requiring surrounding
  whitespace.
- A backslash outside quotes must make the next character part of the current word.
- Matching single or double quotes must group their contents into one word and must not become part of
  that word. Spaces and operator characters inside quotes are literal.
- Adjacent quoted and unquoted fragments with no delimiter must form one word.
- An empty quoted string must produce an empty argument.
- An unmatched quote or a final unquoted backslash must be a syntax error.

The required shell performs no variable expansion, command substitution, wildcard expansion, field
splitting, or comment removal. Those features may be added later only if they do not alter required
cases. Inside either supported quote style, characters are otherwise literal for the required subset.

### Operators and errors

- A pipeline must contain a command on each side of every `|`.
- `&` is valid only once and only at the end of the line.
- Each redirection operator must be followed by exactly one filename word. Redirection operators may
  appear before, between, or after command arguments; they do not become arguments.
- A command may contain at most one input redirection and one output redirection. Repeating a
  redirection for the same stream must be a syntax error; no file from that line may be opened.
- A command containing only redirections is outside the required subset and may be rejected.
- Empty pipeline members, missing filenames, unexpected operators, and malformed quotes must produce a
  diagnostic, set status 2, launch no part of that line, and leave the shell usable.
- One input line contains at most one pipeline. `;`, `&&`, `||`, and parentheses have no special
  required meaning and may be diagnosed as unsupported.

Parsing must finish successfully before any process for that line is launched or any requested file is
opened. If the scaffold's documented command or argument capacity would be exceeded, that must also be
a syntax error rather than a partial parse.

## 3. Commands and built-ins — Milestone 2

### External commands

- A command not recognized as a built-in must be executed as an external program.
- A name containing `/` must be tried as the supplied path. Other names must be resolved using the
  process environment's `PATH`.
- Arguments, including empty arguments, must arrive in their original order.
- Failure to find a program must produce a diagnostic and command status 127 without terminating the
  shell. A located file that cannot be executed as a program image, including an executable text file
  without a valid interpreter header, must not be passed to a host shell; it must produce a diagnostic
  and status 126. Other execution failures must also produce a diagnostic and nonzero status.
- The status of a foreground pipeline is the status of its last command. Normal exit statuses must be
  preserved. A command ended by a signal must yield a nonzero status.

### Built-ins

The shell must recognize `cd`, `pwd`, `exit`, `jobs`, `fg`, and `bg` without consulting `PATH`.

- `cd [DIRECTORY]` must change the shell's working directory. With no directory, it uses `HOME`; with
  more than one directory, an unset `HOME`, or a failed directory change, it must diagnose failure and
  leave the current directory unchanged.
- `pwd` must print the shell's current working directory followed by a newline and reject unexpected
  operands.
- `exit [STATUS]` must request shell termination. With no status it uses the shell's current status.
  With one valid integer it uses that value as the process exit status. A nonnumeric status must be
  diagnosed and terminate the shell with status 2. Excess operands must be diagnosed with status 2 but
  must not terminate the input-reading shell.
- `jobs`, `fg`, and `bg` follow the job requirements in Sections 5 and 6.

Built-ins must execute in the shell process when used as a standalone foreground command. In a pipeline
or background job, `cd`, `pwd`, `jobs`, and `exit` must execute in a child context, so state changes do
not affect the parent shell and output can follow that command's descriptor setup. `fg` and `bg` must
diagnose that they are unavailable in a pipeline or background context.

## 4. Redirections and pipelines — Milestone 3

Redirections apply to the command they occur in:

- `< FILE` must make `FILE` the command's standard input and fail if it cannot be opened for reading.
- `> FILE` must make `FILE` the command's standard output, creating it if needed and truncating it if it
  exists.
- `>> FILE` must make `FILE` the command's standard output, creating it if needed and appending if it
  exists.
- Open or descriptor-setup failures must prevent the affected command from executing and must produce a
  nonzero status and diagnostic.

For `A | B`, the default standard output of `A` must feed the default standard input of `B`. Longer
pipelines must connect each adjacent pair. An explicit redirection on a command overrides the pipeline
endpoint for that same standard descriptor.

All pipeline members must be launched before the shell waits for any member. Every process, including
the shell, must close pipe and redirection descriptors it no longer needs. A foreground pipeline must
not return control until every member has exited or stopped; it reports the last member's status.

Built-ins whose output is meaningful in a pipeline, including `pwd`, must honor pipeline and file
redirection. Redirections around a parent-executed built-in must be restored before the next prompt or
command.

## 5. Background jobs — Milestone 4

- A line ending in `&` must start one background job and return for the next command without waiting for
  that job to finish.
- A job is the entire pipeline, not an individual process. Each job must have a positive shell-assigned
  job identifier, the original command text, and a state sufficient to distinguish running, stopped,
  and completed work.
- The shell must observe and reap all children. Completed background processes must not remain as
  zombies, including when several exit in quick succession or while an unrelated foreground job is
  still running.
- `jobs` must reject operands and report each known non-foreground job on standard output as
  `[N] Running COMMAND` or `[N] Stopped COMMAND`, where `N` is its job identifier. Runs may contain
  additional spacing, but the fields and their order must remain recognizable.
- Completion must be reported once on standard error as `[N] Done COMMAND` during child-state
  collection, after which the completed job must be removed.
- Starting a background job must leave a successful launch status. A later failure within that job does
  not retroactively change the status of an unrelated foreground command.
- On normal shell exit, the shell must reap children that have already changed state, send `SIGHUP` to
  every remaining tracked job process group, and send `SIGCONT` as well to a tracked stopped job. It
  must not wait indefinitely or signal an unrelated process.

Child-state handling must remain correct when a child exits before its job has been fully recorded.

## 6. Interactive job control — Milestone 5

These requirements apply only when the shell has a controlling terminal. Non-interactive execution
must not attempt terminal ownership operations.

- The shell must remain in its own process group and retain or regain foreground ownership of its
  controlling terminal whenever it reads a command.
- Every external pipeline must occupy one process group distinct from the shell, with all members in
  that group. Process-group setup must be safe if either parent or child runs first.
- Before waiting for a foreground job, the shell must give that job's process group foreground terminal
  ownership. After the job exits or stops, the shell must reclaim terminal ownership before prompting.
- Terminal-generated interrupt and stop signals intended for a foreground job must not terminate or
  stop the shell. Child processes must receive ordinary interactive signal behavior.
- Waiting must observe exited, signaled, stopped, and continued child states and update the aggregate
  job state accordingly.
- `fg [JOB]` must continue the selected job if necessary, give it the terminal, and wait until it exits
  or stops. `bg [JOB]` must continue the selected stopped job without giving it the terminal.
- A job operand may be `%N` or bare `N`, where `N` is the job identifier printed by `jobs`. If the
  operand is omitted, the most recently assigned eligible job must be selected. A malformed or unknown
  job operand, or an omitted operand when no eligible job exists, must produce a diagnostic and a
  nonzero status without affecting other jobs.

Preserving and restoring job-specific terminal modes is a permitted extension; reclaiming terminal
ownership reliably is required.

## 7. Robustness and quality — Milestone 6

- The shell must not crash, hang, or execute a partial line for any diagnosed syntax error.
- Recoverable allocation, file, process, descriptor, wait, group, and terminal-control failures must
  produce useful diagnostics and leave the shell in the safest recoverable state.
- All diagnostics must go to standard error. Normal command and built-in output must go to standard
  output.
- Input buffers, tokens, parsed commands, job records, and descriptors must have explicit ownership and
  be released when no longer needed.
- Waiting and notification logic must tolerate interrupted system calls and rapid state changes without
  relying on arbitrary sleeps.
- The code must compile using the scaffold's warning flags. Required tests must use bounded timeouts for
  pipeline and terminal interactions.

## Acceptance checklist

A completed submission demonstrates all of the following from a clean build:

- direct-command and standard-input modes;
- quote, escape, adjacency, and syntax-error cases;
- external command success, lookup failure, built-ins, and preserved shell state;
- input, truncate-output, and append-output redirections;
- a multi-stage pipeline large enough to expose incorrect sequential waiting;
- background completion and reaping;
- interactive stop, `jobs`, `bg`, and `fg` through a pseudo-terminal;
- continued operation after representative parse and system-call failures.

Optional features are not substitutes for any required case.
