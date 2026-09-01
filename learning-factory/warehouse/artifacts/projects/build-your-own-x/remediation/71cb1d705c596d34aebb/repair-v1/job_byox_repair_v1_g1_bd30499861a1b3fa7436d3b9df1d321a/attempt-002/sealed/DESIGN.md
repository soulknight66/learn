# Reference design answers

This document describes the sealed `minish` implementation. It is an answer key
to `DESIGN_QUESTIONS.md`, not learner-facing guidance.

## Representation and ownership

The implementation has five explicit phases: byte-oriented line acquisition,
lexing into `TokenVec`, parsing into `Program`, execution of each `Pipeline`, and
job-state collection. The complete physical line is lexed and parsed before any
pipeline on it runs, so a later syntax error cannot follow earlier side effects.

Each word token owns an unquoted, unescaped string. A word builder has a
separate “started” bit, which preserves `""` and `''` as real empty arguments.
The parsed program duplicates arguments and redirection paths, while the token
vector remains independently destructible. Commands own NULL-terminated argv
arrays and redirections; pipelines own commands plus an exact trimmed source
slice; the program owns pipelines. Every cleanup routine accepts a partially
initialized zeroed object.

Dynamic arrays double from small initial capacities. Central checked helpers
reject capacity doubling, element-count multiplication, and terminator addition
that would overflow `size_t`. Allocation failure emits one diagnostic and exits
status 2 rather than allowing a partially valid shell to continue.

## Lexing and parsing

The lexer is a small state machine embedded in `lex_line`. Outside quotes,
ASCII whitespace terminates a word and `| ; & < >` begin operators. Single
quotes copy literally. Double quotes copy until the closing quote and let a
backslash quote the next byte. Backslash has the same next-byte rule outside
single quotes. Adjacent fragments share one builder.

The parser implements this precedence directly:

```text
program  -> pipeline ((';' | '&') pipeline)* trailing-separator?
pipeline -> command ('|' command)*
command  -> (WORD | redirection)+, with at least one WORD
```

It rejects a missing command, dangling pipe, missing redirection target, doubled
separator, trailing escape, and unterminated quote. A pipeline's display string
is sliced from the original input, trims only its outer whitespace, and excludes
the separator. A NUL detected by the input reader invalidates the complete
physical line before lexing; `-c` cannot contain NUL because argv strings cannot.

## Descriptor and process plan

The reference creates all `N-1` pipes before forking, then forks all `N`
commands before waiting. In child `i`, pipe `i-1` becomes stdin and pipe `i`
becomes stdout where those edges exist. Every original pipe endpoint and the
self-pipe descriptors are closed before a builtin or `execvp`. Command
redirections are then applied in source order, so they intentionally override a
pipeline endpoint.

For a new interactive foreground job, each child first joins the process group,
restores child signal dispositions, closes unrelated descriptors, and then
waits on a close-on-exec launch barrier. The parent establishes every child and
the common PGID, transfers the terminal, and writes one explicit `GO` token per
child. End-of-file before a token means abort, so a partial-fork path cannot run
a command body accidentally.

The parent closes all pipe endpoints after the fork loop. If a pipe, fork,
barrier release, or terminal transfer fails, it closes owned descriptors,
kills both the partially established group and recorded individual children,
reaps them, and returns failure. Completed pipeline status comes from the saved
wait status of its last member, independent of reap order. If the aggregate job
stops, status instead comes from the rightmost stopped member. A command absent
from its explicit path or `PATH` search maps to 127; a located command that
cannot execute, including a missing shebang interpreter, maps to 126.
Recoverable `EINTR` results from pipe, open, duplication, descriptor-flag,
metadata, exec, and terminal attribute operations are retried in narrow
wrappers; close is not blindly retried because its cross-platform state after
interruption is not uniform.

When job-control mode is absent, stage zero of an asynchronous pipeline opens
`/dev/null` for stdin unless the command has an explicit input redirection.
That redirection is applied afterward and therefore wins.

## Builtin context and status

Every standalone foreground builtin runs in the parent. `cd`, `exit`, `fg`, and
`bg` therefore affect live shell state; `pwd` and `jobs` use the same path for
uniform temporary redirection. The parent duplicates stdin/stdout, applies all
redirections, runs the builtin only after they succeed, flushes output, and
restores both descriptors on every return. In a pipeline or background job,
builtins run after fork. Child `fg` and `bg` reject the context rather than
signalling through a copied job table.

The shell stores both the current list result and the most recent foreground
result. Natural end returns the former. Operand-free `exit` uses the latter, so
an asynchronous launch or syntax error does not erase the previous foreground
result. Explicit exit integers are reduced digit by digit modulo 256, avoiding
signed overflow for arbitrarily long operands.

## Jobs and signals

One child-launched pipeline becomes one process group. Both child and parent
call `setpgid`, tolerating the expected scheduling race. `Job` stores a monotonic
ID, PGID, exact command text, and one state/wait-status record per direct child.
Aggregate state is derived rather than asserted: any running member means
`Running`; no running member plus a stopped member means `Stopped`; otherwise
all members are `Done`.

The `SIGCHLD` handler saves `errno` and writes one byte to a nonblocking,
close-on-exec self-pipe. It does not allocate, print, mutate the job table, or
reap. Main control flow drains the pipe and loops over nonblocking `waitpid`
until no state remains. Signal coalescing and a full self-pipe are harmless
because the pipe is only a wakeup; `waitpid` is the durable ledger.

No fork-to-table lost-event window exists in this design: the handler never
reaps, and main flow cannot call the reaper between `fork` and inserting a
successful background job. An already-exited child remains waitable; the next
refresh finds it by PID after insertion.

Completed background jobs are removed silently. IDs are assigned only when a
background job is inserted or a foreground job stops. `fg` can select any
unfinished job; `bg` selects only a stopped job. Omitted operands search the
table from newest to oldest.

## Terminal ownership and shutdown

Prompt visibility for the input loop is `isatty(stdin) && isatty(stdout)`;
`-c` forces it off. Job-control mode instead requires stdin to be a controlling
terminal, verified with `tcgetpgrp`. The
shell duplicates that terminal descriptor above stderr and marks it
close-on-exec, so temporary redirection of fd 0 by a parent builtin cannot break
`fg`. Foreground execution gives the terminal to the job PGID, waits for done or
aggregate stopped state, gives it back to the shell PGID, and restores shell
terminal modes. A new foreground group cannot pass its launch barrier until
the transfer succeeds, preventing a fast reader from being stopped by
`SIGTTIN`. Children reset terminal-related signals to default; the shell
ignores them while supervising.

At EOF or `exit`, unfinished groups receive `SIGHUP` and `SIGCONT`. Main flow
polls and reaps for 200 ms, sends `SIGKILL` to surviving groups and recorded
direct PIDs, then waits until no direct child remains. This deterministic policy
prevents a background child from retaining captured output indefinitely.

## Deliberate limits

There is no expansion language, compound syntax, stderr redirection, here-doc,
per-job saved terminal mode, persistent history, or completion notification.
The implementation uses one C file to keep the answer auditable and is not a
compatibility shell or a sandbox.
