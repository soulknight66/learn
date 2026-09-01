# `minish` requirements

Build a small Unix shell in C. The goal is not POSIX completeness: the goal is a
well-defined core that makes process creation, file-descriptor ownership,
parsing, and job control observable and testable.

The words **must**, **should**, and **may** distinguish required behavior,
recommended engineering practice, and optional extensions. Complete the core
before adding syntax not specified here.

## 1. Build and command-line interface

- `make -C starter` from the repository root must create `starter/minish`.
- The required implementation language is C. It must compile with GCC 8.5 or a
  compatible C compiler using the starter `Makefile`.
- `./starter/minish -c COMMAND` must execute exactly one command string and exit with its
  resulting shell status.
- With no arguments, `./starter/minish` must read commands from standard input until
  `exit` or end-of-file.
- `./starter/minish --help` must print a short usage message and exit zero.
- Unknown options and missing `-c` operands must be diagnosed on standard error
  and exit nonzero.
- The prompt `minish$ ` must be written only when both standard input and
  standard output refer to terminals. `-c` mode is never prompt-visible, even
  when both descriptors refer to terminals. Batch input must contain no prompt.
- End-of-file at an empty interactive prompt must terminate cleanly. A partial
  final line in batch input must still be evaluated.

The core has no startup files, configuration files, or command-line script-file
mode.

## 2. Input model

Each physical input line is one command list. A newline always ends that list;
a quote that is still open at that boundary is a syntax error. In `-c` input,
embedded newlines separate successive command lists. Multiline quoted words are
outside the core language.

The grammar below is descriptive EBNF. `WORD` is produced by the lexer.

```text
line        := [ list ]
list        := pipeline { separator pipeline } [ separator ]
separator   := ";" | "&"
pipeline    := command { "|" command }
command     := element { element }
element     := WORD | redirection
redirection := "<" WORD | ">" WORD | ">>" WORD
```

A `command` must contain at least one `WORD`; redirection-only commands are out
of scope. Operators are recognized without surrounding spaces, so `a|b>out`
and `a | b > out` have the same structure. `|` binds more tightly than `;` and
`&`. A separator applies to the whole pipeline on its left. A trailing `;` is
accepted, and a trailing `&` launches the preceding pipeline asynchronously.

Reject, at minimum:

- a leading or doubled pipe;
- a missing command after a non-trailing separator;
- a redirection without a following word;
- an unterminated quote or trailing escape;
- an otherwise empty command between operators.

Syntax diagnostics must go to standard error, must not execute any part of the
invalid line, and must produce status 2. In the read/evaluate loop, a syntax
error must not terminate the shell.

## 3. Words and quoting

Unquoted ASCII whitespace (space, tab, carriage return, vertical tab, and form
feed) separates words. Newline separates command lists as described above. The
characters `|`, `;`, `&`, `<`, and `>` are operators when unquoted; `>>` is one
operator. All other non-NUL bytes belong to a word.

- Single quotes preserve every enclosed character literally until the next
  single quote.
- Double quotes preserve enclosed spaces and operators. Within double quotes,
  backslash removes the special meaning of the next character.
- Outside single quotes, backslash quotes the next character.
- Quoted and unquoted fragments with no separating whitespace form one word:
  `pre"two words"post` is one argument.
- Empty quotes produce an empty argument. They must not disappear.
- Quote characters and quoting backslashes are syntax and are not included in
  the resulting argument.

Variable expansion, command substitution, arithmetic expansion, pathname
globbing, tilde expansion, here-documents, comments, logical `&&`/`||`, and
parentheses are explicitly out of scope. Bytes such as `$`, backtick, `*`, `?`,
`[`, `]`, `~`, `#`, `(`, and `)` are ordinary word bytes and acquire no hidden
meaning. `&&` and `||` are doubled core operators and therefore syntax errors.
Do not use `/bin/sh` to parse or execute a line on `minish`'s behalf. A NUL byte
from batch stdin must be diagnosed as syntax status 2; it must not silently
truncate or split a command.

## 4. Simple commands and statuses

