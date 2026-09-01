# Namespace-order analysis

The fake backend proves only that a plan was constructed. It cannot prove which kernel namespace the
helper or its mounts actually occupy.

The intended process sequence is:

1. the caller supplies a validated spec; the controller records `CREATED` then `RUNNING` and invokes
   the backend, which resolves the command inside the rootfs;
2. the backend starts `unshare` with the canonical namespace tuple `user, mount, pid, uts, ipc`, plus
   `net` for mode `none`; the argv uses `--map-root-user` and `--fork` for PID-namespace semantics;
3. the resulting child starts the helper inside those namespaces;
4. the helper makes mount propagation private before creating any mount, sets the hostname, drops
   supplementary groups when permitted, sets namespace-root gid/uid, enters the rootfs with `chroot`
   and `chdir("/")`, mounts a hardened proc filesystem at `/proc`, enables `no_new_privs`, and
   reports `READY` over a close-on-exec descriptor immediately before it `exec`s the target; and
5. the controller captures the result or failure, cleans up the process group, and performs the one
   legal terminal state transition. A helper setup or exec failure reports `ERROR`; no readiness
   marker means the launcher failed. Either case becomes `FAILED`, while a ready target's returned
   status, including 125, becomes `EXITED`.

Mounting proc before the new mount/PID namespace, or bind-mounting the host's proc tree into the
rootfs, gives the wrong process view and risks host-visible mount effects. Omitting the fork associated
with PID namespace creation leaves the invoking process outside the new PID namespace. Making mount
propagation private must precede helper mounts. The proc mount must occur after entry into the target
root so `/proc` names the rootfs mount point.

A real integration test should compare namespace links such as `/proc/self/ns/pid`, `mnt`, and `uts`
between host and target; assert the target sees its expected PID-namespace view; assert its hostname
without changing the host hostname; and verify after exit that no rootfs proc mount remains. These
checks need a disposable privileged runner and feature-based skips. Checking only that `--pid` or
`--mount` appears in a plan would reproduce the inadequate fake-backend test.
