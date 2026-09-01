# Alternative designs (sealed)

These are instructor-facing comparison points, not required learner answers.

## `posix_spawn` instead of `fork` plus `exec`

`posix_spawnp` can describe descriptor actions and process-group attributes
without running a large amount of code after `fork`. That is attractive in a
multithreaded production program and on platforms where `fork` is expensive.
For this challenge, explicit `fork`, `setpgid`, `dup2`, and `execvp` make the
descriptor and process-group invariants observable. A spawn-based alternative
would need careful portability checks for foreground group creation and error
reporting.

## AST arena instead of individually owned nodes

An arena makes parse-error cleanup and per-command-loop teardown almost
constant-time: discard the entire arena after execution. Individually allocated
strings and vectors make ownership more explicit to a C learner and allow jobs
to retain only the command text they need. Both designs are sound if the
lifetime boundary is documented and tested under allocation failures.

## Other signal integration instead of the implemented self-pipe

The reference has a minimal `SIGCHLD` handler that writes to a nonblocking
self-pipe; ordinary flow polls that pipe with input and drains all available
`waitpid` state. A blocked-signal plus `sigsuspend` design can avoid a pipe but
fits awkwardly beside input polling. Linux `signalfd` makes signals ordinary
pollable events but narrows portability. Polling only at prompt boundaries is
smaller, but it can leave zombies while an idle shell waits for input. Any
choice still needs a durable wait loop because notifications may coalesce.

## Per-process state instead of aggregate job state

A job can store a record for every child, including stopped/continued/exited
state, then derive the aggregate. A smaller implementation can track remaining
children and a coarse stopped flag. The detailed representation handles mixed
pipeline states and diagnostics more faithfully; the aggregate representation
is easier to teach but must not declare a job complete until every member is
reaped.

## Table-driven parser instead of recursive descent

The grammar is intentionally small enough for hand-written recursive descent.
A generated LR parser would become useful after adding compound commands,
subshells, functions, here-documents, and operator precedence. That alternative
requires a generator dependency and shifts the lesson away from explicit
token/ownership mechanics.
