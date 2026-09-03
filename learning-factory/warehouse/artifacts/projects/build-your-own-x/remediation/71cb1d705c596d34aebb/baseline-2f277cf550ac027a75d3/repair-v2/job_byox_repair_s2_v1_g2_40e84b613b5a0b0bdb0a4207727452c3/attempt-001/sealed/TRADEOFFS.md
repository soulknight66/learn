# Reference tradeoffs

## One translation unit

The reference keeps parsing, execution, and job tracking in one C file. That
makes control-flow and descriptor review straightforward for an instructor,
but it is less maintainable than separate lexer, parser, process, and job
modules. The starter explicitly permits either organization.

## Pipes created up front

Creating all pipes before forking makes child setup uniform and makes syntax
execution atomic with respect to pipe allocation. It also consumes twice
`n-1` descriptors at once. A rolling-pipe algorithm lowers peak descriptor use
but complicates rollback and per-child closure proofs.

## Synchronous safe-point reaping

The shell polls `waitpid` before prompts and in `jobs` rather than mutating job
structures in a signal handler. This avoids async-signal-safety hazards. It
also means completion notifications can wait while the shell is blocked in
`getline`; a production event loop could use a self-pipe or `signalfd` on
platforms that provide it.

## Fatal allocation failure

Allocation helpers terminate on exhaustion. This keeps exercise cleanup paths
focused on OS resources, but a long-lived production shell should propagate
allocation failure, restore terminal state, and release jobs predictably.

## Deliberately small language

No expansion or compound syntax means the parser can validate the entire line
without an AST. This is a teaching boundary, not a claim that a token vector is
sufficient for a real shell language.

## Background lifecycle on shell exit

The reference frees its bookkeeping but does not send `SIGHUP` or wait for
running background jobs at normal EOF. This avoids imposing policy absent from
the public contract. A production shell needs a documented logout/disown
policy and careful terminal cleanup.
