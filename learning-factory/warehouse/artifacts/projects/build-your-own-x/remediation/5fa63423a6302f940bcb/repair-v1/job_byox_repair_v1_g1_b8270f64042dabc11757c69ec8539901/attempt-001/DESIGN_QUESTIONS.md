# Design Checkpoints

Answer these in your own notes as you finish each milestone. They are deliberately questions rather
than hints. Strong answers name an invariant, an observable test, and the cleanup behavior on failure.

## Milestone 0 — Loop and interfaces

1. How does the program distinguish `-c`, redirected standard input, and an interactive terminal?
2. Which component owns an input line, and when may that storage be reused or freed?
3. What status is retained after a parse error, a built-in, and an external command?
4. How will a test prove that end-of-file exits rather than spinning?
5. Which prompt behavior is observable, and how will non-interactive tests avoid prompt noise?

Do not continue until blank input, end-of-file, invalid arguments, and repeated input lines all have
bounded tests.

## Milestone 1 — Lexer and parser

1. Can a token refer safely into the input buffer, or should it own a decoded string? What lifetime
   follows from that choice?
2. At what stage are quote characters and backslashes removed?
3. How does the representation preserve an empty argument while distinguishing it from no argument?
4. How are operators recognized when no spaces surround them?
5. How does the parser detect a second redirection for the same stream before either file is opened?
6. How does the parser discard a partially built pipeline after an error?
7. Can the complete line be validated before anything with an external side effect happens?

Do not continue until malformed quotes, missing pipeline members, missing redirection targets, empty
arguments, and adjacent operators have focused tests.

## Milestone 2 — One command and built-ins

1. Which built-ins must execute in the long-lived shell process, and which can use a child context?
2. What state must remain unchanged when `cd` fails?
3. What distinguishes “program not found” from “program was found but could not execute,” and does your
   user-facing contract require distinct statuses?
4. After process creation, which code paths belong exclusively to the child and which to the parent?
5. What prevents a failed program replacement from returning to the interactive loop in the child?
6. How are normal exit and signal termination converted into shell status?
7. Which failure paths still require the parent to collect a child?

Do not continue until command lookup failure, child-side setup failure, built-in argument errors, and a
successful command followed by another command all have tests.

## Milestone 3 — Redirections and pipelines

1. Draw every open descriptor in the shell and in each child of a three-command pipeline. Who closes
   each copy, including on partial launch failure?
2. Why could waiting immediately after launching the first command deadlock?
3. If a command has both a pipeline endpoint and an explicit redirection for the same descriptor, which
   wins under the contract?
4. How does a duplicate output redirection fail without creating or truncating either named file?
5. How are the shell's own descriptors restored after a parent-executed built-in?
6. Which process reports an open failure, and how does that failure affect the pipeline's final status?
7. How does the parent retain the last command's identity while still collecting every member?

Do not continue until a large-data pipeline, early reader exit, redirection failure, append behavior,
and descriptor-leak-sensitive repetition all have bounded tests.

## Milestone 4 — Background jobs

1. What is the identity of a job, and how is it distinct from every process ID in its pipeline?
2. Which per-process facts are required to derive `Running`, `Stopped`, and `Done` for the whole job?
3. Can a child exit before the parent publishes the job? What invariant closes that race?
4. How are multiple child changes collected if notifications are coalesced?
5. When may a completed job record be removed without losing its one required report?
6. What does the main loop do when background state changes while it is waiting for input?
7. How will tests detect zombies without relying on timing alone?

Do not continue until rapid exits, concurrent background pipelines, repeated `jobs`, and completion
while the shell remains usable have tests.

## Milestone 5 — Interactive job control

1. Which process creates a new process group, and what happens if parent and child reach that operation
   in either order?
2. At every call that changes foreground terminal ownership, which group owns the terminal before and
   after it?
3. Which signal dispositions should differ between the interactive shell and a newly launched command?
4. How does the shell regain the terminal after normal exit, signal termination, stop, and setup
   failure?
5. What event makes a whole pipeline stopped? What event makes it runnable again?
6. What must `fg` change before waiting? What must `bg` deliberately not change?
7. What happens if the selected job exits between lookup and the requested operation?
8. Which tests require a pseudo-terminal, and what cleanup prevents a failed test from leaving stopped
   processes behind?

Do not continue until interrupting, stopping, background-resuming, and foreground-resuming a real
pipeline all work under a pseudo-terminal deadline.

## Milestone 6 — Hardening

1. List every allocated object and descriptor owner across a successful command and three representative
   failures. Is any ownership ambiguous?
2. Which operations can be interrupted, and what is the policy for each interruption?
3. Can diagnostics themselves alter the status or descriptor state being reported?
4. What happens when process or pipe creation fails halfway through a pipeline?
5. Which tests are deterministic enough for every commit, and which slower diagnostics belong in a
   separate run?
6. What unsupported syntax is diagnosed explicitly rather than misinterpreted?
7. What evidence supports each completion claim beyond “it worked once”?

The project is ready for review when a clean checkout can be built and tested with recorded commands,
and every known limitation is explicit.
