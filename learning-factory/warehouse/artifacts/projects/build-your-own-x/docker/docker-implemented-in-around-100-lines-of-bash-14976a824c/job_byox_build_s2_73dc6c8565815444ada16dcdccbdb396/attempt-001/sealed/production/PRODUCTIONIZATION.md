# Productionization assessment

Status: **not productionized**.

The generated implementation has not passed a production security review, cross-kernel integration
matrix, fault-injection campaign, performance qualification, or independent validation. The host's
real user-namespace capability is recorded in `VALIDATION.md`; even support there would not change
this status.

Before production use, replace or substantially redesign:

- directory/file lifecycle state with transactional durable records, owner leases, and reconciliation;
- unrestricted rootfs copying with verified manifests and a safe unpacker that rejects traversal,
  unexpected devices, ownership hazards, and resource exhaustion;
- the direct workload PID 1 with a tested init/supervisor and signal protocol;
- ambient runtime policy with explicit cgroups v2, capabilities, `no_new_privs`, seccomp, devices,
  network isolation, read-only mounts, and least-privilege identities;
- unbounded operations with quotas, timeouts, cancellation, process-group cleanup, and retained logs;
- implicit local trust with authenticated authorization and audited administrative operations.

Testing would need disposable virtual machines, multiple supported kernels and filesystems, crash and
power-loss simulation, namespace escape research cases, fuzzing of image metadata and CLI inputs,
and load tests with stated hardware and methodology. None of those labels is claimed here.
