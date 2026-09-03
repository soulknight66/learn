# Sealed reference tests

`test_reference.sh` first runs the public contract against the sealed controller, then checks
additional safety and lifecycle behavior: invalid state roots, command grammar, metadata rejection,
atomic racing creates, active-run exclusion, completion during transient lock contention, handled
signals, and high runner exit statuses.

The test uses `controlled_runner.sh` instead of namespaces. This separation is intentional: kernel
policy is probed by `environment/check.sh`, while controller semantics remain deterministic.

`test_real_runner.sh` builds a temporary rootfs containing the host's `true` executable and its
reported shared-library dependencies, then attempts the full reference namespace backend. It exits
`77` with a `BLOCKED` record when policy or required host tooling prevents the integration.
