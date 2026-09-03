# Concepts

## A container is coordinated isolation

A Linux container is not one kernel object. It is an ordinary process started with a coordinated
set of namespace membership, credentials, mounts, resource policy, and lifecycle supervision. If
one boundary is set up in the wrong order, another can become meaningless.

## Namespace roles

- **User** maps a process to UID 0 *inside* a namespace without making it host root. Its creation and
  mapping order govern which later mount operations are permitted.
- **Mount** provides a private mount table. A chroot alone only changes path lookup; it neither makes
  mounts private nor prevents all escapes by a privileged process.
- **UTS** separates hostname and domain name.
- **IPC** separates System V IPC and POSIX message-queue views.
- **PID** gives descendants a new process-number view. The first child becomes PID 1 there and must
  reap orphans and handle signals deliberately.
- **Network** separates devices, routes, ports, and firewall context. This exercise creates the
  namespace when networking is disabled; configuring useful connectivity is out of scope.

Namespaces isolate *views*, not resource consumption. Cgroups, seccomp, capability dropping, and
LSM policy solve different problems and are absent from the starter.

## Root filesystem and path resolution

Changing root gives a process a new `/`, but safe setup begins before the change. Host-side paths
derived from guest input need component-aware containment. `resolve()` catches existing symlink
escapes in a single-threaded exercise, while a production implementation should walk with
`openat2(2)` constraints or pinned directory descriptors to resist rename races.

Mount `/proc` only after the PID namespace is selected, and place it beneath the intended rootfs.
Otherwise process listings can expose the host PID view or the mount can land in the host namespace.

Kernel permissions and backing filesystems differ. A setup-only helper can exercise the exact user,
mount, UTS, IPC, PID, network, bind, remount, proc, hostname, and chroot path without execing the
workload. Run it immediately before execution and abort on failure. It is a capability signal, not a
lasting reservation: host policy or the rootfs can still change before the real helper starts.

## The namespace PID 1 problem

PID 1 has special signal behavior and owns orphan reaping. Simply executing an arbitrary workload
as PID 1 can leak zombies or ignore termination assumptions. This exercise uses `unshare --fork`
and kill-child supervision as a teaching-scale compromise. A production runtime needs a deliberate
init shim and signal-forwarding protocol.

## Deterministic state around nondeterministic work

The kernel launch can fail for policy, filesystem, executable, or workload reasons. Durable state
must not depend on a worker's prose. An atomic `CREATED -> RUNNING` claim establishes one owner;
the exit code determines the terminal state, and evidence survives failure. SQLite's
`BEGIN IMMEDIATE` serializes competing writers before either can claim the same row.

## Threat model

The intended workload is a learner-owned executable in a learner-created rootfs. The implementation
must reject malformed configuration and avoid shell injection, host-path traversal, duplicate
launches, and runaway test processes. It is not designed to contain hostile code. Missing seccomp,
capability minimization, cgroups, verified image extraction, race-free path APIs, and audited init
behavior are explicit security gaps.

## Progressive disclosure is an artifact boundary

An answer directory in the same readable checkout is disclosed even if instructions call it
sealed. This pack therefore exports an allowlisted learner tree separately from the complete
instructor tree. A generated manifest records every directory and every payload file's path, size,
and digest; an externally retained digest binds that manifest. This controls distribution, not the
trustworthiness of learner changes after handoff.
