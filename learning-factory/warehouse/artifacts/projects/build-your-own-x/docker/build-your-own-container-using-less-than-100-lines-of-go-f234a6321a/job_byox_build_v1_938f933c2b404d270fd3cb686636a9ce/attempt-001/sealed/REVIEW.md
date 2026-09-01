# Reference review

## What the implementation establishes

- Validation rejects the host root, an unclean or symlink root path, malformed hostnames, relative
  executables, NUL bytes, and duplicate environment names.
- Planning is side-effect free and exposes the exact clone flags and identity maps.
- Re-execution uses argv slices and a fixed internal setup-error descriptor.
- The parent closes its copy of the descriptor immediately after start and bounds the diagnostic
  read. The child marks it close-on-exec before any setup operation.
- Filesystem operations stop at the first error. The workload is never attempted after a failed
  private mount, bind mount, hostname, chroot, chdir, or proc mount.
- Workload status is preserved, including conventional signal status on Linux.

## Important findings that remain open

1. **High: pathname race.** `Lstat` and later `mount`/`chroot` resolve paths separately. A process
   that can mutate the rootfs or ancestors can substitute objects between checks. Production code
   should pin descriptors and use race-resistant resolution/mount APIs.
2. **High: capabilities not bounded.** Namespace root retains broad namespace-scoped capabilities.
   There is no capability bounding, securebits setup, `no_new_privs`, seccomp, or LSM profile.
3. **High: no resource controls.** A workload can exhaust processes, memory, CPU, or I/O subject only
   to host-wide policy because no cgroup or rlimit contract exists.
4. **Medium: PID 1 behavior.** The workload must reap orphans and deliberately handle signals. A
   retained init is safer for general commands.
5. **Medium: inherited descriptors.** The Go process may inherit caller descriptors beyond standard
   I/O. The launcher does not enumerate and close all unintended descriptors.
6. **Medium: writable rootfs.** The root is bind-mounted read-write with no masked paths, device
   policy, or separate writable layer.
7. **Medium: cancellation scope.** Killing namespace PID 1 normally tears down that PID namespace,
   but cancellation and kernel-policy behavior need integration stress tests.
8. **Low: diagnostic channel format.** It is bounded text rather than a versioned structured record;
   callers cannot classify individual setup phases without matching prose.

## Verdict

The code is suitable as a compact teaching reference for namespace creation and filesystem setup. It
is explicitly not approved for adversarial isolation or production deployment. The manifest must
remain `productionized: false`.
