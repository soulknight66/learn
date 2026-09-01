# Productionization assessment

## Current disposition

The artifact is **not productionized**. It is a compact Linux container
concept exercise with deterministic control-plane behavior and an injectable
isolation boundary. A short Bash runtime, chroot, and a handful of namespaces
must not be presented as safe hostile multi-tenancy.

Productionization should begin by choosing a mature OCI runtime or sandbox
backend, not by making the teaching script setuid. The CLI can remain a useful
prototype for desired behavior, while privileged mechanics move behind a
small, authenticated service boundary.

## Required architecture work

1. Define a versioned request and state schema with database-enforced lifecycle
   transitions, idempotency keys, and crash recovery.
2. Run a dedicated supervisor with fixed executable paths and a scrubbed
   environment. Authenticate and authorize every caller and instance action.
3. Delegate isolation to a maintained OCI runtime. Pin supported versions and
   validate all generated runtime configuration.
4. Apply user-namespace mapping, a minimal capability set, `no_new_privs`,
   seccomp, LSM policy, read-only and `nosuid/nodev/noexec` mounts where
   appropriate, and a closed device policy.
5. Place every workload in cgroups with CPU, memory, PID, and I/O limits.
   Specify out-of-memory, fork-bomb, and disk-exhaustion behavior.
6. Define network namespaces, address allocation, firewall policy, DNS, egress
   controls, and teardown reconciliation.
7. Replace arbitrary host rootfs paths with immutable, digest-addressed images
   from an authenticated source. Verify unpacking against traversal, links,
   devices, ownership tricks, and decompression limits.
8. Use descriptor-relative filesystem operations and dedicated state/image
   roots with verified ownership and permissions. Add quotas and garbage
   collection with explicit ownership evidence.

## Reliability and operations

The supervisor needs startup reconciliation between database state, runtime
state, cgroups, mounts, network resources, and live process identity. Every
transition needs a bounded deadline, cancellation behavior, and retry policy.
Cleanup should be idempotent and should quarantine ambiguous resources rather
than deleting by an unverified path or PID.

Expose structured metrics for operation latency and outcome, active workloads,
stale state, cleanup retries, cgroup pressure, image usage, and helper/runtime
errors. Emit tamper-resistant audit events containing authenticated actor,
request ID, instance ID, image digest, policy version, transition, and outcome;
never include secret values or unrestricted child output.

Logs require size limits, rotation, backpressure, and an explicit policy for
stdout/stderr retention. Health checks must distinguish API availability from
the ability to start a sandbox. Operators need documented backup, restore,
upgrade, rollback, host-drain, and incident procedures.

## Test and assurance gates

- Unit and state-machine tests cover every allowed and forbidden transition,
  including duplicate requests and crash-recovery replay.
- Concurrency tests deterministically exercise create/run/delete races and
  prove that cleanup cannot remove a successor's resources.
- Integration tests run on each supported kernel/filesystem combination and
  verify namespace, mount, cgroup, capability, seccomp, LSM, and network state
  from both sides of the boundary.
- Image ingestion is fuzzed with malformed archives, links, devices, sparse
  files, huge metadata, and resource-exhaustion cases.
- Fault injection kills the CLI, supervisor, runtime, and host at transition
  boundaries and verifies reconciliation after restart.
- Security review includes threat modeling, dependency/SBOM policy, static
  analysis, syscall-policy review, and an independent escape assessment.
- Load and soak tests retain raw data and establish capacity limits, tail
  latency, fairness, leak behavior, and cleanup backlog under failure.

## Release criteria

No production label should be applied until supported host configurations,
threat model, service-level objectives, and incident ownership are explicit;
all gates above have durable evidence; critical findings are closed; and a
staged deployment demonstrates rollback and host reconciliation. The current
challenge intentionally does not meet those criteria.
