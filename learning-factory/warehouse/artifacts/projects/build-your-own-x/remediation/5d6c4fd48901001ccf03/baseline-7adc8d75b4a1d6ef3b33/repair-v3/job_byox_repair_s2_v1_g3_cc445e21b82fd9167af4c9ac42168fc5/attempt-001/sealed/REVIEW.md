# Sealed implementation review

## What the reference establishes

- Inputs are immutable after strict parsing; booleans cannot masquerade as numeric timeouts.
- Existing path and symlink escapes fail a component-aware containment check.
- The launch is an argv array, workload values travel over bounded stdin, and helper environment is
  rebuilt rather than inherited.
- SQLite transitions are parameterized, transactional, and protected by a fixed-predicate trigger
  installed by a numbered migration; the legacy writable policy table is removed. A failed run and
  its log path remain durable. Every lifecycle entry point enforces the RFC 3339 lexical grammar,
  rejects the unsupported `:60` spelling, and validates calendar fields.
- Timeout tests prove a process-group kill is requested and the child is reaped, without launching a
  real process.
- A setup-only plan precedes the opted-in CLI workload. Unsupported read-only setup is actionable,
  and a unit test proves a failed preflight causes no second process launch.
- The distribution exporter creates disjoint allowlisted views. Per-view manifests cover all
  directories and payload file hashes, and mutation/extra-entry tests prove verification fails.

## Findings that block production approval

1. **Critical — incomplete hostile-workload controls.** There is no capability drop, seccomp, LSM
   profile, cgroup, image verification, or safe extraction pipeline.
2. **High — filesystem TOCTOU.** `Path.resolve` validation and later mount/chroot operations are not
   one descriptor-pinned operation.
3. **High — PID 1 semantics.** `unshare --fork` and kill-child do not replace a tested init shim with
   signal forwarding and orphan reaping.
4. **High — output memory bound.** `communicate` captures unlimited workload output in memory.
5. **High — crash reconciliation.** State can remain `RUNNING` after supervisor death; PID reuse can
   make naive recovery unsafe.
6. **Medium — util-linux portability.** Flag presence and setup order vary across installed versions;
   the host probe covers only the simplest user namespace operation.
7. **Medium — mount assumptions.** `<rootfs>/proc` must exist, remount behavior depends on kernel
   policy, and mount cleanup is delegated to namespace teardown rather than independently verified.
   Preflight makes rejection actionable but cannot reserve capability across the following launch.
8. **Medium — database trust.** An operating-system principal with arbitrary write access can still
   alter SQLite schema or non-state evidence fields; the educational API is not an authorization
   boundary around the database file.
9. **Medium — error/log privacy.** Child exceptions can reveal host paths, and no redaction or log
   retention policy exists.

Decision: suitable as an independently testable workshop reference, not suitable for production or
for running untrusted code. `MANIFEST.yaml` therefore keeps `productionized: false` and `PARTIAL`.
