# Sealed reference implementation

This directory contains the maintainer reference for the Minibox challenge. It
is not part of the learner view. The implementation favors explicit contracts,
inspectable plans, deterministic fake-backend tests, and bounded subprocess
behavior over feature breadth.

The state implementation distinguishes ordinary failures before atomic
publication from `StateCommitUncertain` after publication and supplies an
exact-record recovery operation. Its regression tests inject failures on both
sides of that boundary.

The optional Linux backend is educational code, not a security boundary. It
uses a user, mount, PID, UTS, IPC, and (normally) network namespace; changes
mount propagation; enters a supplied root with `chroot`; mounts a fresh
`proc`; and executes one process. It does not implement cgroups, seccomp,
capability minimization, image verification, layered filesystems, or daemon
supervision.

Run the deterministic suites from the repository root:

```bash
PYTHONPATH=sealed/reference python3 -m unittest discover -s public_tests -v
PYTHONPATH=sealed/reference python3 -m unittest discover -s sealed/reference_tests -v
```

The live backend must only be tried with a disposable rootfs created for the
exercise and on a host where unprivileged user namespaces are intentionally
enabled. A deterministic test pass does not demonstrate secure containment.
