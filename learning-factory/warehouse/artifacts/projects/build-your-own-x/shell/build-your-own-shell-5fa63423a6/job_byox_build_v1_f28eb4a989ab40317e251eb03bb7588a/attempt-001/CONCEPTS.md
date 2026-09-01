# Concepts for a Small Unix Shell

Use this as a map when a milestone exposes an unfamiliar behavior. It intentionally describes
relationships and questions to investigate, not the control flow or code needed to implement them.

## The shell is a state machine around OS primitives

A useful high-level model is:

```text
bytes -> tokens -> parsed pipeline -> launched job -> observed state -> released resources
```

Each arrow is a contract boundary. Tokenization should not open files. Parsing should not launch
processes. Launching should not discard the representation that job reporting still needs. State
observation should not free a job while another event can still refer to it.

The shell itself is long-lived, so small leaks and accidental state changes accumulate. Error paths
deserve the same ownership design as successful paths.

## Lexing and parsing are different jobs

Lexing decides where words and operators begin and end. Parsing decides whether their order is legal
and constructs commands, redirections, and a pipeline. Keeping those stages distinct makes several
important cases testable without creating a child process:

- an operator adjacent to a word;
- a quoted operator that is literal text;
- multiple fragments that form one argument;
- an empty quoted argument;
- a redirection filename that is missing;
- a pipeline with an empty member.

A parsed representation should retain semantic content, not punctuation that has already done its job.
It also needs a clear lifetime: either it owns its strings or it borrows from an input buffer that is
guaranteed to outlive it.

## Process creation separates two timelines

A process-creation call produces a parent and a child that can run in either order. They initially see
copies of user-space state and references to the same open kernel resources. Changes to ordinary memory
after the split are not shared. That is why a directory-changing built-in must run in the shell process
when its effect should persist.

Program replacement then exchanges the child's program image for the requested executable. A
successful replacement does not return; a return path represents failure and must end the child
without accidentally resuming the shell loop.

Waiting is not simply “did it finish?” A wait status can describe normal exit, termination by a signal,
a stop, or a continuation. Decode the category before interpreting its associated value.

## File descriptors are inherited references

A file descriptor is a per-process integer referring to an open kernel file description. After process
creation, parent and child descriptor numbers may refer to the same underlying object. Descriptor
duplication changes which number refers to an object; it does not copy the file's bytes.

Pipes make descriptor ownership visible. A reader sees end-of-file only after every descriptor that
refers to the pipe's write end is closed. One forgotten copy in the shell or an unrelated child can
therefore turn a correct-looking pipeline into a hang.

For every descriptor, ask:

1. Which command needs it as standard input or output?
2. Which processes inherited it but do not use it?
3. At what point can the shell close its copy?
4. What cleanup happens if a later pipe, open, or process creation fails?

The project permits one redirection per standard stream on each command. Detecting a duplicate while
parsing avoids file side effects from a line the shell will reject.

## A pipeline must make progress concurrently

Pipes have finite capacity. If the shell waits for a producer before starting its consumer, enough
output can fill the pipe and block the writer forever. Launching the complete pipeline
before waiting allows producers and consumers to make progress together.

The result of a pipeline and the lifetime of a pipeline are separate questions: its reported status
comes from the last command, but the foreground job is not finished until all of its members have been
observed.

## Processes, process groups, sessions, and terminals

These concepts form a hierarchy:

```text
session
├── controlling terminal (at most one)
├── shell process group
│   └── shell
└── job process group
    ├── pipeline member A
    └── pipeline member B
```

A process group lets the terminal and the shell address an entire pipeline. The terminal tracks one
foreground process group. Terminal-generated keystrokes such as interrupt or stop are delivered to
that foreground group, not specifically to the first process in a pipeline.

Foreground ownership is independent of which process runs first. The shell gives the terminal to a
foreground job while the job runs and takes it back before reading again. Background groups that try
some terminal operations may be stopped by the terminal driver; that behavior is part of job control,
not necessarily an application bug.

## Signals are notifications, not queued work items

Signals can arrive between almost any two ordinary instructions. Traditional signals of the same type
may be coalesced, so one notification does not imply one child event. A robust design treats a child
signal as “there may be state to collect” and drains all currently observable changes in normal control
flow.

Only a narrow set of operations is safe in a signal handler. Allocation, formatted I/O, and complex job
table mutation do not belong there. Coordination is also needed while the main flow creates a process
and publishes its job record; a very short-lived child can otherwise be reported before the record
exists.

System calls may return early after signal delivery. Decide which interrupted operations should be
retried and which should return control to the main loop.

## A job has aggregate state

A job represents a whole pipeline, while wait events describe individual processes. “Stopped” cannot
be inferred from a single member if another is still running, and “Done” requires accounting for all
members. Store enough per-process state to derive the job state after every event.

Job identifiers belong to the shell and are not process IDs. Keeping them distinct prevents accidental
signals to the wrong target and gives users a stable handle for `jobs`, `fg`, and `bg`.

There is also a reporting lifecycle. A completed job may need to remain in the table until its final
state has been shown, after which retaining it forever becomes a leak.

## Built-ins cross execution boundaries

Some built-ins change long-lived shell state (`cd`, `exit`, `fg`, and `bg`). Others mainly produce
output (`pwd`, `jobs`). Pipelines and background execution introduce a question: does a built-in need
the parent shell's state, a child execution context with redirected descriptors, or a clear rejection?

There is no universal shortcut. Classify each built-in by the state it reads, the state it mutates, and
whether its output must flow through a pipeline. Then apply the behavior promised by the requirements.

## Testing terminal behavior requires a terminal

A pipe provides bytes but no controlling-terminal semantics. Tests for prompting, terminal ownership,
and terminal-generated signals need a pseudo-terminal. Such tests should:

- wait for observable output or state, not a fixed sleep;
- set a deadline so failures cannot hang the suite;
- send control characters through the terminal when testing terminal behavior;
- capture both the transcript and the child exit status;
- clean up the whole test process group on failure.

Keep most tests below this level. Lexer, parser, job-state, and descriptor-planning logic can be tested
deterministically without a pseudo-terminal.

## Useful manual references

On a POSIX-like host, the manual pages for process creation, program execution, waiting, descriptor
duplication, pipes, process groups, terminal foreground ownership, and signal masks define the precise
contracts. Read the return values, error cases, and notes—not only the synopsis. Your platform's C and
POSIX documentation is authoritative for the platform you are running on.
