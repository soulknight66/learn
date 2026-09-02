# Sealed reference implementation

This directory contains instructor-only reference code for the documented contract. It is not
learner-visible and is not a production container runtime.

Deterministic tests use temporary rootfs directories, fake process objects, and SQLite. The optional
CLI can invoke `unshare`, but only after the caller passes `--allow-execution`; default tests do not
take that path. The helper uses a user namespace, a private mount namespace, a bind-mounted rootfs,
a child-side procfs mount, optional read-only remounting, `chroot`, a UTS hostname, and direct
`execvpe` without a shell.

Run reference tests from the repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference \
  python3 -m unittest discover -s sealed/reference_tests -v
```

Passing unit tests validates deterministic behavior only. It does not establish a hostile-workload
security boundary or prove this host permits the kernel operations.
