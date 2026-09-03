# Requirements and acceptance contract

Implement the missing behavior in `starter/minictr` using only the Python 3.11 standard library.
All errors at the configuration boundary must be `minictr.errors.ValidationError`; invalid lifecycle
operations must raise `minictr.errors.TransitionError`.

## R1 — validated immutable specification

`ContainerSpec.from_mapping(value)` returns an immutable spec and:

- accepts exactly `id`, `rootfs`, `command`, `hostname`, `env`, `timeout_seconds`,
  `readonly_root`, and `network`;
- requires an ID matching `[a-z][a-z0-9_-]{0,31}`, an absolute rootfs path, a nonempty list of
  nonempty string arguments, and a hostname of 1–63 lower-case letters, digits, dots, or hyphens;
- accepts environment names matching `[A-Za-z_][A-Za-z0-9_]*`, string values without NUL, and at
  most 128 entries;
- accepts a finite numeric timeout from 0.1 through 300 seconds but rejects booleans; and
- requires actual booleans for `readonly_root` and `network`.

`to_mapping()` must return new mutable containers and never expose internal aliases.

## R2 — filesystem containment

`validate_rootfs(path)` requires a `pathlib.Path`, returns the canonical absolute directory, and
rejects every other input type, a nonabsolute path, the host filesystem root `/`, a symlink supplied
as the root, a missing path, or a nondirectory. All such rejections raise `ValidationError`.

`resolve_guest_path(rootfs, guest_path)` accepts a guest-absolute POSIX path and returns its canonical
host path only if it remains beneath the canonical rootfs. Reject NUL, relative paths, `..`
components, and any existing symlink chain that escapes. Lexical prefix checks are not sufficient:
`/tmp/root-other` is not beneath `/tmp/root`. This helper reduces mistakes but does not eliminate
time-of-check/time-of-use races; production code would use descriptor-relative kernel APIs.

## R3 — namespace launch plan

`build_launch_plan(spec, unshare_path)` returns an immutable `LaunchPlan`. `unshare_path` must be an
absolute executable regular file. The argv must be a tuple beginning with that exact path and use
separate flags for:

- a user namespace mapped to root inside the namespace;
- mount, UTS, IPC, and PID namespaces;
- forked PID-1 semantics and kill-child behavior; and
- a network namespace exactly when `spec.network` is false.

The rootfs must contain a real `proc/` directory. The host-side Python child helper receives the spec
on stdin—not embedded in argv—and, after entering the new PID and mount namespaces, mounts procfs at
that directory before the chroot/exec boundary. This child-side mount avoids incompatible
`unshare --mount-proc=<path>` behavior found on some util-linux/kernel combinations. `LaunchPlan`
must carry a bounded timeout and a minimal helper environment.

The real-execution CLI must first run a separate setup-only `minictr.preflight` plan using the same
namespace flags and validated spec. The preflight is capped at ten seconds, performs rootfs setup
but never execs the workload, and must abort the run on timeout or setup failure. In particular, a
host/filesystem that rejects the default read-only remount must receive an actionable unsupported
result before workload launch; the runtime must not silently change `readonly_root` to false.

## R4 — atomic lifecycle registry

`Registry` persists rows in SQLite with states `CREATED`, `RUNNING`, `EXITED`, and `FAILED`.
Transitions are only:

```text
CREATED -> RUNNING -> EXITED
                   -> FAILED
```

Schema-level checks or triggers must reject every other state change. `create`, `claim_start`, and
`finish` use explicit transactions; the claim uses `BEGIN IMMEDIATE` so two launchers cannot both
win. SQL values are parameterized. Caller-provided RFC 3339 timestamps make tests deterministic.
This workshop profile deterministically rejects the optional `:60` leap-second spelling instead of
maintaining an external leap-second table. Failed rows, exit codes, and captured log locations
remain durable. The fixed transition set must not be extensible by inserting ordinary policy rows;
an existing registry from the earlier mutable-table schema must be migrated atomically.

## R5 — bounded process supervision

`Runner.run(plan, payload)` starts an argv array with `shell=False`, binary pipes, a fresh session,
and a minimal environment. It writes at most 1 MiB of canonical JSON to stdin and captures stdout
and stderr. On timeout it sends `SIGKILL` to the process group, reaps the child, and returns a result
marked `timed_out`; it never silently reports success. The public API must be injectable so tests do
not launch namespaces.

## Out of scope and completion rule

Layer extraction, seccomp, capabilities, cgroup resource accounting, networking setup, OCI image
compatibility, daemon concurrency, log rotation, and production hardening are intentionally out of
scope. Do not claim production safety. Completion requires the public suite plus independent hidden
tests; privileged integration is separately assessed. Instructor/source and learner artifacts must
be exported separately, and every exported payload file must be covered by that view's generated
path/size/SHA-256 manifest.
