# Design questions

Write down your answers before implementing each subsystem. Revisit them after
tests expose a case your model did not cover. This file intentionally contains
questions only; keep your design decisions in your own notes.

## Representation and ownership

1. What are the lexer, parser, and executor boundaries in your implementation?
2. Who owns each token's text, and when can the source input buffer be freed?
3. How will you represent an empty quoted word distinctly from no word at all?
4. Which structure owns argument vectors, redirection paths, and original job
   text?
5. Can every partially initialized structure be passed to one cleanup routine?
6. What size arithmetic must be checked before growing token and argument
   arrays?

## Grammar and diagnostics

1. How does the lexer decide whether `>`, `>>`, and a quoted `>` are operators?
2. At what point are adjacent quoted and unquoted word fragments joined?
3. How will the parser encode that pipelines bind more tightly than separators?
4. Which component reports a dangling pipe, missing redirection target, trailing
   escape, and unterminated quote?
5. How will you ensure a syntax error has no filesystem or process side effects?
6. What source location can you retain to make diagnostics useful without
   coupling parsing to terminal output?

## Execution and descriptors

1. For an N-stage pipeline, how many pipes and children are live at peak?
2. Immediately before each `exec`, what should every open descriptor refer to?
3. Which pipe ends must the parent close, including on the third of four failed
   forks?
4. How does your launch order behave when a producer writes more than pipe
   capacity before its consumer reads?
5. How will command redirections override default pipeline endpoints in the
   specified order?
6. How will a parent-run built-in save, apply, and restore descriptors if an
   intermediate operation fails?
7. Which process's result determines pipeline status, and where is that result
   stored if children finish in a different order?

## Built-ins and shell state

1. What property decides whether a built-in runs in parent or child context?
2. What should `cd /tmp | pwd` be allowed to change in the parent shell?
3. When does `exit` terminate only a pipeline child, and when does it terminate
   the shell loop?
4. What status does a no-argument `exit` use after a syntax error or background
   launch?
5. If a parent-run built-in's redirection fails, which state changes are still
   permitted?
6. How will built-in argument validation remain consistent across contexts?

## Jobs, signals, and terminals

1. Which process chooses a new job's process-group ID, and how do both sides of
   `fork` tolerate scheduling races while establishing it?
2. What per-process states are required to derive `Running`, `Stopped`, and
   complete for a whole pipeline?
3. How can a child change state between `fork` and insertion into the job table
   without being lost?
4. If five children exit before one `SIGCHLD` is observed, how will all five be
   reaped?
5. Which operations are safe in your signal handler, and how does normal control
   flow learn that reaping is needed?
6. Where are relevant signals blocked, unblocked, ignored, or reset to default?
7. How will the shell transfer terminal foreground ownership and guarantee that
   it is reclaimed on success, setup failure, stop, and interruption?
8. How does the same executor avoid terminal calls when running under captured
   batch input?
9. What does an omitted `fg` or `bg` operand select after newer jobs have
   completed?
10. When can a completed job record be removed without losing status needed by
    a foreground wait or notification?

## Failure handling

1. List every resource acquired while launching a pipeline. What releases each
   one on every early return?
2. How will a child report setup or `exec` failure without accidentally running
   the parent loop?
3. Which interrupted system calls are retried, and which cause the current
   command to fail?
4. If one pipeline stage cannot be started, what happens to stages already
   running and how are they reaped?
5. How do you preserve the original `errno` while attempting cleanup?
6. What prevents one failed command from leaving changed descriptors, signal
   masks, or terminal ownership for the next command?

## Evidence

1. Which lexer and parser properties can be tested without starting a process?
2. Which test produces more than a pipe buffer and fails if stages are launched
   sequentially?
3. How will a test distinguish output, diagnostics, and prompt text?
4. Which cases require a pseudo-terminal rather than stdin/stdout pipes?
5. How will tests avoid indefinite hangs when descriptor ownership is wrong?
6. What observable evidence shows that completed background children are not
   zombies?
7. Which sanitizer configurations are compatible with your fork/exec tests, and
   what remains untested by them?
8. What benchmark variation would indicate a regression rather than ordinary
   scheduler noise?
