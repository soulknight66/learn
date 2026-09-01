# Reference design

This document describes the sealed reference architecture for the educational
`minictr` runtime. It is a design answer, not a claim that a short shell
program forms a security boundary suitable for hostile multi-tenant use.

## Goals and boundary

The public CLI has four operations:

```text
minictr create NAME ROOTFS
minictr run NAME COMMAND [ARG...]
minictr ps
minictr delete NAME
```

`MINICTR_HOME` is a trusted state-root choice. Names, rootfs paths, commands,
arguments, state-file contents, concurrent invocations, and child statuses are
untrusted. The CLI owns deterministic validation and lifecycle bookkeeping.
The isolator owns kernel-facing setup. That boundary keeps state-machine tests
rootless: `MINICTR_ISOLATOR` can name a capture helper invoked as exactly
`ISOLATOR ROOTFS COMMAND [ARG...]`.

## Components

- `minictr` performs dispatch, arity checks, validation, diagnostics, and calls
  lifecycle functions.
- `lib/runtime.sh` owns state paths, coordination, create/run/list/delete, and
  live-process verification.
- `lib/isolate.sh` is the default Linux adapter. It composes namespace, mount,
  environment, and chroot tools using argv elements, never a shell command
  string.
- The public and sealed tests substitute a fake isolator. Its capture-specific
  variables are test fixtures, not runtime API.

All ordinary errors use a `minictr:` prefix on stderr and a nonzero status.
Create and delete are silent on success. Run exposes only child stdio and
returns the child's status. `ps` alone emits runtime-generated data.

## Validation before derivation

The name grammar is the ASCII byte grammar
`[A-Za-z0-9][A-Za-z0-9_.-]{0,63}`. Validation forces the C locale and rejects
dot entries explicitly before a name is appended to a state path. This makes
containment a construction invariant rather than a locale-sensitive or later
string-prefix guess.

A rootfs must be an absolute existing directory. The runtime canonicalizes it,
rejects `/`, and rejects tab, carriage-return, and newline delimiters before
storing it. The canonical value is the one passed to the isolator and printed by `ps`.
Commands are not interpreted or normalized; after arity validation they remain
an argument vector.

Before state initialization, the runtime resolves the prospective state path
through its nearest existing physical ancestors and normalizes the remaining
components. It rejects either-direction overlap with the canonical rootfs.
This prevents registration itself from writing into the filesystem being
registered and keeps later state cleanup outside that tree. Component parsing
uses Bash parameter expansion rather than a here-string, so unavailable
temporary storage cannot empty the component list and turn the check into a
successful resolution of `/`.

## Durable and transient state

The logical layout beneath `MINICTR_HOME` is:

```text
containers/
  NAME/
    rootfs       canonical, line-safe rootfs
    run          transient owner PID plus Linux process-start token
locks/           runtime-owned coordination entries
```

An atomic per-name lock directory serializes the name claim. Metadata is built
in a private temporary directory and renamed into place before the operation
is reported successful. A failed creator removes only its private staging
directory. A duplicate creator cannot overwrite the winner's `rootfs` record.

The `run` record is transient evidence, not a durable assertion that a process
is alive. PID alone is insufficient because the kernel reuses PIDs. The paired
start token from `/proc/PID/stat` makes identity `(pid, start-token)`. Readers
parse both strictly and compare the current process token. Missing, malformed,
zombie, dead, or mismatched evidence is stale.

## Operation flows

### Create

1. Validate the name and rootfs without changing state.
2. Resolve and reject state/rootfs overlap before creating state.
3. Ensure runtime-owned parent directories exist with a restrictive umask.
4. Enter per-name coordination and prepare a private complete state directory.
5. Rename that directory to commit `containers/NAME` atomically.
6. On an initialization error, clean up only the claim from this invocation.

The externally visible transition is absent to `CREATED`; two successful
creates of the same name are impossible.

### Run

1. Validate the name and require at least one command element.
2. Under per-name coordination, require a complete container entry and no
   verified live run.
3. Record the owning CLI process PID and start token, then release
   coordination before executing a potentially long workload.
4. Invoke the isolator without `eval`, inherit its stdin, stdout, and stderr,
   and capture its exact status.
5. Re-enter coordination and remove the run record only if it is still the
   record owned by this invocation.
6. Return the captured child status after cleanup.

The ownership comparison prevents an old cleanup path from deleting evidence
for a successor. Signal paths apply the same owner-checked cleanup rule.

### List

`ps` scans only valid container-entry names, accepts only complete rootfs
records, and classifies a run as `RUNNING` only when owner PID and start token
both match and `/proc` reports neither zombie nor dead state. It prints:

```text
NAME<TAB>STATUS<TAB>PID<TAB>ROOTFS
```

Created entries use status `CREATED` and PID `-`. Rows are sorted by name with
the C locale so filesystem enumeration order and locale do not leak into the
interface. Stale transient evidence is treated consistently; it cannot make a
container permanently undeletable.

### Delete

Delete enters the same per-name coordination as run. It requires a complete
known entry and refuses a verified live run. Removal is limited to the already
validated instance path. The visible transition is `CREATED` to absent.

## Default isolation sequence

The Linux adapter uses an explicit tool chain to create the requested
namespaces, establish a private mount view, mount a constrained proc filesystem
inside the rootfs, prepare a minimal environment, and execute the command
through chroot. Each
tool path is one executable and all user values remain separate argv elements.
Test-only executable overrides allow deterministic verification of the
sequence without granting namespace privileges.

The wrapper's TERM path signals the direct `unshare` helper. The helper uses
`--kill-child=TERM`, so supervisor death sends the same catchable signal to the
namespaced stage/payload rather than util-linux's default SIGKILL. Cleanup polls
for a bounded grace interval before escalation.

Namespace setup can still fail because of kernel configuration, capabilities,
user-namespace policy, mount propagation, or an incomplete rootfs. Such a
failure is surfaced as a run failure; the control plane does not relabel it as
success.

## Invariants

- No unvalidated name participates in a state path.
- The physical state and rootfs trees are disjoint before the first state write.
- Exactly one create owns a given absent-to-created transition.
- A live run excludes delete and another run for the same instance.
- Only the owner of a transient run record may remove it.
- State-derived process liveness requires PID, start token, and a non-zombie,
  non-dead process state.
- User command data is never parsed as shell source.
- Child output and status cross the wrapper unchanged.
- Listing order and formatting do not depend on directory order or locale.

These invariants make the control plane teachable and testable. They do not add
cgroups, seccomp, image verification, capability minimization, networking, or
an OCI-compatible lifecycle.
