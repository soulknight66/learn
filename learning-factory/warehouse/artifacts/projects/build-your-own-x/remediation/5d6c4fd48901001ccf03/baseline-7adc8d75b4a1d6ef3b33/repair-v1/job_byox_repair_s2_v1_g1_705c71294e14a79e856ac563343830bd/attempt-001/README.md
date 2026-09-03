# TinyCtr: build a Linux container launcher in Python

TinyCtr is a staged systems exercise about what a container runtime actually has to coordinate:
validated configuration, a filesystem view, Linux namespaces, a PID-1 boundary, process cleanup,
and durable lifecycle state. It deliberately stops short of an image registry, networking stack,
and daemon API.

The starter is safe by default. It can parse a small container specification, but real execution is
disabled until you complete the launch planner and runner. Most work can be tested without root by
asserting plans and using fake subprocesses. An optional integration probe explains whether this
host permits an unprivileged user namespace; capability varies by kernel and policy.

## Route through the workshop

1. **Specification boundary** — make malformed IDs, commands, environment entries, timeouts, and
   unexpected fields fail closed.
2. **Filesystem boundary** — resolve guest-absolute paths beneath one trusted rootfs and reject
   traversal and symlink escapes.
3. **Namespace plan** — compile an explicit `unshare(1)` argv for user, mount, UTS, IPC, and PID
   namespaces, with network isolation as an opt-in flag. Never create a shell command string.
4. **Lifecycle state** — use SQLite transactions to claim a launch exactly once and enforce the
   `CREATED -> RUNNING -> EXITED|FAILED` state machine.
5. **Supervised execution** — send the validated spec over stdin, bound runtime, capture logs, and
   terminate the whole process group on timeout.

Read `REQUIREMENTS.md` for the precise contract, `CONCEPTS.md` for the kernel model, and
`DESIGN_QUESTIONS.md` before implementation. Start with `starter/README.md` and run:

```bash
PYTHON311="${PYTHON311:-/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3}"
"$PYTHON311" -c 'import sys; print(sys.version.split()[0]); sys.exit(0 if sys.version_info >= (3, 11) else "Python 3.11+ required")'
TMPDIR="${TMPDIR:-$PWD}" PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=starter \
  "$PYTHON311" -m unittest discover -s public_tests -v
```

The default path above is the supplied factory toolchain. Set `PYTHON311` to a Python 3.11-or-newer
interpreter on another host. The green discovery suite covers the supplied warm-up; opt-in stage
checkpoints that start red are documented in `public_tests/README.md`.

## Safety boundary

This is an educational runtime, not a security boundary for hostile workloads. User namespaces may
be disabled. Rootfs setup and mount operations are platform-specific. Do not point it at `/`, a
source checkout, or data you care about. The generated artifact remains `PARTIAL`: deterministic
unit tests can exercise plan construction, but this build environment did not establish a complete
container rootfs or grant production readiness.
