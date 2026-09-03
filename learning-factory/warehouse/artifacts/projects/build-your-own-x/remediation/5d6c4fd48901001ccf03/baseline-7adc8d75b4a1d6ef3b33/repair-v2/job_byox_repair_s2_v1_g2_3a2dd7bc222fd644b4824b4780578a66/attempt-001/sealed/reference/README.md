# Sealed reference implementation

This directory contains instructor-only reference code for the documented contract. It is present
in the complete instructor/source artifact and is deterministically absent from the generated
learner view. It is not a production container runtime.

Deterministic tests use temporary rootfs directories, fake process objects, and SQLite. The optional
CLI can invoke `unshare`, but only after the caller passes `--allow-execution`; default tests do not
take that path. The helper uses a user namespace, a private mount namespace, a bind-mounted rootfs,
a child-side procfs mount, optional read-only remounting, `chroot`, a UTS hostname, and direct
`execvpe` without a shell.

The opted-in `run` CLI first invokes `minictr.preflight` with the same namespace setup. That helper
never execs the workload. A denied default read-only remount returns an actionable unsupported-host
result, and the CLI proves the workload launch was not attempted.

Run reference tests from the repository root:

```bash
PYTHON311="${PYTHON311:-/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3}"
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference \
  "$PYTHON311" -m unittest discover -s sealed/reference_tests -v
```

Passing unit tests validates deterministic behavior only. It does not establish a hostile-workload
security boundary or prove this host permits the kernel operations.
