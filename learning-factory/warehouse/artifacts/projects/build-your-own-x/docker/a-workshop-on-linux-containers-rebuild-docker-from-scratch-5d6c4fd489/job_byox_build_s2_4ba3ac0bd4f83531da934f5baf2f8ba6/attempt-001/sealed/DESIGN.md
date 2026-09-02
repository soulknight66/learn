# Sealed design answers

1. `chroot` changes one process's path lookup root but does not create a new mount table. Existing
   descriptors, unsafe privilege, mutable shared mounts, and incorrectly arranged mount propagation
   can retain access or affect the host. A private mount namespace must precede rootfs mounts.

2. The host validates input and rootfs, then `unshare` establishes user mapping plus mount, UTS, IPC,
   PID, and optional network namespaces. `unshare --fork` creates the namespace child. The
   already-imported helper marks propagation private, bind-mounts and optionally remounts the rootfs
   read-only, mounts procfs at `<rootfs>/proc`, sets the UTS hostname, calls `chroot`, changes to `/`,
   constructs a minimal environment, and directly execs the workload.

3. String prefixes ignore path components: `/srv/root-other/x` starts with `/srv/root`. A path such
   as `/srv/root/jump/x` may also traverse an existing `jump -> /outside` symlink. Canonicalize and
   use `relative_to` for the educational check.

4. An attacker can rename a checked component or replace it with a symlink between resolution and
   use. A hardened implementation pins the root directory descriptor and walks with `openat2` using
   `RESOLVE_BENEATH | RESOLVE_NO_MAGICLINKS` (and an intentional symlink policy), then performs
   descriptor-relative mounts or uses newer mount APIs.

5. `network: false` must fail closed by creating a fresh network namespace. Sharing host networking
   would make a flag that appears restrictive do the opposite. `network: true` in this limited model
   means “do not request separation,” not “configured container networking.”

6. Namespace PID 1 must reap orphans and deliberately forward/handle signals. The reference relies
   on util-linux supervision for a bounded workshop, but that is not a full init contract. A real
   runtime supplies and tests a small init shim.

7. Without a write-locking transaction, two launchers can both observe `CREATED`, start distinct
   processes, and then each record itself as owner. `BEGIN IMMEDIATE` acquires the writer position
   before the conditional update; row count makes the losing claim explicit.

8. Fixed, nonsensitive control switches belong in argv. A minimal import environment belongs in the
   helper environment. Canonical validated workload configuration is bounded and sent over stdin so
   command/environment values are not exposed in the launch argv. Durable state records canonical
   spec, ownership, terminal code, log location, and caller-supplied timestamps, but secret handling
   would require a separate design.

9. Killing only the immediate launcher can leave a forked namespace child or descendants alive.
   Starting a session and killing its process group gives the supervisor one cleanup target. Cgroups
   would be a stronger workload-membership boundary in production.

10. Major gaps are verified rootfs acquisition, descriptor-race-safe filesystem setup, capability
    minimization, seccomp/LSM policy, cgroup resource and kill semantics, a real init shim, safe
    networking, bounded persistent logging, and extensive kernel-version integration tests. For
    hostile workloads, capability/seccomp/filesystem and resource containment are all blockers.
