# Minibox requirements

This document is the normative learner contract. “Must” identifies required
behavior. The optional Linux integration section is explicitly marked; all
other sections are part of the deterministic core.

## 1. General constraints

- Implement a Python package named `minibox` under `starter/`.
- Support Python 3.10 or newer.
- Use only the Python standard library for the required implementation.
- Keep imports and deterministic unit tests usable on non-Linux hosts. Linux
  facilities may be consulted only when the optional backend actually runs.
- Never invoke a shell. Any subprocess command must be represented as an
  argument sequence.
- Domain failures must use the exception hierarchy below rather than
  assertions or process termination:

  - `MiniboxError` is the common base for expected Minibox failures.
  - `SpecError`, `RootfsError`, and `StateError` report failures in the three
    deterministic policy boundaries. `StateCommitUncertain` is a
    `StateError` subtype reserved for the post-publication persistence outcome
    defined in section 5.
  - `BackendError` is the base for execution setup and supervision failures.
  - `BackendUnavailable` reports a host that cannot provide the optional
    backend.
  - `BackendTimeout` reports an execution that exceeded its deadline.

These classes live in `minibox.errors` and are re-exported from the `minibox`
package root. The package root likewise re-exports the public values named in
the later sections.

Exact error-message wording is not part of the interface. Messages should be
brief and must not disclose the full environment or unrelated host data.

## 2. Strict container specification

`minibox.config` must expose:

```python
ContainerSpec
from_dict(data) -> ContainerSpec
load_spec(path) -> ContainerSpec
```

`ContainerSpec` is a value object with these normalized fields:

| Field | Required input | Valid value | Default |
| --- | --- | --- | --- |
| `schema_version` | yes | integer exactly `1` | none |
| `rootfs` | yes | absolute, existing real directory reached through no symlinks | none |
| `argv` | yes | non-empty JSON array of non-empty strings | none |
| `env` | no | string-to-string mapping with valid names | empty mapping |
| `hostname` | no | conservative ASCII hostname label | `"minibox"` |
| `network_mode` | no | `"none"` or `"host"` | `"none"` |
| `timeout_seconds` | no | finite number in `(0, 300]` | `30.0` |

The input schema is closed. `from_dict` must reject a non-mapping top-level
value, missing required fields, and every unknown field. Boolean values do not
count as integers or timeout numbers. A string does not count as an `argv`
sequence. Each argument must be a non-empty string.

Environment names must match this ASCII grammar:

```text
[A-Za-z_][A-Za-z0-9_]*
```

Every environment value must be a string. The implementation must not merge
the caller's host environment into the specification.

The hostname is one lowercase ASCII, DNS-label-like component matching:

```text
[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?
```

It is 1 through 63 characters long, a hyphen may not be first or last, and
uppercase letters are rejected. Minibox does not accept a dotted fully
qualified domain name.

`load_spec` must read one UTF-8 JSON document from a regular, non-symlink file
of at most 1 MiB and pass its decoded object through the same validation as
`from_dict`. It must reject non-finite JSON constants, duplicate object keys,
and trailing non-whitespace data. Invalid JSON, a non-object document, an
unreadable input, or any schema error must become `SpecError`. Valid JSON does
not imply a valid Minibox specification.

The configured `rootfs` and every component from the filesystem root to it
must be real directories rather than symbolic links. This check makes the
input rule deterministic; it does not eliminate later check-to-use races.

Callers must not be able to change an existing `ContainerSpec` by later
mutating the input `argv` or `env` containers.

## 3. Rootfs-confined executable resolution

`minibox.rootfs` must expose:

```python
resolve_executable(spec: ContainerSpec) -> pathlib.Path
```

The function resolves `spec.argv[0]` as a *guest* executable and returns its
host-side path beneath `spec.rootfs`.

- A guest absolute executable such as `/bin/tool` means `bin/tool` beneath the
  configured rootfs. It must never mean the host's `/bin/tool`.
- An executable containing a slash is resolved directly as a guest path.
- A bare executable name is searched using the specification's `PATH` value.
  If `PATH` is absent, the effective fallback is `/bin:/usr/bin`.
- PATH entries are guest locations. Empty, relative, malformed, or hostile
  entries must never cause host-path lookup or escape from the rootfs.
