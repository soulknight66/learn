# Design answers

1. **Mount propagation first.** A new mount namespace initially copies propagation relationships.
   Marking `/` recursively private before new mounts prevents changes from traveling through shared
   peer groups into another namespace.
2. **PID namespace timing.** The caller remains in its current PID namespace; the first child made
   with `CLONE_NEWPID` becomes PID 1 in the new namespace. Its descendants see that PID hierarchy.
3. **Mapped root.** Mapping host UID 1000 to container UID 0 enables namespace-scoped capabilities
   needed for setup without making UID 1000 global root. It does not make kernel bugs, exposed host
   files, or resources outside namespace ownership safe.
4. **Internal marker.** An argv marker is explicit, local to the process creation request, and can be
   encoded without inheriting mutable ambient state. An environment switch is easier to trigger
   accidentally and may be inherited into unrelated child processes.
5. **Races.** Every pathname-based check can become stale before bind mount or chroot. An attacker
   able to rename directories or change intermediate symlinks can invalidate earlier observations.
6. **Exit categories.** Once `exec` succeeds, preserve the workload status (or `128 + signal`). Before
   that point, report a runtime setup error. The reference uses a close-on-exec pipe to distinguish
   those phases.
7. **PID 1 duties.** PID 1 has special default signal behavior and must reap orphaned descendants.
   This exercise execs the workload as PID 1, so workloads that fork need to handle both concerns or
   be placed behind a small init.
8. **Unconfigured network.** A new network namespace has its own down loopback device and no routes,
   addresses, veth peer, or DNS setup. Isolation exists, but useful connectivity does not.
9. **Untrusted workloads.** Add cgroup limits, a seccomp allowlist, capability bounding, LSM policy,
   `no_new_privs`, read-only/masked mounts, controlled devices, verified rootfs acquisition, robust
   init/signal handling, and race-resistant descriptor-based path resolution.
10. **`pivot_root`.** The new root must be a mountpoint, an old-root directory is needed, the process
    changes root and working directory, then detaches and removes the old root. Each failure needs a
    safe abort path in the private namespace.
11. **Fresh proc.** Procfs renders the PID namespace associated with the mounting process. Reusing a
    host proc mount can reveal a view associated with the wrong PID namespace.
12. **Signal tests.** Inject a process-launch abstraction for unit tests and assert argv, attributes,
    cancellation, and status mapping there. Reserve real namespace behavior for opt-in integration
    tests on a disposable host.

The reference makes planning inspectable with `LaunchPlan`, isolates platform code with build tags,
and gives the child exactly one fixed setup-error descriptor. It does not serialize secrets into the
setup pipe and bounds parent reads to prevent an unbounded diagnostic allocation.
