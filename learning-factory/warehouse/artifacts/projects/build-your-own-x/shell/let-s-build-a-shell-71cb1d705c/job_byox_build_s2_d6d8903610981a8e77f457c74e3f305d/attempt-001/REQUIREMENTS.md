# Observable requirements for `msh`

The words **must**, **should**, and **may** describe testable requirements,
recommended robustness, and optional behavior respectively.

## 1. Invocation and input

- `msh -c COMMAND` must parse and execute exactly one command line and return
  its status. `msh` with no arguments must read newline-delimited commands from
  standard input until EOF.
- Any other arguments must produce a diagnostic and status 2.
- Interactive mode is enabled only when standard input and standard error are
  terminals. It must print `msh$ ` to standard error before each input line.
- Blank or whitespace-only lines must succeed without launching a process.
- An input line larger than 1 MiB may be rejected with status 2.

## 2. Grammar

The grammar for one line is:

```text
line       := pipeline ["&"]
pipeline   := command {"|" command}
command    := {word | "<" word | ">" word | ">>" word}+
```

Unquoted spaces and tabs separate tokens. `|`, `&`, `<`, `>`, and `>>` are
operators even without surrounding spaces. A backslash outside quotes makes
the next byte literal. Single quotes preserve every byte up to the next single
quote. Inside double quotes, backslash escapes the following byte; all other
bytes are literal. Quote delimiters are removed, adjacent quoted and unquoted
fragments form one word, and an empty quoted string is a valid empty word.

Expansion is out of scope: `$HOME`, `*`, `~`, `;`, parentheses, and backticks
have no special meaning and remain ordinary word bytes. NUL bytes need not be
accepted. Unterminated quotes, dangling backslashes, missing redirection
targets, empty pipeline stages, non-final `&`, duplicate input redirection, or
duplicate output redirection must print a diagnostic containing `syntax:` and
return 2 without launching any part of the line.

## 3. Execution and status

- Each external stage must use `fork` plus an `exec` family call with an argv
  array. PATH lookup is required. Failure to execute must be diagnosed as
  `msh: NAME: MESSAGE`; return 127 for not found and 126 for other exec errors.
- A pipeline may contain any number of stages up to available resources. Its
  status is the last stage's status. Normal exit `N` maps to `N`; signal `S`
  maps to `128 + S`.
- `<`, `>`, and `>>` must open a command's standard input, truncate-create
  output, and append-create output respectively. Files are created with mode
  `0666` filtered by the process umask. Redirection takes precedence over a
  pipeline endpoint on the same descriptor.
- The shell and children must close unused pipe and redirection descriptors.
  It must retry `waitpid` after `EINTR` and avoid zombies.

## 4. Built-ins

`cd`, `exit`, `jobs`, and `fg` are built-ins. When used as the sole foreground
stage, they run in the shell process so state changes persist. A built-in in a
pipeline or background job runs in a child and cannot alter parent state.

- `cd [DIR]` accepts zero or one argument; zero uses `HOME`. A missing `HOME`,
  too many operands, or `chdir` failure returns 1 with a diagnostic.
- `exit [N]` accepts zero or one decimal integer in 0..255. Zero arguments uses
  the most recent status. Bad operands or extra arguments return 2 without
  terminating the shell. A valid parent-context invocation terminates it.
- `jobs` accepts no operands and prints one line per live job as
  `[ID] Running COMMAND` or `[ID] Stopped COMMAND`, ordered by increasing ID.
- `fg [%ID]` accepts at most one job ID. With no ID it selects the greatest
  live ID. It moves the job to the foreground, continues it if stopped, waits
  for it, and returns its last-stage status. Unknown/invalid jobs return 1.

Parent-context built-ins must honor redirections and restore the shell's
original descriptors afterward.

## 5. Background jobs and terminal control

- A trailing `&` starts the entire pipeline without waiting and immediately
  returns 0. All its children must share a new process group. The shell prints
  `[ID] PGID` to standard error and assigns monotonically increasing IDs.
- Before each prompt, and before `jobs`, the shell must reap changed children
  without blocking and update job state. Completed jobs may be reported once
  on standard error and then removed.
- Every foreground pipeline must use its own process group. In interactive
  mode the shell gives that group the controlling terminal while waiting, then
  restores the terminal to its own group. The shell ignores terminal-stop
  signals while children restore default `SIGINT`, `SIGQUIT`, `SIGTSTP`,
  `SIGTTIN`, `SIGTTOU`, and `SIGCHLD` behavior.

No particular prompt behavior, notification timing, or terminal control is
required for non-interactive input beyond the status and reaping rules above.