- Reject any candidate containing a `..` path component, even when lexical
  normalization would happen to place the result back inside the rootfs.
  Normal `.` components must never weaken the rootfs boundary.
- Every filesystem component below the rootfs through the final candidate
  must be checked without following symbolic links. Minibox intentionally
  rejects even a symlink whose target would remain inside the rootfs.
- The selected candidate must be an existing regular file with at least one
  executable mode bit set.
- Search order must be stable and follow PATH order. Return the first valid
  candidate.

If no safe executable can be selected, raise `RootfsError`. The resolver must
not execute, open as a program, or modify the candidate. Its confinement checks
are required even when the caller happens to have elevated privileges.

## 4. Deterministic namespace plan

`minibox.plan` must expose:

```python
IsolationPlan
build_plan(
    spec: ContainerSpec,
    *,
    unshare_path="/usr/bin/unshare",
    python_path="/usr/bin/python3",
) -> IsolationPlan
```

`IsolationPlan` has two observable tuple fields:

- `namespaces: tuple[str, ...]`
- `argv: tuple[str, ...]`

The namespace order is deterministic. It begins with:

```text
user, mount, pid, uts, ipc
```

When `network_mode` is `"none"`, append `net`. When it is `"host"`, do not
request a network namespace.

The argument tuple must begin with the supplied `unshare_path`, request the
same namespaces with long options, map the calling user to root *inside the new
user namespace*, and fork for the PID namespace. In order, the fixed prefix is:

```text
UNSHARE --user --map-root-user --mount --pid --fork --uts --ipc
```

Add `--net` only for `network_mode="none"`. The remaining fixed suffix is:

```text
-- PYTHON -m minibox._child
```

where `UNSHARE` and `PYTHON` are the two injected path arguments. Each shown
token is a separate tuple element. No quoting, shell syntax, host probing, or
subprocess execution belongs in `build_plan`.

This object records requested isolation; it is not evidence that the kernel
accepted or enforced the request.

## 5. Atomic lifecycle state

`minibox.state` must expose `ContainerState` and `StateStore`. Construct the
store with a state directory and an optional keyword-only, zero-argument
`clock` callable. The default clock may use wall time; tests can inject a
deterministic one.

The store API is:

```python
store.create(container_id) -> ContainerState
store.get(container_id) -> ContainerState
store.recover(uncertainty) -> ContainerState
store.transition(
    container_id,
    expected,
    target,
    *,
    exit_code=None,
    error=None,
) -> ContainerState
```

`ContainerState` is an immutable value with these attributes:

```text
container_id, status, revision, created_at, updated_at, exit_code, error
```

Container identifiers must match exactly:

```text
^[a-z0-9][a-z0-9_.-]{0,63}$
```

This excludes path separators, uppercase letters, traversal components as an
entire identifier, and identifiers longer than 64 characters.

The only statuses and transitions are:

```text
CREATED -> RUNNING
RUNNING -> EXITED
RUNNING -> FAILED
```

`create` atomically creates a `CREATED` record at revision `0`, sets both
timestamps from the injected clock, and rejects an existing identifier.
`transition` must verify both the expected current status and the legal target,
increment the revision by one, retain `created_at`, and obtain a new
`updated_at` value from the clock. `EXITED` records carry the execution result's
integer exit code. `FAILED` records carry a useful error string. Outcome fields
that do not apply remain `None`.

Invalid identifiers, missing or duplicate records, corrupt records, expectation
mismatches, and illegal transitions must raise `StateError`.

State is persisted as JSON under the configured directory. A reader must see
either the complete previous record or the complete next record, never a
partially written document. Two concurrent transitions with the same expected
state must not both succeed. Temporary files must remain inside the state
directory. A record path that is a symlink or is not a regular file must be
rejected as `StateError`; the store must never read or overwrite a symlink
target as container state.

Publication has two explicit phases. Any failure before the no-overwrite link
used by `create`, or before the atomic replacement used by `transition`, is an
ordinary `StateError` and must not publish the proposed record. After that
atomic publication point, the complete proposed record is already visible. If
the following directory synchronization fails, the operation must raise
`StateCommitUncertain`, not a generic `StateError`. That exception must expose
the exact proposed `ContainerState` as `proposed_state`. A caller must not
blindly retry `create` or `transition`, because doing so can misreport a
successful publication as a duplicate or stale transition.

