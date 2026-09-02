# Concepts

## A container is an arrangement, not one kernel object

A container runtime combines several mechanisms. Namespaces change what a process can see; a root
filesystem changes path resolution; lifecycle code tracks what should be allowed next. None of these
alone is “a container.” Tinybox keeps the controller separate from the runner so this boundary is
visible.

## PID namespaces and process isolation

A process in a new PID namespace sees a different process-numbering tree. The first process becomes
PID 1 in that namespace and inherits special responsibility for orphaned children and signals.
`unshare --fork --pid` is needed because namespace membership applies to children; merely invoking
`unshare --pid` without creating a child does not put the calling process into the new PID view.

A separately mounted `/proc` matters: process tools derive their view from that filesystem. A PID
namespace paired with the host's `/proc` leaks a misleading host process view.

## Mount and root filesystems

Changing root affects pathname lookup, while a mount namespace isolates mount-table changes. They
solve different problems. Tinybox makes a full copy of the supplied tree to emphasize filesystem
ownership and reproducibility. Real runtimes use content-addressed layers, copy-on-write mounts, and
careful image unpacking to avoid that cost.

`chroot` is not a complete security boundary. A credible hostile-workload runtime must additionally
reason about capabilities, open file descriptors, devices, mount propagation, syscall filtering,
cgroups, and many other surfaces.

## User, UTS, and IPC namespaces

A user namespace can map an unprivileged caller to UID 0 *inside* the namespace without granting
host-wide root. Whether unprivileged mappings are allowed is controlled by the host. A UTS namespace
isolates hostname state. An IPC namespace isolates System V IPC and POSIX message queues.

## State is part of correctness

The kernel does not maintain Tinybox's desired lifecycle. The controller must ensure two creates do
not both publish one name, a delete cannot race a run, and observers never read half-written status.
Atomic directory creation supplies exclusion; write-plus-rename supplies atomic metadata updates.
This remains a deliberately small local protocol, not a crash-proof database.

## Argument boundaries are a security property

The command `printf '%s\n' 'two words'` contains separate values. Flattening it into a string and
re-parsing it changes meaning and may turn data into syntax. Bash arrays and `"$@"` preserve the
boundary all the way into `exec`.
