# Concepts

## A container is several mechanisms composed

A container is not one kernel object. Production runtimes combine filesystem views, namespace
membership, resource accounting, credentials/capabilities, syscall policy, networking, and a process
lifecycle. PyDocklet implements a portable model of only a few control-plane pieces. Its directory
and environment isolation are useful organization, not an adversarial boundary.

## Images, layers, and snapshots

An image can be represented as an ordered list of immutable tar layers. Applying a later regular
file replaces the earlier path. A whiteout removes a lower-layer path; an opaque marker hides all
older children of one directory. The order is meaningful, so a content identifier must commit to
both each layer's bytes and their sequence.

Archive extraction crosses a trust boundary. A name such as `../../outside`, an absolute path, a
symbolic link followed by a later file, or a device node can turn “unpack here” into host mutation.
Secure extraction validates all metadata first, resolves paths structurally, rejects unsupported
types, and copies bytes itself under strict quotas.

## Lifecycle as durable state

Filesystem directories alone do not answer whether a container may start. A durable record separates
`CREATED`, `RUNNING`, and `EXITED`. The start operation is a claim: concurrent callers must not both
observe `CREATED` and launch. SQLite's `BEGIN IMMEDIATE`, a constrained transition graph, and a
database trigger make that invariant deterministic across processes.

There is still a crash window between committing `RUNNING` and launching or recording `EXITED`.
Production systems use leases, supervisors, reconciliation, and durable execution evidence to
resolve that ambiguity. Recognizing the window is part of the lesson.

## Process execution versus process isolation

An argv array avoids shell interpretation; a fresh process group lets a timeout terminate descendants;
a controlled environment reduces ambient input; a dedicated current directory organizes files; and
file-backed capture avoids unbounded RAM use. None prevents a process from opening host absolute
paths, making network calls, or using all CPU and memory.

Linux PID, mount, user, UTS, IPC, and network namespaces change which global resources a process can
see. Cgroups account for and limit resources. Capability sets and seccomp reduce authority. A robust
runtime composes these in a carefully ordered privileged helper and treats cleanup as part of the
security design. Python APIs alone do not make that composition portable or safe.

## Determinism and evidence

Content digests are deterministic only if they hash stable bytes in a defined order. Runtime IDs can
be deterministic within one database without pretending executions themselves are reproducible.
Hashing a caller-owned file and reopening it later is not stable: import must hash while copying to
private staging and apply that same staged byte stream. Likewise, a content-addressed published tree
needs both read-only modes and integrity verification before reuse; a digest-shaped directory name
does not make mutable bytes immutable.
Exit status, bounded stdout/stderr, and final state are evidence; a prose message saying “it ran” is
not. Likewise, this challenge's validation log describes local observations while independent
validators decide final labels.
