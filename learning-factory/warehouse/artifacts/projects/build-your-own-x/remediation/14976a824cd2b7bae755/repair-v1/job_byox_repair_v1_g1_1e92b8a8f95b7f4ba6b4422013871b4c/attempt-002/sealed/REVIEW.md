# Sealed implementation review

## Review scope

This review evaluates the reference design and implementation against the
educational contract: deterministic state handling, path containment, exact
argv flow, lifecycle evidence, and testability without privileged namespace
operations. It is not a penetration-test report and does not award validation
labels. Commands and observed results belong in `VALIDATION.md` and require
independent validation.

## What the architecture gets right

- CLI dispatch is a closed set with explicit arity and stable stderr errors.
- Names are validated as ASCII under the C locale before state-path
  construction, closing traversal, option-injection, and locale-stranding routes.
- Rootfs values are absolute, canonical, existing, line-safe, and cannot name
  the host root.
- Prospective state paths are parsed without temporary shell input and resolved
  before creation; either-direction state/rootfs overlap is rejected before
  registration can mutate the rootfs even when `TMPDIR` is unusable.
- The isolator receives a real argv vector. There is no command-string or
  `eval` boundary, so empty, whitespace, glob, and metacharacter arguments can
  remain data.
- Create uses an atomic ownership step rather than a check-then-create claim;
  metadata publication uses exclusive noclobber creation so a planted symlink
  is not followed.
- Run state carries process-start identity in addition to PID and rejects
  zombie/dead process states, reducing stale PID-file false positives.
- Run cleanup is tied to record ownership, and delete shares coordination with
  lifecycle mutation.
- Signal teardown verifies both helper PID and process-start token, applies a
  bounded TERM-to-KILL sequence, configures unshare to preserve TERM at the
  payload, and reaps the helper before clearing state.
- `ps` has a fixed schema and C-locale ordering rather than filesystem order.
- The injection seam permits deterministic rootless tests of output, status,
  argv, races, and state transitions.

## Residual correctness risks

### Crash consistency

Filesystem atomicity is narrower than durability. A directory or renamed file
can be visible before its data and parent-directory metadata are forced to
stable storage. Abrupt host failure can therefore leave partial or stale state.
The educational runtime should detect malformed records and fail closed, but it
does not implement a write-ahead log, directory `fsync`, or a recovery journal.

### Shell signal semantics

There are unavoidable races between run-record publication, helper start, trap
installation, signal delivery, wait, and owner-checked cleanup. Tests can make
ordinary interleavings deterministic, but exhaustive signal correctness is
not credible in a small shell script. A persistent supervisor using pidfds and
structured cancellation would be stronger.

### Lock-owner recovery

Coordination uses atomic lock directories with a bounded acquisition wait, but
the lock directory carries no owner identity or lease. Normal return paths
remove it; an uncatchable termination between acquisition and unlock can leave
it behind and wedge later operations for that name. Automated removal based
only on age would be unsafe. A supervisor-backed lock or a transactional state
store with recoverable ownership is needed for robust crash recovery.

### Host-path replacement

Canonicalizing a rootfs at create time does not pin an inode. A privileged host
actor can replace or remount that path before run. This project assumes its
host and state administrator are trusted; a stronger design would open and
verify filesystem handles in the privileged helper.

### State-root trust

`MINICTR_HOME` and its ancestors must not be attacker-controlled. Symlink or
permission attacks on a shared state tree exceed the simple path checks. A
service should create a fixed root owned by a dedicated account, verify every
component, reject links, and use descriptor-relative filesystem operations.

## Security limitations

The default adapter demonstrates namespaces and a changed root. It does not
provide a production container security profile. In particular, the reference
scope omits comprehensive user-namespace mapping, capability bounding, seccomp,
LSM policy, cgroups, device policy, verified images, read-only mounts,
networking policy, secret handling, and audit integration. Chroot is not an
independent security boundary. Root inside an inadequately configured runtime
can remain root on the host.

Executable override variables are a testing seam, not a privileged-service
API. A caller who can control them can choose host programs to execute. Any
future privileged frontend must discard caller environment, use fixed absolute
tool paths, authenticate requests, and communicate through a constrained
protocol.

## Review disposition

The implementation is suitable as an independently validated learning
artifact if its deterministic tests pass on the target host and environmental
namespace blockers are reported honestly. It should remain labeled partial
and not productionized. The gaps above are architectural, not polish items;
production use should build on a mature runtime rather than incrementally add
privilege to this shell program.
