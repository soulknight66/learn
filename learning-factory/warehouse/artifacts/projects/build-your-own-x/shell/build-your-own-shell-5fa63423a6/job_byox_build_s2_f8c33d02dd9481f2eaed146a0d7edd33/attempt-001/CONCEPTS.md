# Concepts to master

## A shell has two kinds of state

Lexical and parse state is ordinary in-process data: token boundaries, ownership, and grammar position. Execution state crosses a kernel boundary: descriptors, PIDs, process groups, signal dispositions, and terminal ownership. Keeping those halves behind a narrow AST-like structure makes failures easier to reason about.

## Pipes are inherited references

A pipe reaches EOF only when every descriptor referring to its write end is closed. After `fork`, those references exist in more processes than the source code's original variables suggest. The important accounting question is not “which descriptor did I use?” but “which process still owns a reference?”

## Process groups represent jobs

A PID identifies one process; a process-group ID identifies the cooperating processes of a pipeline. Terminals deliver interactive signals to a foreground process group. A shell therefore must coordinate process-group creation, terminal ownership, waiting, and restoration rather than merely fork and wait one child at a time.

## Built-ins expose the process model

An external command cannot change its parent's current directory. That is why `cd` must execute in the shell process. The same observation explains why an `exit` child cannot terminate its parent. Pipelines complicate the policy because each stage normally belongs in a child.

## Parsing creates a trust boundary

Execution should consume typed structure, not rescan input text. A validated pipeline distinguishes arguments from operators and redirections. This prevents accidental reinterpretation and makes ownership, diagnostics, and test cases deterministic.
