# Engineering tradeoffs

The reference favors an inspectable teaching implementation over feature
breadth. These choices are intentional, but none should be mistaken for the
only valid way to build a shell.

## Growable owned reference representation

The sealed parser copies words into growable vectors and strings owned by the
pipeline. Compared with pointers borrowed from a mutable input line, this makes
the parsed lifetime independent and lets a job retain its source safely. It
also creates more allocation and more partial-construction failure paths. Every
growth needs checked size arithmetic, a temporary `realloc` result, and an
explicit destructor that tolerates partial initialization.

The learner scaffold instead uses fixed command/argument arrays and pointers
borrowed from its writable line. That makes limits and cleanup obvious but ties
execution to the line's lifetime. Silent clipping is wrong in either model:
fixed-limit overflow and dynamic allocation/size failure must be diagnosed
before launch.

## Lexer followed by parser

A separate lexer is more code than splitting on spaces, but quoting and
operator adjacency make whitespace splitting structurally wrong. It also gives
the parser a small vocabulary and makes empty quoted arguments representable.
The tradeoff is that source spans and richer diagnostics require tokens to
carry more metadata than this project strictly needs.

## Reject duplicate same-stream redirections

The command representation has one input slot and one output slot. Rejecting a
second redirect for either descriptor keeps execution and parent-builtin
rollback small and ensures a syntax error has no file side effects. This is a
deliberate language simplification: larger shells commonly accept `cmd > first
> second` and preserve the earlier open/truncation side effect. Compatibility
would require an ordered redirection list rather than silently keeping only the
last path.

## Fork/exec per pipeline stage

The classic process-per-stage design maps directly onto Unix pipes, process
groups, signals, and the `exec` family. It is portable across conventional POSIX systems
and exposes the mechanisms this exercise teaches. It is not the lowest-overhead
way to run trusted builtins or a large number of trivial commands. Avoiding a
fork with `posix_spawn`, or evaluating pure builtins in-process, shifts
complexity into file actions and state-isolation rules.

## Parent execution for standalone foreground builtins

Running a standalone `cd` in a child would be easy but useless because the
parent's working directory would not change. The reference therefore runs all
standalone foreground builtins in the parent and treats their descriptor
changes transactionally. This unifies behavior, at the cost of a careful
save/apply/flush/restore sequence. Builtins in pipelines or background jobs use
child semantics to preserve pipeline concurrency and shell isolation.

## Both sides call `setpgid`

Calling `setpgid` in both parent and child is redundant in a serial mental
model, not in a concurrent one. The child must not reach `exec` in the wrong
group, and the parent must know the group exists before terminal handoff. The
two calls converge on the same state and close scheduling windows, while
requiring careful classification of expected race errors versus real failures.

## Self-pipe wakeups with deferred `SIGCHLD` work

The handler sets a flag, writes a nonblocking self-pipe marker, and leaves
`waitpid` and table mutation to the main path. Markers and signals may coalesce,
which is harmless because the reap operation drains every available status.
Keeping `SIGCHLD` blocked outside an atomic `pselect` wait closes the gap between
checking child state and sleeping for input. This costs a pair of descriptors
and a small input buffer, but avoids both unsafe handler work and indefinitely
delayed idle reaping. A platform event primitive such as `signalfd` could reduce
machinery at the cost of POSIX portability.

## Process-group jobs rather than PID jobs

A pipeline is presented as one job and receives terminal signals as one process
group. Recording only the leader PID would make it impossible to derive correct
completion when a non-leader stage outlives the leader. Tracking every child
adds table state but gives `jobs`, `fg`, `bg`, and reaping a sound basis.

## Minimal grammar

Excluding expansion and compound operators keeps lexing, parsing, and execution
separable. It also means `byosh` is not a `/bin/sh` replacement: many familiar
commands are passed literally rather than expanded, and script compatibility is
not a goal. Adding `;`, `&&`, or `||` would require a list/conditional AST and
status-driven evaluator; adding `$` or globbing would require an expansion
model with precise quote provenance. Neither belongs as a local patch to an
external program's argument vector.

## `stdio` versus descriptor-level output

Descriptor-level operations are natural for redirection, while builtins are
convenient to write with `stdio`. Mixing them demands flushing at ownership
boundaries so buffered bytes follow the intended descriptor. An alternative is
to make all builtin output use `dprintf`/`write`; that reduces buffering
surprises but still requires short-write and interruption policy for robust
output.

## Portability boundary

The design uses POSIX process groups, terminal control, signals, pipes, and
manual `PATH` search with `execv`; it is intentionally Unix-specific. Even among Unix systems, details
such as `WCONTINUED`, terminal availability in containers, and libc behavior
deserve feature checks. A Windows port would need a different job/process and
console-control backend rather than conditional compilation around a few calls.