For an external command, use the environment's `PATH` search behavior. The
child must inherit the shell environment and intentional ambient descriptors.
Internal pipe, signal-notification, saved-redirection, and job-control
descriptors must be closed before `exec` or marked close-on-exec.

- A command that cannot be located through its explicit path or `PATH` search
  must be diagnosed and yield status 127. A located command that cannot be
  executed must be diagnosed and yield status 126; this includes an executable
  script whose named shebang interpreter does not exist. A successful
  standards-defined `execvp` text-file fallback is external program behavior,
  not parsing of the `minish` source line.
- Normal termination yields the child's exit status.
- Signal termination yields `128 + signal_number`.
- A foreground pipeline yields the status of its last command.
- A foreground list yields the status of the last foreground pipeline it ran.
- Successfully starting an asynchronous pipeline yields status zero for that
  list position; later completion must not retroactively change `$?` (which is
  not otherwise exposed in the core language).

The status remembered for operand-free `exit` changes only when a foreground
pipeline (including a parent-run builtin) completes or stops. A syntax error or
an asynchronous launch can change the current list result but does not replace
that remembered foreground status.

Natural end-of-file and the end of `-c` return the current list result, whereas
operand-free `exit` returns the remembered foreground result. Thus
`false ; true &` followed by natural end returns 0, but
`false ; true & exit` returns 1. A syntax-error line followed by end-of-file
returns 2; if another physical line subsequently executes `exit`, that builtin
still uses the preceding foreground result.

Diagnostics should name the failed command or operation and go to standard
error. Exact prose is not part of the contract unless a test explicitly says
otherwise.

## 5. Pipelines and redirections

All commands in a pipeline must be started before the shell waits for any of
them. For each adjacent pair, the left command's standard output feeds the
right command's standard input. The shell and its children must close pipe ends
they do not need, so readers can observe end-of-file and long pipelines cannot
stall solely because the shell retained a descriptor.

Redirections are processed from left to right for their command, after that
command's default pipeline endpoints have been selected:

- `< path` opens `path` for reading and replaces standard input;
- `> path` opens or creates `path`, truncates it, and replaces standard output;
- `>> path` opens or creates `path`, appends to it, and replaces standard
  output.

When job-control mode is unavailable (standard input is not a controlling
terminal), the first command of an asynchronous pipeline whose standard input
has no explicit `<` redirection must receive `/dev/null` as its standard input.
This rule does not depend on prompt visibility. Later pipeline commands still
receive normal pipe input. The policy prevents a background command from
consuming subsequent batch source text.

Use normal user file permissions subject to the process umask. A redirection
failure must prevent that command from executing and must yield a nonzero
status. Redirections belong only to their command; they must not permanently
alter the parent shell's descriptors, including when running a built-in.

## 6. Built-ins

Implement these built-ins:

- `cd [directory]`: change directory. With no operand, use `HOME`; reject more
  than one operand and diagnose a missing `HOME`.
- `pwd`: print the shell's current directory; reject operands.
- `exit [status]`: request shell termination. With no operand, use the most
  recent foreground status. Accept one `[+-]?[0-9]+` decimal integer of any
  length and use its value modulo 256; an invalid number or extra operand is an
  error and must not silently terminate the interactive shell.
- `jobs`: print known, unfinished jobs in stable increasing job-ID order.
- `fg [%job]`: continue the selected job if necessary, give it the foreground,
  and wait until it stops or finishes.
- `bg [%job]`: continue a stopped job without giving it the terminal. Naming a
  running job is an error.

For `fg` and `bg`, omitted job operands select the most recently created
eligible job. An explicit operand is a percent sign followed by a positive job
ID. Missing and malformed jobs are errors.

A parent-affecting built-in (`cd`, `exit`, `fg`, or `bg`) in a single foreground
command must run in the shell process. Every built-in in a pipeline or
asynchronous job must run in a child context, so its state changes cannot alter
the parent. Redirections still apply to foreground parent-run built-ins and
must be restored afterward.

