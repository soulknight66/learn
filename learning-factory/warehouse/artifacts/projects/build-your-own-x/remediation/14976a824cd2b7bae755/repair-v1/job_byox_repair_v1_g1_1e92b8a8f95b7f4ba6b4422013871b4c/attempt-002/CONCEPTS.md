# Concepts: from process to container

A container is not a special kind of executable. It is an ordinary Linux process observed through a
carefully assembled set of kernel boundaries. MiniCTR separates that kernel-facing data plane from a
small durable control plane so you can reason about both.

## Threat model and trust boundaries

MiniCTR assumes the invoking user, the host administrator, the runtime state root, and the supplied
rootfs are within one educational trust boundary. CLI arguments, metadata bytes, child status, and
concurrent invocations are still treated as untrusted data: they must not become shell syntax, escape
the selected state tree, or bypass lifecycle exclusion.

The exercise does not claim containment of a malicious rootfs or hostile local administrator. It also
omits cgroups, seccomp, comprehensive capability removal, image verification, device policy, and an
authenticated privileged service. Namespace setup must fail closed, but a successful teaching probe
is not evidence of production multi-tenant security.

## A useful mental model

Think of one `run` operation as four layers:

| Layer | Question it answers | MiniCTR concern |
| --- | --- | --- |
| Registration | What configuration did the user name? | durable name-to-rootfs state |
| Lifecycle | May this instance start or be deleted now? | locks, PID identity, cleanup |
| Isolation | Which kernel objects does the process see? | namespaces, mounts, apparent root |
| Execution | What program and arguments run? | exact argv, stdio, signals, exit status |

Failures at one layer should not corrupt another. A missing namespace feature is a run failure, not a
reason to lose the registration. A stale lifecycle marker should not silently bypass isolation.

## Root filesystems are not process isolation

A root filesystem is a directory tree containing a program, its loader, libraries, configuration, and
any files it expects. Changing a process’s apparent root alters pathname resolution, but it does not by
itself isolate PIDs, hostnames, networking, IPC objects, mounts, credentials, memory, or CPU.

`chroot` is therefore one ingredient, not a security boundary on its own. Its behavior also depends on
open file descriptors, the process’s working directory, capabilities, and the mount tree. A runtime
must establish the surrounding namespace rules before treating the new root as meaningful.

Dynamic executables need their ELF interpreter and shared libraries inside the rootfs. A copied binary
that reports “not found” can exist at the requested path while its loader is absent. This is one reason
the exercise does not pretend that a directory with one arbitrary host binary is a portable image.

## Namespace roles

Linux namespaces virtualize different views. No single namespace makes a complete container.

| Namespace | View separated from the host | Typical observable effect |
| --- | --- | --- |
| user | user/group IDs and capabilities | apparent root can map to an unprivileged host user |
| mount | mount table and propagation relationships | container mounts need not appear on the host |
| PID | process identifiers and ancestry | the first child appears as PID 1 inside |
| UTS | hostname and domain name | changes need not rename the host |
| IPC | System V IPC and POSIX message queues | IPC identifiers are not shared |
| network | interfaces, routes, sockets, firewall view | the instance starts with its own network view |

Namespace creation can fail despite the relevant utilities being installed. Kernels and hosting
platforms can disable user namespaces, limit namespace counts, filter system calls, or withhold the
capabilities needed by a particular sequence.

## User namespaces and “root”

A user namespace can map the invoking host UID to UID 0 inside the namespace. That namespaced root has
capabilities over resources governed by that namespace; it is not automatically host root. The mapping
is what lets some mount and `chroot` operations work without `sudo`.

This is a reduced privilege boundary, not magic. Kernel vulnerabilities, externally supplied file
descriptors, unsafe host mounts, and incorrect ownership mappings remain relevant. A correct toy
runtime fails if the mapping cannot be established instead of retrying without isolation.

## Mount namespaces and propagation

A new mount namespace begins as a copy of a mount view. Mounts can still have propagation relationships
with mounts in another namespace. If the relevant tree is shared, a mount made “inside” can propagate
outside. Container setup therefore has to reason about both namespace membership and propagation mode.

The proc filesystem is also view-sensitive. Reusing the host’s `/proc` after entering a PID namespace
can expose the wrong process view. A proc mount associated with the new PID namespace belongs inside the
isolated mount namespace and the selected rootfs.

