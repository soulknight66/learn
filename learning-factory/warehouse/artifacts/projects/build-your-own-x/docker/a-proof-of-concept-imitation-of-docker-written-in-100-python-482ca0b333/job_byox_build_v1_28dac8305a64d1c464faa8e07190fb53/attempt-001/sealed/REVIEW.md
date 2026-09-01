# Reference review

Review scope: independently generated MiniBox reference code and tests.

## Findings addressed in the reference

- Archive extraction does not use `extractall`, rejects special files and links, prevalidates metadata, strips special mode bits, and checks existing symlink components.
- Lifecycle writes use parameterized SQL, explicit `BEGIN IMMEDIATE`, expected-state comparison, a database-enforced graph, and append-only events.
- Image and container staging paths are internally generated and cleaned only while owned by the operation.
- Runtime launch uses an argv tuple, a minimal explicit environment, `shell=False`, a timeout, a new session, process-group termination, and bounded retained output.
- Public and sealed tests distinguish a payload's nonzero exit from harness failure.

## Residual findings

- Archive application is not rollback-atomic after metadata validation, and path checks remain vulnerable to a malicious concurrent writer because Python lacks an `openat2` wrapper in the standard library.
- Tar links are rejected, reducing compatibility with typical Linux root filesystems.
- Filesystem publication and lifecycle insertion are not one transaction; recovery/reconciliation is missing.
- There are no cgroups, capability bounding, seccomp, LSM integration, signature checks, namespace PID-1 reaping helper, networking setup, read-only mounts, or host resource accounting.
- Runtime behavior depends on util-linux flag support and host user-namespace policy. No real isolated payload was validated in this build.

Disposition: suitable as an educational reference; not approved for hostile workloads or production use. Status remains `PARTIAL`.
