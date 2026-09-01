# Review: `SIGCHLD` and a job table

`buggy.c` launches several short-lived children and tries to remove completed
entries from a global job table in a `SIGCHLD` handler.

From this exercise directory:

```sh
cc -std=c11 -Wall -Wextra -Wpedantic -O0 -g buggy.c -o buggy
timeout 2 ./buggy
```

The outcome is schedule-dependent: it may print entries, hang, corrupt state,
or appear to work. Apparent success is not evidence that signal interactions
are valid.

Find at least eight issues. Your review must cover:

- async-signal safety;
- whether one signal corresponds to one child event;
- insertion/removal races;
- the check-then-sleep sequence in `main`;
- table capacity and allocation failure;
- the difference between a PID and a pipeline job/process group;
- preservation of `errno`;
- stable job identity.

Propose a division of responsibility between minimal signal-time work and the
normal control path. Describe bounded tests that stress bursts of child exits
and the fork-to-table-insertion window.
