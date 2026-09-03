# Sealed implementation review

## Review outcome

The reference controller is suitable as a deterministic teaching implementation and test oracle for
the stated contract. It is not suitable for hostile workloads or production deployment. The most
important positive properties are anchored name validation, scoped recursive deletion, argv
preservation, inert metadata parsing, same-filesystem publication, explicit transitions, and a
test-injectable runner.

## Known limitations

- `SIGKILL`, power loss, or filesystem failure can leave a lock or `RUNNING` state with no owner.
- `status` and `exit_code` are separate files, so inspection is not a transactional snapshot.
- A process with write access to the private state directory can race path checks.
- Copying arbitrary rootfs trees has no image-manifest validation, size limit, ownership policy, or
  protection from device nodes and other special files.
- The workload is PID 1 without a purpose-built init process to reap descendants and forward signals.
- No timeout, cgroup, network, seccomp, capability, device, or resource policy exists.
- The namespace runner depends on util-linux behavior and site policy. A bounded integration probe
  ran on the generation host, but that single result proves neither portability nor containment.
- The controller has no durable supervisor, recovery reconciliation, or structured audit log.

## Security boundary statement

Tinybox must not be described as a sandbox. User and mount namespaces reduce some host impact, but
the omitted controls and minimal image handling leave a large attack surface. Even a passing real
runner probe would demonstrate availability, not containment quality.

## Recommended review gates before extension

Before adding features, introduce a transactional metadata store, a narrow privileged boundary (if
one is truly necessary), safe image extraction with explicit special-file policy, a real init shim,
and integration tests in disposable virtual machines across supported kernels. Threat modeling must
precede any claim about untrusted workloads.