`recover(uncertainty)` is the recovery protocol. It accepts only a
`StateCommitUncertain` created by a store for the same directory, locks the
identifier, reads the complete visible record, and verifies that it equals
`uncertainty.proposed_state`. It then retries directory synchronization and
returns that record. A missing, different, or superseded record raises
`StateError` without rewriting evidence; another synchronization failure
raises `StateCommitUncertain` again. Recovery after a process or machine crash
therefore requires the controller to reconcile its intended record with the
currently visible record before deciding whether another lifecycle action is
safe.

The contract is atomic visibility and compare-and-transition behavior with an
explicit indeterminate durability outcome. It does not claim distributed
consensus or guaranteed durable commits across machine or filesystem failure.

## 6. Runtime and injectable backend

`minibox.runtime` must expose:

```python
ExecutionResult
Runtime
LinuxSubprocessBackend
```

`ExecutionResult` is a value object with:

```text
exit_code: int
stdout: bytes
stderr: bytes
```

An execution backend provides:

```python
backend.run(spec: ContainerSpec) -> ExecutionResult
```

`Runtime(store, backend).run(spec, container_id)` coordinates one attempt:

1. Create the state record.
2. Transition it from `CREATED` to `RUNNING`.
3. Call the injected backend exactly once.
4. If the backend returns, transition to `EXITED`, recording its exit code,
   and return the same `ExecutionResult`. A nonzero exit code is still an
   ordinary completed execution, not a backend failure.
5. If the backend raises an ordinary exception, transition from `RUNNING` to
   `FAILED` with a useful error string, then re-raise the original exception.

The core runtime must be testable with an in-memory fake backend and must not
inspect the host to decide whether a fake can run. It must not silently retry a
backend or convert payload exit codes into Python exceptions.

## 7. Optional real Linux backend

`LinuxSubprocessBackend` is the extension stage. Its class must be importable on
all test hosts, but construction or execution may report `BackendUnavailable`
when Linux, `unshare`, or required user-namespace features are unavailable.
Other launch or setup failures use `BackendError`, and an enforced deadline
uses `BackendTimeout`. A payload's ordinary nonzero exit remains an
`ExecutionResult`.

Its constructor is:

```python
LinuxSubprocessBackend(
    *,
    unshare_path=None,
    python_path=None,
    max_output_bytes=1_048_576,
)
```

`max_output_bytes` must be a positive integer no greater than `16_777_216`;
booleans are not integers for this setting. Invalid values raise `ValueError`.
Apply the limit independently to stdout and stderr. If a stream exceeds it,
retain its first
`max_output_bytes` bytes and append this exact marker:

```python
b"\n[minibox: output truncated]\n"
```

The returned stream may therefore be longer than the configured content limit
by the marker length. When `unshare_path` is `None`, locate `unshare` with
`shutil.which("unshare")`; when `python_path` is `None`, use `sys.executable`.
Explicit arguments allow tests and unusual installations to select both
executables. Before launch, the backend must require both resolved paths to be
absolute executable regular files; otherwise it raises `BackendUnavailable`.

A completed extension should:

- use `resolve_executable` and `build_plan` rather than duplicate their policy;
- launch only an argument vector, never a shell command;
- enforce `timeout_seconds`, capture stdout and stderr as bytes, and clean up
  the started process group after timeout;
- distinguish backend/setup failure from a payload's nonzero exit status;
- refuse to continue if requested isolation cannot be established; and
- avoid requiring or recommending execution as root.

The child-side setup needed for meaningful filesystem isolation is intentionally
left as design work. Passing the deterministic unit tests is not proof that a
real payload is confined. Run integration experiments only when explicitly
opted in on a disposable Linux host.

`minibox.cli` and the private `minibox._child` wire format are extension
surfaces, not additional stable public APIs. A learner may choose their
argument and message details, provided the backend behavior above is met and
the helper rejects malformed input at its privilege boundary.

## 8. Verification

All public tests use `unittest`. From the repository root, run:

```bash
python3 -c 'import sys; print(sys.version.split()[0]); raise SystemExit(0 if sys.version_info >= (3, 10) else 1)'
PYTHONPATH=starter python3 -m unittest discover -s public_tests -v
```

Core tests must be deterministic and must use temporary root filesystems,
temporary state directories, injected clocks, and fake backends. They must not
depend on root privileges, a working `unshare`, the host network, or a Docker
daemon.
