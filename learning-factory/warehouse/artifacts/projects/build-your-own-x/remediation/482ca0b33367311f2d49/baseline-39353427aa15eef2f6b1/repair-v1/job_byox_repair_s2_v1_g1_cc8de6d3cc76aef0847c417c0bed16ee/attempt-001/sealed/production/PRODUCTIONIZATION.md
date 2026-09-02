# Productionization assessment

Status: **not productionized**. The manifest value `productionized: false` is intentional.

Release engineering must treat this full tree as an evaluator artifact. A student artifact is a
separate output of the checked exact-file exporter under `environment/`; copying or serving the full
tree exposes reference code, private tests, and answers. The release pipeline should independently
compare the exported path set with the allowlist before publication.

Before any hostile workload, replace the portable runner with a reviewed supervisor that provides
rootless user, mount, PID, IPC, UTS, and network namespaces; a verified root switch; no-new-privileges;
minimal capabilities; seccomp; cgroup CPU/memory/PID/I/O controls; bounded logs; and reliable signal
forwarding/reaping. Avoid a general-purpose privileged Python process.

The control plane also needs:

- versioned SQLite migrations, backup/restore tests, corruption handling, and upgrade compatibility;
- leases, attempt rows, supervisor acknowledgements, restart reconciliation, and idempotent cleanup;
- authenticated image provenance, digest verification across transport, decompression budgets, and a
  registry policy;
- read-only content mounts plus copy-on-write container layers with quota accounting;
- exact ownership metadata for mounts/directories and safe garbage collection after crashes;
- multi-tenant authorization, audit events, redaction, log retention, and denial-of-service limits;
- structured metrics, health checks, trace correlation, operator runbooks, and fault injection;
- Linux distribution/kernel matrices and adversarial isolation tests in disposable machines; and
- independent security review and transfer verification by operators who did not author the runtime.

Local unit tests cannot validate those properties. The current code is an instructional control-plane
model and must remain unprivileged.
