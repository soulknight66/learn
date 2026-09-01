# Exercise 3: the child that finishes before it exists

`buggy.c` tries to keep a one-entry background-job table up to date directly
from a `SIGCHLD` handler. A fast child can exit before the parent publishes the
entry, after which the parent may pause forever with a stale `live` flag.

Tasks:

1. Write the event ordering that loses the child's completion.
2. Find every operation in the handler that is unsuitable for this design,
   including library calls and shared-state access.
3. Specify where `SIGCHLD` must be blocked and restored in both parent and
   child.
4. Redesign the handler/main-loop boundary so that coalesced signals cannot lose
   child statuses.
5. Explain why checking a flag and then calling `pause()` can introduce a second
   lost-wakeup race.
6. Propose a stress test that does not confuse a recycled PID with an old job.

Compile with:

```sh
cc -std=c11 -D_POSIX_C_SOURCE=200809L -Wall -Wextra -Werror \
  -o sigchld-race buggy.c
```

The broken executable may hang; use a bounded harness.

