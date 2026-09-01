# Productionization assessment

Minibox is **not production-ready** and this repository makes no productionization claim. The
reference is a compact educational control flow, not a substitute for an audited container runtime.

## Required redesign before hostile workloads

### Pin filesystem objects

Treat rootfs ownership and mutability as security policy. Open a trusted root directory and resolve
all paths descriptor-relatively with kernel-enforced no-escape and no-symlink rules. Keep descriptors
open through launch and execute a pinned object where executable and interpreter semantics permit.
Build a new private mount tree, make propagation private, bind required paths with explicit flags,
use `pivot_root`, detach the old root, and clean up mounts on every failure. Reject special files and
untrusted mount sources.

### Minimize privilege

Use a small, memory-safe or narrowly audited launcher. Define rootless user-namespace mappings where
supported; otherwise isolate the privileged service from callers. Set target uid/gid and groups,
drop bounding/permitted/effective/ambient capabilities, set `no_new_privs`, apply a reviewed seccomp
profile, and integrate an LSM policy. Close or explicitly whitelist file descriptors. Prevent
ptrace and credential regain. Handle setuid files and file capabilities intentionally.

### Control resources and processes

Create a cgroup v2 subtree per workload with CPU, memory, pids, and I/O limits and an explicit OOM
policy. Use pidfds or equivalent stable process handles. Specify signal forwarding, PID-1 behavior,
zombie reaping, graceful termination, forced cgroup kill, and cleanup. Timeouts must cover the whole
process tree, not just the launcher process.

### Harden protocol and persistence

Version and size-limit both the JSON helper protocol and the close-on-exec readiness protocol; reject
duplicate/unknown fields, invalid Unicode policy, wrong JSON types, non-finite numbers, and trailing
data. Replace private text errors with structured reason codes while retaining the exec-boundary
signal. Authenticate callers. Store desired state, observed state, ownership, idempotency keys,
process identity, reason codes, and append-only audit events transactionally. Use explicit locks or a
single writer and reconcile incomplete work after a crash. Never infer success from a log line.

### Define networking

Specify what `none` means for loopback and routes. For connected modes, create and move interfaces,
apply address and route policy, isolate DNS configuration, enforce ingress/egress filtering, and
clean up idempotently. Network policy needs integration tests proving absence as well as presence of
connectivity.

### Bound data and observability

Bound argv, environment, payload, and output sizes. Stream stdout/stderr to durable sinks with
backpressure, byte counts, truncation labels, retention, and access control. Emit structured audit
events for validation, state changes, launcher identity, namespace/cgroup identity, exit cause, and
cleanup. Escape untrusted values in every presentation layer and avoid secrets in logs.

## Release evidence needed

Before any production label, require threat modeling, independent security review, kernel-version
compatibility testing, fuzzing of both protocol endpoints and path handling, crash/fault injection,
concurrency tests, resource-exhaustion tests, and privileged integration tests in disposable hosts.
Measure cold start, steady-state overhead, logging behavior, and cleanup under load with a published
methodology. No such benchmark or audit evidence is claimed here.

Operational readiness also needs signed artifacts, dependency and SBOM policy, reproducible builds,
vulnerability response, upgrade/rollback procedures, schema migrations, metrics and alerts, runbooks,
backup/recovery tests, supported-platform documentation, and an incident-response owner.

## Safer deployment guidance for the exercise

Run only in an expendable VM dedicated to the workshop. Use a non-sensitive test rootfs, no host
secrets, no production mounts, no privileged network access, and no untrusted multi-tenant input.
Prefer the fake backend for ordinary unit tests. Destroy the VM after privileged experiments.
