# Study Task: Build `proc-run`

## Goal

Build a C++17 command-line program that runs one child command as a separate process group, keeps the child's standard output and standard error separate, enforces a wall-clock timeout, reaps the direct child, and returns a documented status. Treat it as a maintainable system component rather than a one-off algorithm exercise.

Timebox the complete task to about ten hours.

## Required interface

Your executable must be named `build/proc-run` and accept:

```text
build/proc-run --timeout-ms N --stdout PATH --stderr PATH -- PROGRAM [ARG ...]
```

`N` is a positive base-10 integer. `--` ends runner options. Every token after it is one element of the child's argument vector; do not join those tokens into a command string. `PATH` names files created or truncated for the child's two output streams.

The runner must use these process-result conventions:

- return the child's exit status after a normal exit;
- return `128 + signal_number` when the child terminates from a signal;
- return `124` when the timeout policy takes effect;
- return `125` for runner usage or parent-side setup failure;
- return `127` when the requested program cannot be executed.

Diagnostics produced by the runner itself must go to the runner's standard error. Child output belongs only in the two requested files.

## Behavioral requirements

1. Validate all runner options before launching a child. Reject missing values, an invalid or zero timeout, a missing `--`, and a missing program.
2. Launch directly with a POSIX `fork`/`exec` interface. Do not use `system`, `popen`, `/bin/sh -c`, or another shell intermediary.
3. Put the child in a new process group. On timeout, send `SIGTERM` to that group, allow a bounded 200 ms grace period, then send `SIGKILL` to the group if the direct child has not exited.
4. Measure the deadline with a monotonic clock. A child that exits while timeout handling begins must still be reaped; the runner must never wait indefinitely.
5. Redirect the child's standard output and standard error to their respective paths. Close unneeded descriptors in both processes. A child-side setup or execution failure must terminate through a child-safe failure path rather than continuing through parent logic.
6. Interpret the complete `waitpid` status instead of treating it as a plain exit code. Reap the direct child exactly once on every launched-child path.
7. Handle interrupted system calls where interruption is a valid occurrence. Report actionable diagnostics without printing misleading success messages.
8. Do not add network access, privilege changes, a shell parser, background mode, configuration files, or third-party libraries.

## Engineering workflow

### 1. Specify before coding

In `submission/DESIGN.md`, draw or describe the parent/child state transitions from validated input through final reap. State at least four lifecycle invariants, identify where each file descriptor is owned, and list the important failure points. Include a short rationale for direct `argv` execution and process-group timeout handling.

### 2. Build the smallest end-to-end path

First make a normal command run, redirect, exit, and reap. Add error reporting and status interpretation. Add the monotonic deadline and two-stage group termination only after the normal lifecycle is testable. Keep OS-facing operations in small functions whose contracts can be reviewed.

### 3. Automate integration checks

Tests may use the Python standard library, POSIX shell, or small compiled helper programs, but they must run locally without a network or third-party package. Cover at least:

- normal exit with distinct stdout and stderr text;
- propagation of a nonzero child exit status;
- preservation of empty arguments, spaces, and shell metacharacters as literal arguments;
- a nonexistent executable;
- timeout of a long-running child;
- timeout of a child that creates a descendant in the same process group;
- repeated quick runs, including a check that the runner does not hang.

Avoid tests that rely on exact sub-millisecond scheduling. Each test must use its own temporary paths and clean up its processes and files.

### 4. Review like a maintainer

Run the full suite from a clean build. Use compiler warnings. Inspect at least one failure path with a debugging or tracing tool available on your system, and record what you inspected in `submission/README.md`. Explain known limitations without claiming they work.

## Submission layout

Submit exactly this top-level structure (you may organize files beneath `src/` and `tests/`):

```text
submission/
├── README.md
├── DESIGN.md
├── COMPREHENSION_RESPONSES.md
├── Makefile
├── src/
└── tests/
```

The following commands must be documented and noninteractive:

```text
make -C submission clean all
make -C submission test
```

`README.md` must state the platform assumptions, compiler requirement, build and test commands, interface examples, exit-status contract, debugging/tracing observation, and known limitations. Do not include downloaded course material or solutions in the submission.
