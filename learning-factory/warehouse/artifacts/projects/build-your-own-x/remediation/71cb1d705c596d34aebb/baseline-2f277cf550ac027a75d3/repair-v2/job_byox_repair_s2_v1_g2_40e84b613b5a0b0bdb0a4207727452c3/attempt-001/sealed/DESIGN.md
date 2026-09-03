# Reference design answers

This document is sealed because it answers the learner-facing design prompts
and describes the reference implementation.

## Representation and ownership

Lexing produces an owned vector of typed tokens. Word tokens own NUL-terminated
strings; operator tokens have no string. A separate `started` bit in the word
builder distinguishes no pending word from the valid empty words created by
`''` and `""`.

Parsing copies word data into this execution model:

```text
pipeline
  background flag
  original display string
  command[]
    argv[]
    optional input path
    optional output path + append flag
```

The lexer vector and parser model have independent ownership, so each can be
freed on any boundary. Parsing finishes and validates every token before
execution starts. This is how `touch marker |` is guaranteed not to create the
marker.

## Syntax decisions

The lexer recognizes operators without surrounding whitespace. Quotes and
backslashes are processed only while forming a word. The parser associates
redirections with the current command, rejects repeated directions, and
requires an argv word for every stage. A final `&` belongs to the whole
pipeline. Unsupported shell syntax is intentionally ordinary data rather than
half-implemented syntax.

## Pipeline construction

For `n` commands, the parent creates `n-1` pipes before the first fork. Stage
`i` duplicates the previous pipe's read end when `i > 0` and the next pipe's
write end when `i < n-1`. It then closes all original endpoints. Explicit file
redirection happens after pipe duplication, so it overrides that endpoint.
The parent closes every endpoint once all children have been forked.

Each first child creates a process group whose ID is its PID. Later children
join it. Both child and parent call `setpgid`: either side can win the scheduling
race while both request the same final state. A fork failure closes all pipes,
signals the partially created group, and waits for each known child.

## Built-in contexts

A single foreground built-in executes in the parent. Input and output files
are opened first; affected standard descriptors are duplicated, replaced,
then restored along a shared cleanup path. In a pipeline or background job,
the built-in executes after fork and cannot mutate parent state. `fg` therefore
reports that it is unavailable in child context.

`exit` reads the shell's previous status before the outer command loop updates
it. Invalid operands return 2 without setting the termination flag. `cd`
changes the parent directory only in parent context.

## Job-state model

Every job stores a PGID and one record per child PID. A child record is
Running, Stopped, or Done plus its most recent raw wait status.

- A job is Done only when every child is Done.
- It is Stopped when every non-Done child is Stopped and at least one remains.
- Otherwise it is Running.

The last pipeline member's raw wait status defines the shell result. The
nonblocking reaper matches returned PIDs against background job members,
updates state, reports completed jobs at a safe point, and removes them.
Foreground waiting targets the negative PGID so unrelated background children
cannot satisfy the wait.

## Terminal handoff

Interactive initialization places the shell in its own group, claims the
terminal, and ignores terminal stop/interrupt signals. A new foreground job is
given the terminal before waiting. A resumed job is also given the terminal
before `SIGCONT`; reversing those steps allows a reader to stop immediately
with `SIGTTIN`. Children restore default signal dispositions and unblock the
same terminal/job-control signals before a built-in or `execvp`. Every
foreground return path attempts to reclaim the terminal.

## Cleanup boundaries

Token, command, pipeline, job, and pipe arrays each have one freeing function.
Children use `_exit` after fork so they do not flush copied parent stdio state.
`waitpid` retries `EINTR`. Diagnostics are emitted with `dprintf` so child
failure paths do not depend on buffered stdio.
