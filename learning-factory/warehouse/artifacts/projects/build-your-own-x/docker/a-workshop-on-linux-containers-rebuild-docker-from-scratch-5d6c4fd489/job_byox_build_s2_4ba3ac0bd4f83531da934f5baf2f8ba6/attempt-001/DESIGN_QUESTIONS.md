# Design questions

Write down your answers before opening each stage. These are assessed on reasoning as well as code.

1. Why does `chroot` without a private mount namespace fail to define a complete filesystem
   boundary? Which privileges make that especially dangerous?
2. In what order should user, mount, PID, proc-mount, and chroot setup occur? Identify which process
   performs each step.
3. Why is checking `str(candidate).startswith(str(root))` unsound? Give both a sibling-prefix and a
   symlink example.
4. What remains racy after `Path.resolve()` containment succeeds? Sketch a descriptor-relative
   design that closes the gap.
5. Should `network: false` mean “share the host network” or “create an empty network namespace”?
   How does fail-closed behavior influence the choice?
6. What must a namespace PID 1 do with signals and orphaned children? Is `unshare --fork` enough for
   a production runtime?
7. Why must a lifecycle claim and state update be one database transaction? What concrete history
   can two nonatomic launchers produce?
8. Which information belongs in argv, environment, stdin, and durable state? Consider observability,
   size limits, secret exposure, and reproducibility.
9. After a timeout, why kill a process group rather than only the immediate `unshare` process?
10. Which missing controls prevent this workshop runtime from being a security boundary for hostile
    workloads? Rank them for your intended threat model.
