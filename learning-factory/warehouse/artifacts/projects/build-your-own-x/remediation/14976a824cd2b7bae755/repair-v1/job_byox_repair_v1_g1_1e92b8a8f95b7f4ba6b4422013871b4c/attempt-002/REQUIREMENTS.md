# MiniCTR requirements

This document is normative for the learner implementation. “Must” denotes required behavior; “should”
denotes a strong recommendation that may be assessed in review. Unless stated otherwise, output means
UTF-8 text and paths are host paths.

## 1. Scope and platform

1. The implementation must be Bash and must run on Linux.
2. The implementation must provide `starter/minictr` plus any helpers below `starter/`.
3. MiniCTR manages registrations for caller-supplied root filesystems. It must not pull images, copy a
   rootfs, configure a bridge, or act as a long-running daemon.
4. One registered instance may have at most one active `run` operation.
5. Namespace isolation is best-effort with respect to host kernel policy. Unsupported isolation must
   fail closed and return nonzero; it must never silently run the command on the host.

## 2. Invocation and diagnostics

The supported forms are:

```text
minictr create NAME ROOTFS
minictr run NAME COMMAND [ARG...]
minictr ps
minictr delete NAME
minictr help
minictr -h
minictr --help
```

1. Help must return zero, describe all four operations on standard output, leave standard error empty,
   and not create state.
2. An unknown operation, a missing operand, or an extra operand must return nonzero and print a concise
   diagnostic to standard error.
3. Operational diagnostics must start with `minictr:` and must not include secret environment values
   or dump entire metadata files.
4. `create` and `delete` must be silent on successful completion.
5. `run` must reserve standard output and standard error for the invoked command. Wrapper errors before
   launch go to standard error.
6. Exit codes for validation and state errors need only be nonzero. Once a command is launched, `run`
   must return that command’s exit status, including a value greater than 1.

## 3. Names and paths

1. `NAME` must match the ASCII byte grammar `[A-Za-z0-9][A-Za-z0-9_.-]{0,63}` and must not be
   `.` or `..`. The result must not depend on the caller's locale.
2. Name validation must happen before constructing a name-derived filesystem path.
3. `ROOTFS` must be an absolute path to an existing directory.
4. `ROOTFS` must not be `/` and must not contain a tab, carriage return, or newline. Spaces and shell
   metacharacters are otherwise valid path characters and must not be interpreted.
5. `create` must store a physical, canonical absolute rootfs path. Later operations must read it as
   data, not as shell syntax.
6. `run` must recheck that the registered rootfs is still a directory before invoking the isolator.
7. The canonical rootfs and resolved `MINICTR_HOME` must be disjoint: neither may equal or contain the
   other. `create` must reject an overlap before it creates any state inside the rootfs.

## 4. State root and persistence

1. All durable and transient MiniCTR state must stay below `MINICTR_HOME`.
2. When `MINICTR_HOME` is unset, the implementation should default to
   `${XDG_STATE_HOME:-$HOME/.local/state}/minictr`.
3. Tests may give each process an absolute temporary `MINICTR_HOME`; the implementation must honor it.
4. A registration must survive separate CLI invocations. Process-local variables are not durable state.
5. State must be created with permissions that do not grant access to other users by default.
6. Metadata must be parsed as data. It must never be evaluated or sourced as a shell program.
7. Updates that establish a registration or active run must be atomic from another MiniCTR process’s
   perspective. Partial state must not appear as a valid instance.
8. Temporary files and locks must not be placed alongside the caller’s rootfs or elsewhere on the host.
9. State-root/rootfs overlap must be detected before state initialization mutates either tree.
10. Path parsing and containment checks must fail closed if an internal read or temporary-storage
    operation fails. A failed check must produce a `minictr:` diagnostic rather than continuing with
    an empty or fallback path.

The exact internal directory and metadata layout is not a public API. Tests interact through the CLI.

## 5. `create`

`minictr create NAME ROOTFS` registers one idle instance.

1. It must apply all name and rootfs validation rules.
2. It must fail if `NAME` is already registered, regardless of whether the requested rootfs is the same.
3. Concurrent attempts to create the same name must yield exactly one success.
4. A failed create must not leave a registration visible to `ps`.
5. Success must return zero and produce no output.

## 6. `ps`

`minictr ps` reports registrations, not arbitrary host processes.

Its exact format is tab-separated:

```text
NAME<TAB>STATUS<TAB>PID<TAB>ROOTFS
```

