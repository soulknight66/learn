# Reference design answers

## Boundaries and ownership

The reference uses three modules with one public header. `parser.c` owns all byte-to-argument transformation and performs no system calls that create processes. `shell.c` owns terminal state, transient pipes, transient foreground PIDs, and builtin dispatch. `jobs.c` owns copied labels, PID arrays, and per-process states for retained background or stopped jobs.

Parsing transfers ownership instead of duplicating twice: the lexer allocates each completed word, and a successful grammar pass moves that pointer into a null-terminated `argv`. A token pointer is nulled at transfer, so either token cleanup or pipeline cleanup owns it, never both. `msh_pipeline_destroy` is valid after every successful parse. On failure the output remains empty.

An explicit `started` bit distinguishes an empty quoted word from no pending word. Lexing uses normal, single-quoted, and double-quoted states. Operators are emitted only in normal state. Grammar validation runs over all tokens before the first command vector is allocated and long before execution.

## Pipeline graph

For `N` commands the parent creates `N - 1` pipes before forking. Child `i` duplicates pipe `i - 1` onto standard input when `i > 0`, and pipe `i` onto standard output when `i < N - 1`. It then closes every original pipe endpoint. The parent launches all `N` children, closes all endpoints, and only then waits.

Pipe descriptors are marked close-on-exec as a second line of defense. Every pipe and fork failure path closes known descriptors. If some children already exist, the parent signals their process group, continues it in case it was stopped, and waits for each recorded PID.

The PID array retains position: the last array entry is the command whose normalized wait status becomes the pipeline status, regardless of completion order.

## Process groups and races

The first child PID becomes the group ID. Each child calls `setpgid` before descriptor setup and `execvp`; the parent also calls `setpgid` immediately after each fork. Either side can win the scheduling race without leaving later children in separate groups. The shell never joins that group.

For an interactive foreground job, the parent calls `tcsetpgrp` with the job group, waits using a negative PGID, and restores its own group on every normal wait return. The shell ignores terminal-control and interrupt signals only in interactive mode. Every child restores default dispositions before exec.

A foreground wait retains one state and raw status per PID. Once each process has either exited or stopped, an all-done pipeline is discarded. If any member stopped, the whole snapshot is copied into the durable job table and the observed statuses are replayed into it.

## Job model

Each retained job owns a monotonically assigned ID, PGID, display label, ordered PID array, ordered state array, and raw status for the final pipeline member. A job is `Running` if any member runs, `Stopped` if none run and at least one is stopped, and `Done` only if all are done.

Nonblocking collection drains `waitpid(-1, ..., WNOHANG | WUNTRACED | WCONTINUED)` at command boundaries. `wait` uses blocking `waitpid`, never polling, until no retained process is running. Completed entries are removed only after `wait` has selected the highest job ID's last-command status. `jobs` deliberately retains and displays completed entries so a quick job remains observable.

## Builtins and errors

The executor scans all pipeline stages for builtin names before launching anything. A builtin combined with a pipe or background marker is rejected as a whole. Standalone builtins run in the parent, which is necessary for directory and exit state.

Parse/usage errors use status 2, not-found uses 127, other exec failures use 126, and wait statuses are decoded only through `WIF*` macros. The exec error value is saved before formatting its diagnostic so library calls cannot alter the status choice.
