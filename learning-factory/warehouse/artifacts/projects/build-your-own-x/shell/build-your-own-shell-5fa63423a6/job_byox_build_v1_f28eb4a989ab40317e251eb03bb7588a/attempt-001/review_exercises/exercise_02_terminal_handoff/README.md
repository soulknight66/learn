# Review 2: process groups and terminal handoff

`candidate.c` is pseudocode-quality C from a proposed foreground-pipeline
launcher. Helper details are omitted so the review can focus on ordering.
Assume the interactive shell ignores Ctrl-C/Ctrl-Z-related terminal signals and
currently owns `terminal_fd`.

Perform a concurrency review rather than assuming parent and children run in
source order:

1. enumerate schedules around `fork`, `setpgid`, `exec`, and `tcsetpgrp`;
2. determine which processes receive terminal-generated signals;
3. determine which pipeline members are waited for and reaped;
4. inspect every route by which the function can return without reclaiming the
   terminal;
5. account for a child that exits before job-table publication;
6. propose a correct launch protocol and pseudo-terminal regression cases.

Treat ignored return values as findings only when you can explain the resulting
state and recovery requirement.

