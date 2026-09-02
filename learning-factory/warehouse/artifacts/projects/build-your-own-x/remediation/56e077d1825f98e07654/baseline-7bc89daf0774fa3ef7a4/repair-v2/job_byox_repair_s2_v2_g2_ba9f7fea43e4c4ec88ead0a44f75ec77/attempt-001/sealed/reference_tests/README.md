# Sealed reference tests

The host-side tests extend the public contract with exhaustion, stale state,
PID wrap exhaustion, top-of-address-space translation, raw-byte mutation
snapshots, canonical padding checks, and full-capacity scrubbing checks. They
intentionally compile only the portable C units.

`make arm-test` is a separate target-level regression. It compiles the runtime
and real ARM context switch, then runs a bounded QEMU probe in a new process
session. The probe leaves a physical frame behind while its logical task exits,
is reaped, and has its slot reused. It checks both stale yield and stale return:
the selected replacement must run, obsolete code after stale yield must not
resume, and the reused context must not be overwritten. The runner requires
`REENTRANT-PROBE`, `REPLACEMENT-RAN`, `RETURN-REPLACEMENT-RAN`, and `NO-BUG`,
and rejects `OUTER-RETURN`, `BUG-STALE-RETURN-KILLED-REPLACEMENT`, and setup
failure markers.

Failure snapshots use `memcpy` into unsigned-byte arrays rather than structure
assignment, so their evidence does not depend on unspecified padding stores.

The tests are deterministic and use compiler sanitizers in the factory host
run. Exact configured ARM, QEMU, Python, and library paths must be passed to the
ARM target because factory tools are not on `PATH`. Passing results evaluate
this generated reference, not arbitrary learner submissions or production
fitness.
