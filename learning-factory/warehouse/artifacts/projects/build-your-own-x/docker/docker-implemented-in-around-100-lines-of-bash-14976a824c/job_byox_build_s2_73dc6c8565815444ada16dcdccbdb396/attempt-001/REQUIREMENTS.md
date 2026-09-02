# Tinybox requirements

This document is the normative learner contract. `ROOT` below means the configured Tinybox state
directory, not the operating system root directory.

## Platform and process model

- Use Bash and begin both scripts with `#!/usr/bin/env bash` plus `set -eu` or stricter behavior.
- The controller must work without elevated privileges when a test runner is selected.
- Invoke subprocesses with quoted argv elements. Do not use `eval`, `source`, `sh -c`, or a command
  assembled into one string.
- Diagnostics go to stderr. Machine-readable command output goes to stdout.
- `help`, `--help`, and `-h` print usage and return zero. Usage errors return `2`; all other
  controller errors return a nonzero value.

## State root and names

Use `TINYBOX_STATE_DIR` when it is set. Otherwise use
`${XDG_STATE_HOME:-$HOME/.local/state}/tinybox`. Reject an empty state path and `/`. Create state with
private permissions (`umask 077`) and this layout:

```text
ROOT/
  containers/NAME/
    rootfs/
    status
    exit_code        # only after a completed run
  locks/NAME.lock/   # exists only while a mutating operation owns it
  tmp/
```

A name must match `^[a-z][a-z0-9_-]{0,31}$`. Validate it before forming any name-derived path.
Metadata is plain text and must be read as data, never sourced as shell code.

## Lifecycle

The allowed transitions are:

```text
absent -> CREATED -> RUNNING -> EXITED
                    ^          |
                    |__________|

CREATED -> absent (delete)
EXITED  -> absent (delete)
```

Each mutating command obtains the container lock with an atomic operation. If the lock is already
held, fail rather than waiting forever. Status updates use write-to-temporary-file plus rename. A
normal runner failure and a handled `INT` or `TERM` must not leave status as `RUNNING`.

## Commands

### `create NAME ROOTFS`

- Require exactly two operands, a valid name, and an existing directory.
- Fail if that name already exists.
- Build in `ROOT/tmp`, copy the *contents* of `ROOTFS` recursively while preserving modes and
  symlinks, write `CREATED`, then atomically publish the complete container directory.
- A later change to the source directory must not change the copied rootfs.
- Print the name followed by a newline on success.

### `list`

Accept no operands. Print one line per published container, sorted bytewise by name:

```text
NAME<TAB>STATUS
```

An empty state prints nothing. Ignore unrelated entries and incomplete temporary state.

### `inspect NAME`

Require one valid, existing name. Print exactly these lines, with an empty value when no exit code
has been recorded:

```text
name=NAME
status=STATUS
exit_code=VALUE
```

Reject missing, empty, or unrecognized status data rather than evaluating it.

### `run NAME -- COMMAND [ARG ...]`

- Require a valid existing name, the literal separator `--`, and at least one command element.
- Require `COMMAND` to start with `/`, because it is resolved within the container rootfs.
- Permit runs only from `CREATED` or `EXITED`.
- Select `${TINYBOX_RUNNER}` when set, otherwise `runner.sh` beside the controller. Require it to be
  an executable regular file.
- While holding the lock, remove an old `exit_code` and atomically change status to `RUNNING`; then
  release the lock before waiting for the runner.
- Invoke the runner as `RUNNER ROOTFS NAME COMMAND [ARG ...]`, preserving every argument exactly.
- Forward its stdout/stderr and return its exact exit status. On completion, atomically record that
  numeric status in `exit_code` and change status to `EXITED`.

The runner interface is deliberately injectable for deterministic tests. A controller is not
allowed to claim isolation; only the selected runner creates it.

### `delete NAME`

Require one valid, existing name. Delete only a `CREATED` or `EXITED` container. Refuse `RUNNING`.
After validating both the name and constructed target, recursively remove exactly
`ROOT/containers/NAME`. Print the name on success.

## Linux runner

`starter/runner.sh` receives `ROOTFS NAME COMMAND [ARG ...]`. It must validate its inputs, ensure a
`proc` mount point exists inside the rootfs, require GNU/Linux `unshare` plus `mount`, `hostname`, and
`chroot`, and execute the command in new user, mount, PID, UTS, and IPC namespaces. Map the caller to
root only inside the user namespace, set the hostname to `NAME`, change root and working directory to
`/`, mount a private `/proc`, and forward the command as argv. Adding a network namespace is an
optional extension.

Availability of these features depends on kernel and site policy. A clear nonzero failure is correct
when the host denies user namespaces.

## Out of scope

Image downloads, layered filesystems, cgroups, networking setup, capabilities hardening, seccomp,
daemon supervision, distributed state, and hostile multi-user security are intentionally omitted.