Mount teardown should be designed before mount setup. Namespace destruction normally removes private
mounts, but error paths, helper processes, and propagation mistakes can make cleanup assumptions false.

## PID 1 is different

The first process in a PID namespace has PID 1 in that namespace. Linux treats it specially for signal
delivery, and it inherits orphaned descendants. A general container init needs to forward signals and
reap children. MiniCTR runs one foreground command, but you should still ask what happens when that
command forks, ignores a signal, or exits before its descendants.

The PID printed by `minictr ps` is host-visible lifecycle information. It is not necessarily the same
number observed by the command inside its namespace.

## Durable state versus liveness

A registration is durable: it should still exist after the CLI process that created it exits. Running
is transient: it depends on a particular live process. Mixing those facts in one unchecked file leads
to classic bugs:

- a crash leaves “running” forever;
- a PID is reused by an unrelated host process;
- two launches both observe idle and proceed;
- delete races between validation and launch; or
- a reader sees a partially written record.

A PID alone is a weak identity because the kernel reuses numbers. On Linux, a process start token from
`/proc` can help distinguish the process originally recorded from a later process with the same PID.
A matching token is still not sufficient when the process is a zombie or dead task: `Z` and `X`
states can no longer supervise a workload and must be treated as stale. Whichever representation you
choose, make the state transition atomic and define recovery from stale transient state.

The state tree must also be disjoint from every registered rootfs. If state is placed inside a rootfs,
ordinary registration writes mutate the filesystem being registered and the isolated command can see
control-plane metadata. If a rootfs is placed inside state, lifecycle cleanup and state maintenance can
accidentally cross the filesystem boundary. Compare canonical prospective paths before creating state,
including when the requested state directory does not yet exist.

## Locks protect decisions, not just writes

Atomic rename prevents a reader from seeing half a metadata file, but it does not make a multi-step
decision atomic. “Check idle, then write running” races unless competing operations share an exclusion
mechanism. The protected region must include the observations that justify a state change.

Shell offers filesystem primitives that can be used as atomic lock attempts, but every lock design must
also address ownership, stale locks, bounded waiting, and cleanup after signals. Avoid assuming that
“the commands usually run quickly” removes the race.

## Arguments are already structured data

The shell that starts MiniCTR has already parsed quotes and produced an argv vector. For example, one
argument may contain spaces, wildcard characters, a semicolon, or an empty string. Joining that vector
into text and passing it through another shell loses information and may execute data as code.

Bash arrays and quoted `"$@"`-style expansion preserve argument boundaries. Metadata has the same rule:
read a path as data rather than sourcing a file whose contents happen to resemble assignments.

## Signals, status, and cleanup

For a foreground runtime, the child’s streams and outcome form part of the API. A wrapper that changes
exit 23 to exit 1, swallows standard error, or leaves a running marker behind has changed observable
program behavior.

Signal handling creates ordering questions. The wrapper may need to remember a child PID, forward a
signal, wait for termination, remove transient state, and then return a conventional status. Traps can
run while an operation is only partially initialized, so cleanup should be idempotent and narrowly
scoped.

Supervisor defaults matter. In particular, util-linux `unshare --kill-child` defaults to `SIGKILL`,
which changes a wrapper's `TERM` into an uncatchable signal at the payload. The required design chooses
`--kill-child=TERM`, gives the payload a bounded TERM grace period, and reserves KILL for escalation.

## The fake isolator is a test boundary

Lifecycle logic should not require kernel privileges to test. `MINICTR_ISOLATOR` replaces only the
isolation layer with an executable that accepts the rootfs followed by the exact user command argv. A
fake can capture arguments, return a selected status, or pause while another CLI process calls `ps` and
`delete`.

Passing those tests means the control plane honored its contract. It says nothing about whether the
default isolator created the required namespaces. Keep those claims and test layers separate.

## What this project intentionally omits

Production runtimes also handle image formats, overlay filesystems, cgroups, seccomp profiles,
capability sets, device policy, LSM labels, rootless networking, terminal allocation, logging,
checkpointing, OCI bundles, and daemon recovery. MiniCTR provides a small surface for learning the
underlying mechanisms; it is not a substitute for those systems.
