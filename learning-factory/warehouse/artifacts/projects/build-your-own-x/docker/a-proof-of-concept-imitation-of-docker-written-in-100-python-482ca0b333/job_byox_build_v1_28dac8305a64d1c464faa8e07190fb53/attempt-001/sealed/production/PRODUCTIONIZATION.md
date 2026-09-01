# Productionization assessment

MiniBox is explicitly **not productionized**. Moving beyond an educational proof of concept requires a smaller privileged component and a much larger validation program.

Required engineering work includes:

1. Replace path-based extraction with descriptor-relative operations using `openat2` resolution constraints, link-safe semantics, quotas, transactional snapshots, and digest verification.
2. Implement a crash-recoverable operation journal that reconciles SQLite state, mounts, processes, cgroups, staging directories, and published rootfs trees.
3. Use an OCI-compatible runtime or a narrowly reviewed native helper for clone/mount/pivot-root/UID-map operations; validate exact kernel and util-linux feature versions.
4. Configure cgroup v2 limits, capability bounding, `no_new_privs`, seccomp, masked paths, read-only mounts, LSM profiles, and safe device policy before executing payload code.
5. Add a PID-1 init/reaper, signal forwarding, log rotation with disk quotas, cancellation, health checks, and durable exit reporting.
6. Design network namespaces, loopback state, veth ownership, firewall policy, DNS injection, and cleanup without exposing host networking by default.
7. Authenticate callers and images, verify signatures and digests, protect the control socket, define authorization, and prevent secret inheritance.
8. Add recovery, concurrency, power-loss, filesystem-fault, decompression-bomb, syscall-fuzzing, and multiple-kernel integration suites. Run them in disposable virtual machines, not a developer host.
9. Add structured audit records, metrics, trace correlation, compatibility matrices, release signing, incident response, and an independently reviewed threat model.

The current archive and state unit tests are useful evidence for their narrow contracts only. They are not evidence for kernel isolation, security, scale, or operational readiness.
