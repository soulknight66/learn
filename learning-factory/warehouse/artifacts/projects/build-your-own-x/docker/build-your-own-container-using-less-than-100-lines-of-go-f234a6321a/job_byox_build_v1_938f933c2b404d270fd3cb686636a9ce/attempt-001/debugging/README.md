# Debugging exercise index

These harness-facing exercises isolate two common runtime mistakes. Each directory is a standalone
Go module with a failing deterministic test. Diagnose the failure before opening that exercise's
local `sealed/` answer.

- `exercise_01`: mount setup ordering
- `exercise_02`: signal-derived exit status

Neither exercise performs a mount, namespace, chroot, signal, or subprocess operation.
