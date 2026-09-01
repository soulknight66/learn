# Reference tradeoffs

## One translation unit

Keeping the reference in one C file makes ownership and control flow easy to
audit in a learning artifact and permits a single strict compile command. It is
not the maintainable production shape. A larger implementation should separate
lexer/parser, immutable execution plans, OS operations, job storage, builtins,
and the event loop behind narrow interfaces with fault injection.

## Precreate every pipe

The reference opens all pipeline channels before any fork. This makes child
descriptor maps regular and makes partial cleanup explicit, at the cost of
`O(N)` live descriptors in the parent. A rolling launcher can retain only the
previous read end while still forking every stage before waiting, which scales
better near `RLIMIT_NOFILE` but has more distinct cleanup states.

## `fork` plus `execvp`

These calls expose the process and descriptor mechanics the challenge teaches.
`posix_spawnp` reduces unsafe post-fork work and may perform better on some
platforms, but foreground process-group attributes and portable error reporting
would need a separate design. The standards-defined `execvp` text-file fallback
is treated as external program behavior; input source is never passed to a
second shell for parsing.

## Self-pipe wakeups

The handler writes a byte and ordinary flow owns all state transitions. This is
portable across the target POSIX-like host and integrates with `poll`. Linux
`signalfd` could remove the handler, while a pure blocked-signal/`sigsuspend`
loop could remove the pipe. Both alternatives complicate either portability or
integration with line input.

## Poll one input byte at a time

Reading a byte at a time avoids stdio read-ahead that could consume data meant
for a foreground command, and it lets `SIGCHLD` wake an idle shell. It is simple
but syscall-heavy. A production event loop would use a buffered reader whose
ownership can be transferred or whose unread bytes are explicitly retained.

## Parent-run builtins share one path

Running even observational `pwd` and `jobs` in the parent gives all standalone
builtins the same save/apply/flush/restore descriptor transaction. Dispatching
non-stateful builtins through a child could isolate failures but would require a
separate way to expose the current job table accurately.

## Silent completion and eager removal

Completed background jobs are reaped and removed without a notification. This
keeps batch output deterministic and satisfies the public `jobs` form. A richer
interactive shell would retain completion records until a notification is
printed at a safe prompt boundary.

## Bounded destructive shutdown

HUP/CONT followed by a short grace period and KILL makes test and pipe cleanup
deterministic. An interactive general-purpose shell might instead warn, refuse
exit with stopped jobs, disown selected jobs, or preserve them across logout.
Those policies require additional syntax and user expectations.

## Exact language rather than POSIX compatibility

Unsupported expansion characters are ordinary word bytes and doubled
operators are syntax errors. This is predictable for a challenge but differs
from established shells. Incrementally adding features without a new grammar
and compatibility suite would be riskier than keeping the boundary explicit.
