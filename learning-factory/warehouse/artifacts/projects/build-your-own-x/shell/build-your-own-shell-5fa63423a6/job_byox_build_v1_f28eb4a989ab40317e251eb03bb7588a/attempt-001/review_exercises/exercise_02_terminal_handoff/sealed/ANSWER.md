# Sample review: process groups and terminal handoff

## Critical: process-group setup loses a race with child execution

Only the parent calls `setpgid`. A child can run through its setup and `exec`
before the parent call; the call may then fail with `EACCES`, leaving that child
outside the intended group. Because the error is discarded, the parent
continues with a fictional group membership. Each child should call
`setpgid(0, leader)` before exec, and the parent should call
`setpgid(child, leader)` as the complementary race-closing operation. Return
values need explicit handling of expected convergence races versus failure.

The child must also reset interactive signal dispositions inherited as ignored
from the shell and restore the pre-launch signal mask before executing user
code. Otherwise Ctrl-C or Ctrl-Z can be ignored by the foreground command.

## Critical: terminal handoff occurs before the group exists

For the first child, `tcsetpgrp` runs before the parent's `setpgid`. The target
process group may not exist, so handoff fails; its result is ignored. Conversely,
if the child happened to create some unexpected state, later members may still
not have joined. Establish all children and group membership, publish the job,
then perform one checked handoff for a foreground job.

## Critical: early child exit races job publication

`SIGCHLD` is not blocked across fork and `remember_job`. A short-lived stage can
exit and be reaped by other shell flow before it can be attributed. Block
`SIGCHLD` before the first fork, keep it blocked through complete table
publication and terminal setup, and restore the old mask afterward. Each child
restores that old mask.

## High: only the process-group leader is waited for

`waitpid(process_group, ...)` uses a positive PID, not a process-group selector.
It waits only for the leader and only for termination. Other stages can remain
alive or become zombies, and stopped foreground jobs are not detected. Job
control needs a loop over the group/membership using appropriate
`WUNTRACED`/`WCONTINUED` handling until the aggregate job is done or stopped.
A negative process-group value can select the group, but returned PIDs still
must update individual member state.

## Critical: many exits abandon terminal ownership

Fork failure after a successful early handoff, job-table failure, and wait
failure all return without reclaiming the terminal. Partial children and pipe
descriptors are also unaccounted for. Use one structured cleanup path that knows
which children, descriptors, table entry, and handoff were acquired. If a
handoff occurred, attempt to restore the terminal to the shell on every path;
cleanup must then reap or deliberately terminate the partial group.

## Medium: raw wait status escapes

Returning encoded `status` repeats the wait-status bug from the debugging lab.
Decode a final stage/job status only after its category is known and after the
documented pipeline-status policy is satisfied.

Pseudo-terminal tests should force the first stage to exit immediately while a
later stage sleeps, send Ctrl-C and Ctrl-Z through the terminal, resume stopped
jobs with `bg`/`fg`, inject failure on a later fork, and assert that the shell
regains terminal ownership and responsiveness after every case. Repeat the
short-child case to vary scheduling.

