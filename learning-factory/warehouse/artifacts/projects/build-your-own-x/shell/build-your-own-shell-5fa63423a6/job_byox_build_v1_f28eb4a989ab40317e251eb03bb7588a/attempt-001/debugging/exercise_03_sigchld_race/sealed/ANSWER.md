# Answer: publish jobs while `SIGCHLD` is blocked

One failing schedule is:

1. the parent forks;
2. the child exits immediately;
3. the handler reaps it, sees no matching published PID, and returns;
4. the parent writes the PID and `live = 1`;
5. no child event remains to produce another signal, so `pause` never returns.

The handler also calls `printf`, which is not async-signal-safe, traverses and
mutates ordinary shared objects, and does not preserve `errno`. Updating the
table from both interrupted and handler control flow makes its invariants
unreviewable even beyond the publication race.

Before `fork`, the parent should block `SIGCHLD` and remember its prior mask.
While it remains blocked, the parent establishes the process group and
publishes a complete table entry. It then restores the prior mask. The child
inherits the blocked mask and must restore the prior mask before executing user
code. All launch-failure paths must restore the parent's mask too.

The handler can be reduced to a coalescing notification:

```c
static volatile sig_atomic_t child_pending;

static void child_changed(int signal_number)
{
    int saved_errno = errno;
    (void)signal_number;
    child_pending = 1;
    errno = saved_errno;
}
```

This snippet requires `<errno.h>`.

Normal control flow responds by repeatedly calling `waitpid(-1, &status,
WNOHANG | WUNTRACED | WCONTINUED)` until it returns zero, retrying `EINTR`, and
updating the job table for every returned PID. Signals may coalesce because each
wakeup drains all available statuses rather than expecting one status per
signal.

There is still a lost wakeup if code observes `child_pending == 0`, receives a
signal, and then calls `pause`. Block `SIGCHLD` while testing the predicate and
use `sigsuspend` with a mask that atomically unblocks it while sleeping, or
integrate a nonblocking self-pipe with `pselect`/`poll`. Always re-check the
predicate in a loop.

A stress test should launch many immediate-exit jobs while varying scheduling,
then require every job to reach a terminal state and every child to be reaped
before a deadline. Store membership and generation/job identity, not merely a
bare PID, so later PID reuse cannot satisfy an assertion about an earlier job.
