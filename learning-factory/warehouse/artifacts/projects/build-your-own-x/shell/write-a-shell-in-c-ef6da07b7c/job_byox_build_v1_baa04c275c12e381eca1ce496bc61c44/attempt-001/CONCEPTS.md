# Concepts primer

This is a map of the ideas behind the challenge, not an implementation recipe.

## A shell is two kinds of program at once

Most commands run in a child created by `fork`, then replaced by another program using an `exec` function. Some commands cannot work that way: a child changing directory cannot change its parent's directory, and a child deciding to exit cannot terminate its parent. That is why `cd` and `exit` are parent built-ins.

After `fork`, parent and child have separate address spaces but initially refer to the same open-file descriptions. Descriptor ownership, not just data flow, matters. One forgotten write end can keep a pipeline reader from ever seeing EOF.

## Pipes are concurrent graphs

A pipe has a read end and a write end. `dup2` can make those ends become a child's standard input or output. A multi-stage pipeline must be launched as a graph before the parent waits; otherwise a producer can fill a pipe buffer while its not-yet-created consumer cannot drain it.

Draw a descriptor table for a three-command pipeline. For each process, cross out every endpoint after duplication. If any process retains an unnecessary writer, revisit the design.

## Exit status and PID are different dimensions

`waitpid` reports both *which child changed state* and an encoded status. Use the `WIF*` and `W*STATUS` macros; the integer is not directly an exit code. Pipelines add another distinction: all children must be reaped, while the externally visible status comes from the last command.

## Process groups are the unit of terminal job control

A PID names one process. A process-group ID names a set of related processes, such as all stages of a pipeline. Terminal-generated signals go to the terminal's foreground process group. This is why merely forwarding `SIGINT` to one remembered PID is not a complete interactive design.

Both parent and child should attempt `setpgid` around `fork` to close a scheduling race. In interactive mode, `tcsetpgrp` transfers the terminal between the shell's group and the foreground job. Signal dispositions inherited across `fork` must be reset in the child before `exec`.

## Parsing is state, not string splitting

Whitespace has different meaning in normal, single-quoted, and double-quoted contexts. Operators are special only outside quotes. Empty quotes matter even though they contribute no bytes. A useful parser separates lexing from grammar validation so it can reject a whole malformed line before execution begins.

For every state, decide what happens on ordinary bytes, whitespace, backslash, quotes, operators, and end-of-input. Then test transitions at boundaries: an operator adjacent to a word, an empty quoted word, and an escape immediately before end-of-input.

## Ownership is part of the design

Write down who frees each token, argument vector, pipeline, job label, and PID array. Also write down who closes each descriptor after every failure point. Error paths are where shells most often leak resources or leave children behind.