1. The header must always be present, including when no instances exist.
2. There must be one row per registration, sorted by `NAME` in bytewise (`C`) order.
3. `STATUS` must be `CREATED` for an idle instance and `RUNNING` for an active `run`.
4. `PID` must be `-` when idle and a decimal host-visible PID when active.
5. `ROOTFS` must be the stored canonical path.
6. A stale active marker must not permanently make an instance look running. The implementation must
   distinguish PID reuse where host facilities make that information available, and a Linux process
   in zombie (`Z`) or dead (`X`) state must not count as a live owner.
7. `ps` must not invoke the isolator or mutate a healthy registration.

## 7. `run`

`minictr run NAME COMMAND [ARG...]` launches one foreground command.

1. `NAME` must exist and `COMMAND` must be a nonempty argument.
2. The isolator must receive exactly `ROOTFS`, `COMMAND`, and every `ARG` as distinct argv elements in
   that order. MiniCTR must not join, re-split, glob, or evaluate them.
3. The child must inherit the caller’s standard input, output, and error streams.
4. MiniCTR must expose the instance as `RUNNING` before the isolator begins user-command work.
5. A second `run` for that name must fail while the first is active.
6. `delete` for that name must fail while the run is active.
7. On normal exit, nonzero exit, or a handled interrupt/termination signal, transient active state must
   be removed and the durable registration must remain.
8. When the foreground wrapper receives `TERM`, the default isolation path must deliver `TERM` (not a
   substituted `KILL`) to the isolated command, return 143 after teardown, and keep cleanup bounded.
   `INT` should be forwarded when the direct helper remains alive; its wrapper result is 130.
9. A wrapper setup failure must return nonzero and restore the instance to `CREATED`.

### Test isolator seam

When `MINICTR_ISOLATOR` is set to a nonempty executable filesystem path, `run` must invoke that
executable instead of the Linux isolator. An absolute path is used directly; a relative path is
resolved from the caller's current working directory, not searched as a command name through `PATH`.
The call is exactly:

```text
MINICTR_ISOLATOR ROOTFS COMMAND [ARG...]
```

This seam is part of the exercise contract so lifecycle behavior can be tested without creating a
namespace. It is not a command string and must not be passed through `sh -c` or `eval`. When the
variable is unset, the default must be `lib/isolate.sh` resolved relative to the actual `minictr`
script, not relative to the caller’s working directory.

## 8. `delete`

1. `minictr delete NAME` must fail if the name is missing.
2. It must fail without removing durable state if the instance has an active run.
3. Concurrent run/delete decisions must be serialized so neither observes a half-deleted instance.
4. Success removes only that registration and its transient state, returns zero, and is silent.
5. It must never recursively delete the rootfs recorded by the registration.

## 9. Default Linux isolator

The learner-completed `starter/lib/isolate.sh` must:

1. fail before launching the command if required Linux tools or namespace operations are unavailable;
2. create fresh user, mount, PID, UTS, IPC, and network namespaces;
3. map the invoking user to root inside the user namespace without gaining host root;
4. prevent mounts made for the container from propagating back to the host;
5. change the apparent root to `ROOTFS`, use `/` as the working directory, and mount a namespace-local
   proc filesystem at `/proc`;
6. run `COMMAND [ARG...]` without a shell re-parse;
7. provide a small deterministic environment suitable for commands in the rootfs; and
8. unmount temporary mounts during teardown or rely on namespace destruction without leaving a host
   mount behind.

The reference signal contract uses `unshare --kill-child=TERM`. If the foreground wrapper terminates
the `unshare` supervisor, Linux therefore delivers `TERM` to its namespaced child. The wrapper may
escalate to `KILL` only after the documented bounded grace period.

The isolator must never fall back to running the command without these boundaries. Cgroups, seccomp,
capability minimization beyond the user namespace, and an OCI-compatible lifecycle are valuable but
outside the required core.

## 10. Safety and implementation quality

1. Do not use `eval`, `source`/`.`, or `bash -c` on learner-, metadata-, or CLI-controlled text.
2. Use quoted expansions and argv arrays. Use `--` where a utility supports it and an operand could
   begin with `-`.
3. Do not use shell command strings to call subprocesses.
4. Bound any wait for another process or lock and report timeout as an error.
5. Restrict cleanup targets to paths derived from a validated absolute `MINICTR_HOME` plus a validated
   name. Never delete a caller-supplied rootfs.
6. Preserve enough error context to debug a failure without claiming that namespace isolation passed
   when only the fake isolator ran.

## 11. Public acceptance behavior

The public suite verifies help/usage behavior, validation, deterministic lifecycle operations, sorted
status output, exact argv transport, child output and exit-status propagation, and active-run guards.
It does so with a fake isolator and no privileged operation. Real namespace isolation, malicious rootfs
hardening, PID-namespace init behavior, and production security require separate review and testing.
