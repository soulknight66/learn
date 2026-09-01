# Reference implementation

`minictr` is a Bash lifecycle tool backed by a Linux namespace/chroot helper.
It implements the challenge contract:

```text
minictr create NAME ROOTFS
minictr run NAME COMMAND [ARG...]
minictr ps
minictr delete NAME
```

Set `MINICTR_HOME` to an absolute state directory. `create` records only a
canonical rootfs path. `run` invokes `lib/isolate.sh` with every command
argument preserved as a separate argv entry. The helper creates user, mount,
PID, UTS, IPC, and network namespaces, makes mounts private, mounts a restricted
`proc`, clears the host environment, and enters the rootfs with `chroot`.

The rootfs must be an absolute directory other than `/`, contain a real `proc/`
directory, and contain the requested executable plus its runtime dependencies.
The physical rootfs and state directory trees must be disjoint; `create` checks
this before creating state so registration never writes inside a rootfs.
Kernel policy can disable unprivileged user or network namespaces; this is an
explicit portability limit, not silently weakened isolation.

For deterministic tests only, `MINICTR_ISOLATOR` may name one executable that
accepts `ROOTFS COMMAND [ARG...]`. The namespace helper also supports
single-executable overrides `MINICTR_UNSHARE_BIN`, `MINICTR_MOUNT_BIN`,
`MINICTR_CHROOT_BIN`, and `MINICTR_ENV_BIN`. Values are never evaluated as shell
text.

This is an educational runtime, not a security boundary for hostile rootfs
images. It does not implement image acquisition, overlay filesystems, cgroups,
capability/seccomp/LSM policy, UID maps beyond the invoking user, or networking.
The CLI forwards signals to its direct isolation helper, and util-linux
`unshare --kill-child` supervises the namespaced payload, but the generic test
hook does not provide complete descendant/process-group supervision.
The overall artifact therefore remains `GENERATED` + `PARTIAL` pending
independent validation.
