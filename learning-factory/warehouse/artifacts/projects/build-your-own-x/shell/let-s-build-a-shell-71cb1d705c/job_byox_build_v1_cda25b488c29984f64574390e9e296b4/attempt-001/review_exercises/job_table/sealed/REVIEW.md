# Review findings

1. **The handler uses non-async-signal-safe functions.** `printf` and `free` may
   acquire libc locks or mutate allocator/stdio state interrupted in the main
   flow. The handler must restrict itself to signal-safe notification work;
   ordinary control flow should update and print the table.

2. **The handler mutates shared compound state.** `volatile sig_atomic_t` makes
   individual accesses to `job_count` observable; it does not make the array,
   pointer updates, or multi-step removal atomic. A handler can interrupt table
   insertion or other main-flow traversal at an inconsistent point.

3. **Only one event is reaped per handler call.** Standard signals may coalesce.
   The normal reaper must call nonblocking `waitpid` in a loop until no more
   state changes are available, handling each returned PID.

4. **`errno` is not preserved.** Even a minimal handler can change the interrupted
   code's `errno`. Save it on entry and restore it on exit.

5. **There is a fork-to-insertion race.** A child can exit and be reaped before
   its table entry exists. The handler then discards an unknown PID, and the
   subsequently inserted entry can never complete. Block `SIGCHLD` around fork
   and insertion, establish all metadata, then restore the mask and reap
   pending changes.

6. **The main loop has a lost-wakeup race.** A final child can be removed after
   `job_count > 0` is tested but before `pause`; with no future signal, the
   process sleeps forever. Atomically unblock-and-wait with `sigsuspend` (or use
   a self-pipe/signalfd event loop) while reevaluating the condition.

7. **Fork failure is stored as a job.** A negative PID is inserted because the
   parent path never checks `fork` failure. Diagnose it and leave the table
   unchanged.

8. **Capacity is unchecked.** The demonstration exactly fills eight slots, but
   the ninth writes beyond `jobs`. Reject, grow safely in normal flow, or reap
   before insertion according to an explicit capacity policy.

9. **`strdup` failure is unchecked.** A NULL description is later passed to
   `%s`. Allocate metadata before exposing a complete entry, and roll back
   cleanly on failure.

10. **Removal changes identity/order.** Replacing an entry with the last entry
    changes display order. Array position cannot serve as a stable shell job
    ID; store a monotonic ID and sort or traverse accordingly.

11. **One PID is not one job.** A shell job can be a pipeline containing several
    PIDs in one process group. Track member processes and their statuses, plus a
    PGID for group signal/terminal operations. Derive aggregate job state from
    members.

12. **Signal installation is underspecified.** `signal` has historically
    varying restart semantics and cannot set a mask intentionally. `sigaction`
    makes the handler mask and flags explicit. Whether waits/reads restart must
    agree with the event-loop design.

13. **Shutdown evidence is lost.** Completed entries are immediately freed,
    including their exit status. A shell may still need the final-stage status
    for a foreground wait or completion notification. Define when all consumers
    have observed a durable record before removing it.

A suitable responsibility split is for the handler to set a `sig_atomic_t`
flag or write one byte to a pre-created nonblocking self-pipe. With `SIGCHLD`
blocked at the needed critical sections, normal flow drains all wait results,
updates a PID-indexed table, derives per-job state, performs output, and then
waits atomically for more work. Tests should launch bursts much larger than the
table and deliberately yield around fork/insertion; every run needs a timeout
and an exact accounting of created and reaped PIDs.
