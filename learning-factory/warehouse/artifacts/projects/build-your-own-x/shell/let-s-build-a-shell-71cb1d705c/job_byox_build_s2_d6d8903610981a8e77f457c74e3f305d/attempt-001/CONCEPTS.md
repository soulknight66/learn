# Concepts behind the challenge

## Parse first, execute second

A shell line should become an owned data structure before any process starts.
That creates a transaction boundary: malformed syntax launches nothing, and
execution never needs to reinterpret source text. A useful model is a pipeline
containing commands, each with an argv vector and optional input/output
redirection.

## File-descriptor topology

For a three-stage pipeline, two pipes provide four descriptors. Each child
duplicates only the endpoint it needs onto descriptor 0 or 1, then closes all
original pipe descriptors. The parent closes all endpoints after forking.
Keeping even one extra write end open can prevent a reader from ever seeing
EOF.

```text
producer stdout -> pipe A -> filter stdin
filter   stdout -> pipe B -> consumer stdin
```

Redirection overrides the corresponding pipeline endpoint. Opening files
before forking simplifies error rollback but requires careful ownership;
opening in each child localizes descriptors but reports failures after other
stages may already exist. Either design must be deliberate.

## Processes versus process groups

A PID names one process. A process-group ID names a job: every stage of one
pipeline shares it. Terminal-generated signals target the foreground process
group, which lets Ctrl-C interrupt the whole pipeline without killing the
shell. `setpgid` should be attempted in both parent and child to close a race
between `fork` and `exec`.

## The controlling terminal

`tcsetpgrp` changes which process group owns terminal input and terminal
signals. An interactive shell temporarily assigns a foreground job, waits,
then reclaims the terminal. The shell ignores signals that would suspend it
during this handoff; children reset those dispositions before exec.

## Reaping and state

Child state is event-driven. `waitpid` reports exit, signal death, stop, and
continuation. A job is complete only when all members are complete; its shell
status comes from the last pipeline member. A `SIGCHLD` handler should do
almost nothing (or nothing): ordinary code can drain `waitpid` with
`WNOHANG|WUNTRACED|WCONTINUED` at safe points.

## Built-ins and ownership

`cd` illustrates why some commands must execute in the shell: changing a
child's working directory cannot affect its parent. In a pipeline, however,
the same built-in belongs in a child because it is a stage. Redirection around
a parent built-in requires saving, replacing, and reliably restoring the
shell descriptors.

## Failure discipline

Every system call has an ownership consequence. After partial pipeline
creation, a robust implementation closes descriptors, terminates or waits for
children already created, restores terminal ownership, and preserves the
first useful error. Treating these as explicit cleanup states prevents the
most common hangs and zombies.
