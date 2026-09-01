# Concepts for building `minish`

A shell looks like a loop that reads text and starts programs, but most of its
difficulty lies at boundaries: text becomes structured data, descriptors become
shared kernel state, and several processes change state independently. This
guide supplies a mental model without prescribing an implementation.

## The shell is both parser and process supervisor

Treat a command line in stages:

```text
bytes -> tokens -> command structure -> execution plan -> child state changes
```

Keeping those stages separate makes failures attributable. A lexer can be
tested without forking. A parser can reject malformed structure before a file
is opened. An executor can consume a validated tree rather than rediscovering
operator precedence while children are already running.

The starter interfaces reflect these boundaries. You may change internal data
representations, but preserve clear ownership: identify who allocates token
text, who owns parsed argument arrays, and which cleanup routine is valid after
each partial failure.

## Lexing is not splitting on spaces

Spaces delimit arguments only when they are unquoted. Operators may touch words,
quoted and unquoted fragments may form one word, and empty quotes are real data.
It is useful to distinguish:

- whether a word has started;
- which quoting mode is active;
- whether the next character is escaped;
- the bytes accumulated for the current word.

That distinction explains why an empty quoted argument exists even though its
text length is zero. It also helps the lexer report an unfinished quote at the
point where input ends.

## Parsing records relationships

Tokens alone do not say which commands share a pipeline or which redirection
belongs to which command. A parser records those relationships in an abstract
syntax tree or equivalent structures. Precedence gives the structure: pipes
group commands more tightly than list separators.

Parsing should be free of process creation and filesystem side effects. If the
line is malformed, rejecting the whole line before execution gives a stable and
testable error model.

## `fork`, `exec`, and two flows of control

After `fork`, parent and child resume from the same point with separate virtual
address spaces. Memory writes in one do not update the other. Both initially
refer to the same underlying open file descriptions, however, which is why
descriptor ownership matters immediately.

An `exec` call replaces the child program; it does not create a process. On
success it does not return. On failure, the child is still running the shell's
code and must take a child-only error path. Buffered C library output copied by
`fork` is another reason to be deliberate about how a failed child exits.

The parent uses `waitpid` to collect state and release the child's kernel
record. A child can exit, stop, continue, or be terminated by a signal; the wait
status must be decoded rather than treated as a plain exit integer.

## File descriptors are references, not byte buffers

A descriptor is a small process-local number referring to an open file
description in the kernel. After `fork`, closing a descriptor in one process
does not close copies in other processes. End-of-file on a pipe appears only
when every descriptor referring to that pipe's write end is closed.

`dup2` changes which open description a descriptor number refers to. A useful
way to reason about setup is as a table for each process: what should descriptor
0, descriptor 1, descriptor 2, and every temporary pipe descriptor refer to
immediately before `exec`? Then separately list which descriptors the parent
retains.

Redirection order is observable because opening and duplicating descriptors are
state changes. Parent-run built-ins add another constraint: their redirections
must be temporary from the shell's point of view.

## A pipeline is concurrent

A pipe has finite capacity. A producer may block until a consumer reads, so a
pipeline cannot generally be executed one stage at a time. Think of pipeline
launch as a transaction with partial-failure cleanup:

1. establish the required communication channels;
2. start every stage and assign the job's process group;
3. close the supervisor's unused descriptors;
4. observe the job until the required state is reached.

The ordering details contain races, especially around process groups. Correct
code should tolerate either process reaching a setup point first rather than
depending on favorable scheduling.

## Built-ins have execution context

Some commands exist specifically to change the shell: changing directory or
requesting exit in a throwaway child would have no lasting effect. Conversely,
pipeline stages and background commands need process isolation. The same
built-in can therefore need parent context in one syntax position and child
context in another.

This is a semantic decision made from the parsed command's context, not merely
from its name. Temporary redirection, status propagation, and cleanup still
apply when no `exec` occurs.

## Jobs and process groups

A process ID names one process. A process-group ID names a set of related
processes and is the unit a terminal uses for job-control signals. Treating one
pipeline as one process group lets Ctrl-C, Ctrl-Z, `fg`, and `bg` act on every
stage rather than an arbitrary child.

In an interactive session, the terminal has one foreground process group. The
shell gives that role to a foreground job and takes it back after the job exits
or stops. The shell's own signal dispositions and the child's inherited signal
dispositions may need to differ. In batch mode there may be no controlling
terminal at all, so terminal operations must be conditional.

## `SIGCHLD` is a notification, not a ledger

Ordinary signals are not a queue containing one entry per child. Several child
events may correspond to a single observed `SIGCHLD`, and another event may
arrive while the shell is processing the first. The durable truth comes from
nonblocking `waitpid` results and the shell's job table.

Signal handlers have a very small safe API. Allocation, formatted I/O, and most
job-table operations do not belong there. Designs commonly arrange for the main
control flow to notice that work is pending, then reap and update normal data
structures at a point protected against races.

Job state is aggregated: a multi-process job is finished only when every member
is finished, remains running while any member runs, and is stopped when no
member runs and at least one is stopped. Record per-process information
sufficient to derive that state.

## Errors are part of the interface

There are several independent error domains:

- lexical or syntactic errors before execution;
- setup errors such as `pipe`, `fork`, `open`, or `dup2` failure;
- `exec` failure in a child;
- ordinary nonzero program exits;
- signal termination or stopping;
- invalid built-in arguments.

Preserve the distinction long enough to choose a diagnostic, clean up acquired
resources, and compute the required shell status. Saving `errno` before cleanup
can prevent a later close or wait from obscuring the original cause.

## Testing process behavior

Good tests observe contracts, not timing guesses. Feed batch input through
pipes, capture stdout and stderr separately, impose a timeout, and inspect exit
status. Use temporary directories for redirection tests. Generate enough data
to exceed a typical pipe buffer when testing concurrency.

Interactive job control needs a pseudo-terminal rather than ordinary captured
pipes. A pseudo-terminal test can verify prompt visibility, foreground terminal
ownership, Ctrl-C/Ctrl-Z behavior, and prompt recovery. Keep waits bounded and
wait for observable markers instead of sleeping for an assumed scheduling
interval.

Sanitizers, descriptor snapshots, and syscall tracing answer different
questions. Use them as evidence generators, then reduce a failure to the
smallest input that still demonstrates the broken invariant.
