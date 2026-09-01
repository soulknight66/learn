# Requirements and acceptance contract

The public API is the `minibox` package in `starter/`. Do not change names or signatures that are exercised by public tests.

## R1 — identifiers and specifications

- `validate_identifier(value)` accepts 1–64 lowercase ASCII letters, digits, `.`, `_`, and `-`; the first character must be alphanumeric.
- Booleans, bytes, empty strings, uppercase text, slashes, whitespace, and non-ASCII text are rejected with `InvalidIdentifier`.
- `ContainerSpec` validates both identifiers, requires a non-empty tuple/list of non-empty string arguments, validates environment variable names, and requires a normalized absolute POSIX working directory without `..` components.
- Serialization is canonical and round-trips without sharing mutable environment mappings.

## R2 — lifecycle model

Supported transitions are:

```text
CREATED -> RUNNING | DELETED
RUNNING -> EXITED | FAILED
EXITED  -> RUNNING | DELETED
FAILED  -> RUNNING | DELETED
DELETED -> (none)
```

Self-transitions and all omitted edges raise `InvalidTransition`.

## R3 — safe filesystem layers

- `apply_layer(layer_path, rootfs, limits=...)` accepts only regular files and directories plus regular-file whiteout markers.
- Absolute names, traversal, NULs, backslashes, duplicate normalized destinations, links, devices, FIFOs, sockets, and size/count limit violations raise `InvalidArchive` before any archive payload is written.
- Existing symlink components in `rootfs` are never followed.
- `.wh.NAME` removes `NAME` in the same directory. `.wh..wh..opq` removes existing children in that directory. Marker files do not remain in the result.
- File contents are streamed, setuid/setgid/sticky bits are stripped, and reported statistics describe payload files and bytes actually written.

## R4 — durable state

- `StateStore` applies numbered SQL migrations and enables foreign keys.
- `create(spec)` atomically inserts a `CREATED` container and its first event.
- `transition(id, expected, target, exit_code=None)` uses `BEGIN IMMEDIATE`, compares the durable state with `expected`, and atomically updates state plus an append-only event.
- Unknown IDs, stale expected states, duplicate IDs, and invalid graph edges have distinct domain errors. Failed operations leave state and event history unchanged.
- SQL values are parameterized. A database trigger independently enforces the transition graph.

## R5 — namespace plan

- `LinuxNamespaceBackend.build_argv(rootfs, spec)` returns an immutable argv tuple beginning with the configured `unshare` executable.
- The plan creates user, mount, PID, UTS, and IPC namespaces, maps the caller to root inside the user namespace, forks, mounts `/proc`, changes root and working directory, uses `--` before the payload, and adds a network namespace only when requested.
- Neither identifiers, paths, environment values, nor command arguments are evaluated by a shell.

## R6 — bounded execution

- `Runner` performs compare-and-transition from `CREATED`, `EXITED`, or `FAILED` into `RUNNING`, launches an argv array with `shell=False`, captures bytes, starts a new session, and enforces a positive timeout.
- Timeout terminates the process group, records `FAILED`, and returns a timeout result. A launched process that exits (including nonzero) records `EXITED` and its exact code. A launch failure records `FAILED` and is surfaced as a domain error.
- Captured output is bounded. Truncation is explicit in the result.

## R7 — workspace and CLI

- Image import stages a new image directory, applies one layer, records a canonical manifest, and publishes it atomically. Existing image IDs are never overwritten.
- Container creation copies an image root filesystem into a per-container writable directory before inserting durable state; failures clean only their own staging path.
- The CLI offers `image-import`, `create`, `inspect`, `events`, and `run`, emits machine-readable JSON, writes errors to stderr, and uses nonzero exit status on failure.

## Non-goals

Registry protocols, multi-layer caching, overlay mounts, cgroups, network setup, capability reduction, seccomp, LSM policy, signatures, and production hardening are explicitly out of scope. They belong in a production design, not in claims about this artifact.