`fg` and `bg` in child context must diagnose that job control is unavailable
and return nonzero; the child must not signal a job from its copied table.
Standalone foreground parent-run built-ins are shell operations, not separately
tracked jobs, and do not receive a process group or job ID.

For a consistent redirection path, standalone foreground `pwd` and `jobs` also
run in the parent. Both reject operands. If any redirection for a parent-run
builtin fails, the builtin body must not run, shell state must not change, and
all shell descriptors must be restored.

## 7. Jobs, process groups, and terminals

Each pipeline launched in children is one job and one process group. A job ID is
allocated only when an asynchronous launch succeeds or a foreground job stops;
IDs increase monotonically and are not reused. In job-control mode, foreground
jobs must temporarily own the controlling terminal. The shell must remain in
its own process group, must regain terminal ownership after a foreground job
stops or exits, and must survive terminal-generated stop/interrupt signals that
were intended for the foreground job.

Job-control mode depends on standard input being a controlling terminal; it
does not depend on where standard output is redirected. Prompt visibility is a
separate decision and still requires both terminal input and terminal output.

Track at least a monotonically increasing shell job ID, process-group ID,
original command text, and state (`Running` or `Stopped`) for each unfinished
job. `jobs` output must use one line per job in this form:

```text
[ID] Running COMMAND
[ID] Stopped COMMAND
```

`COMMAND` is the exact source slice for that pipeline after removing leading
and trailing ASCII whitespace and excluding the following `;` or `&`; quoting
and internal spacing are preserved.

A job is complete only when all members are done. It is `Running` while any
member is running, and `Stopped` when no member is running and at least one is
stopped. If a foreground job stops, its immediate shell status is
`128 + stop_signal`; if several members are stopped, use the rightmost stopped
pipeline member's signal. This stopped-member rule applies even when a later
pipeline member already exited. The retained job can subsequently be selected
by `fg` or `bg`.

Completed jobs must eventually be reaped even while the shell is waiting for
input; zombies must not accumulate. A completion notification is optional, but
if printed it must not corrupt redirected command output. The implementation
must handle multiple child state changes represented by one `SIGCHLD`
notification.

Optional launch, stop, or resume notices containing volatile process IDs may be
printed only in prompt-visible interactive mode. They must not appear when
stdout is redirected or in batch output; the stable `jobs` rows remain the
portable inspection interface.

When standard input is not a controlling terminal, job pipelines and `&` still
work, but terminal ownership transfers are skipped. Batch execution must not
depend on `/dev/tty` being available.

On `exit` or end-of-file, the shell must shut down unfinished owned jobs: send
`SIGHUP` to each process group, send `SIGCONT` to stopped groups, allow a bounded
grace period, then kill any survivors and reap every child before returning.
Shutdown must not wait indefinitely for a command that ignores `SIGHUP`.

## 8. Resource and robustness requirements

- Do not invoke subprocesses through shell command strings.
- Retry wait and descriptor operations where interruption is recoverable.
- Do not perform non-async-signal-safe work in a signal handler.
- Close temporary descriptors on every success and error path.
- Reap every child the shell creates, including partially launched pipelines.
- Bound owned allocations by the size of the input and report allocation
  failure rather than continuing with corrupt state.
- A failed command must not poison later commands in the read/evaluate loop.

The shell should run correctly under AddressSanitizer and UndefinedBehaviorSanitizer
for ordinary non-job-control tests and should terminate without leaks or hung
children after end-of-file.

## 9. Suggested milestones

1. Preserve the starter CLI and clean batch/interactive I/O behavior.
2. Lex words, quotes, escapes, and operators with owned-memory cleanup.
3. Parse lists, pipelines, commands, and redirections without executing them.
4. Execute simple external commands and parent-run built-ins.
5. Add redirections and concurrent multi-command pipelines.
6. Add asynchronous jobs, process groups, terminal handoff, and `jobs`/`fg`/`bg`.
7. Harden error paths, signal races, descriptor cleanup, and shutdown.

An optional feature is acceptable only if it does not change required behavior
for the grammar above and is accompanied by its own tests and documentation.
