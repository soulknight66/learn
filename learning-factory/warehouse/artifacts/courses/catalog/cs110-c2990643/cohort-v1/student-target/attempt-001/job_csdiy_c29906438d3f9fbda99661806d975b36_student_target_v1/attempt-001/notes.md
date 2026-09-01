# Kickoff unit learning notes

## Scope and provenance

These notes cover only the supplied process-supervisor kickoff unit. I used the
three learner-safe files `COURSE_BRIEF.md`, `COMPREHENSION.md`, and
`STUDY_TASK.md`; I did not retrieve linked material or attempt later course
units. Completing this artifact is not completion of CS110 or any Stanford
requirement.

## Core model

- A **program** is executable code/data on storage; an `exec` call replaces the
  current **process image** with that program. The process is the live kernel
  object with a PID, address space, descriptor table, credentials, and state.
- A **process group** is a kernel grouping addressed by a negative PID in
  `kill`. A forked descendant ordinarily inherits its parent's group. This makes
  the group useful for timeout fan-out but does not stop a process from moving
  to another allowed group/session.
- `fork` logically copies user-space state and a descriptor table. The copied
  descriptor entries still reference shared kernel open-file descriptions.
  Child `dup2`/`close` operations therefore do not edit the parent's descriptor
  table, but inherited offsets and status flags require care until extra copies
  are closed.
- `waitpid` returns an encoded status, not just an exit number. Normal exit and
  signal death must be decoded with different macros. Timeout is additional
  policy state maintained by the parent, not a third kernel wait-status kind.

## Concrete hypotheses and experiments

1. **Hypothesis:** Direct `argv` execution preserves empty strings, spaces, and
   shell metacharacters without quoting logic. **Experiment:** passed six such
   values through `proc-run` to Python and decoded the resulting JSON array.
   **Outcome:** all six values, including the empty string and
   `$(printf not-a-command)`, matched byte-for-byte; the integration test passed.
2. **Hypothesis:** Signalling `-child_pid` reaches a descendant that inherits the
   group. **Experiment:** the direct child ignored `SIGTERM`, spawned a
   descendant with a handler that wrote a marker, and then waited.
   **Outcome:** the marker recorded `SIGTERM received`; after the 200 ms grace,
   the direct child required `SIGKILL`, and the runner returned 124.
3. **Hypothesis:** A close-on-exec error pipe can distinguish failed `execvp`
   from a successfully executed program without contaminating the child's
   requested stderr file. **Experiment:** requested a definitely nonexistent
   absolute path. **Outcome:** parent stderr reported `execvp` plus `ENOENT`, the
   requested child stderr file stayed empty, and the return code was 127.
4. **Hypothesis:** Complete validation before resource setup prevents an invalid
   request from truncating output artifacts. **Experiment:** prefilled both
   output files, invoked a zero timeout, and compared contents afterward.
   **Outcome:** status 125 was returned and both sentinels were unchanged.
5. **Hypothesis:** Repeated fast exits will reveal an accidental double wait or
   blocking control path. **Experiment:** ran 20 independent Python no-op
   children, each with its own files and a three-second outer test bound.
   **Outcome:** every launch returned zero and the suite completed without a
   hang.

## Production-engineering lessons

- Lifecycle state needs explicit ownership. A boolean policy decision
  (`timed_out`) and one successful reap are more reliable than inferring intent
  afterward from a signal-shaped wait status.
- Post-fork code should be deliberately small. The child uses system calls,
  reports a fixed record, and ends failures with `_exit`; formatting happens in
  the parent.
- `FD_CLOEXEC` can be a protocol: EOF means the image replacement succeeded,
  while a fixed record means a pre-exec stage failed.
- Race handling should define acceptable outcomes. At the deadline, one last
  `WNOHANG` check gives an already-waitable child its natural result; after that,
  timeout policy wins even if `kill` observes `ESRCH`.
- Tests need two clocks: the behavior deadline being checked and a much larger
  harness deadline that turns a hang into a bounded failure without asserting
  exact scheduling.
- Tool availability is not the same as permission to use a tool. `strace` and
  `perf trace` were installed but blocked by sandbox/kernel configuration, so a
  coverage-instrumented build supplied narrower, accurately labeled evidence.

## Deliberate boundaries

This unit does not solve session-wide containment, descendant reaping, output
quotas, environment sanitization, artifact-path aliasing, or scalable
multi-process event notification. Those are known interface and architecture
questions, not features silently assumed to work.
