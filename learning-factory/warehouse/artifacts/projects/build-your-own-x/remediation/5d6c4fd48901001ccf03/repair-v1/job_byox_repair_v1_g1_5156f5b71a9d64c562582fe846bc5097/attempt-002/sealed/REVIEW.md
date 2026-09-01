# Security and correctness review

## Review outcome

The reference is suitable as an educational implementation when run in a disposable environment
with trusted operators and an expendable rootfs. It is not approved for production or for executing
hostile workloads. Independent validation is still required.

## What the design gets right

- The user command remains an argv vector; no layer constructs a shell command string.
- The privileged helper receives a typed JSON message on stdin and revalidates its shape.
- Rootfs lookup rejects traversal and every symbolic-link component, and it does not consult the
  host's command search path.
- Namespace selection is represented as the deterministic tuple `user, mount, pid, uts, ipc[, net]`
  and can be tested without privileges.
- Real execution is behind an injected backend, permitting exact failure and state-transition tests.
- Lifecycle records have explicit revisions and a small legal transition graph. Complete JSON is
  guarded by a per-ID `flock`, synced, and published by replacement instead of overwriting the
  visible record in place. Initial creation publishes a synced temporary inode with an atomic
  no-overwrite hard link, so a killed writer does not expose a partial initial record.
- A post-publication directory-sync failure is not misreported as an ordinary failed mutation:
  `StateCommitUncertain` carries the exact visible proposal and `recover` verifies and re-syncs it.
- A bounded, close-on-exec status pipe distinguishes helper setup/exec failure from a target's exit;
  a target that returns 125 remains `EXITED`, while a helper error becomes `FAILED`.
- The helper closes unneeded descriptors at launch, hardens the proc mount, enables `no_new_privs`,
  bounds its payload, and the backend caps returned output and kills its process group on timeout.
- The launcher constructs a small deterministic helper environment rather than inheriting
  `os.environ`; the eventual target receives the guest fallback `PATH` plus only spec-provided values.

## High-severity production blockers

1. **Containment is incomplete.** `chroot` plus namespaces does not by itself remove capabilities,
   filter syscalls, constrain devices, enforce LSM policy, or prevent resource exhaustion.
2. **Path resolution has a check-to-use window.** Rejecting links during inspection does not pin the
   inspected inode. A concurrently mutable rootfs can swap components before the child executes.
3. **No cgroups or kill/reap contract.** CPU, memory, pids, I/O, and fork bombs are uncontrolled.
   Timeout handling must also prove that the whole descendant process group is terminated and reaped.
4. **Privilege and identity are underspecified.** Supplementary-group dropping is useful but does not
   establish a non-root target identity, a capability bounding set, syscall filtering, or an LSM
   policy. `--map-root-user` and `no_new_privs` are valuable but insufficient on their own.
5. **Mount construction is minimal.** The root may be writable, device and mount exposure are not
   governed by a comprehensive policy, and an old root is not detached via `pivot_root`. The proc
   mount does use `nosuid`, `nodev`, and `noexec`, but those flags do not harden the broader tree.

## Medium-severity gaps

- Per-file JSON has same-ID local `flock` serialization and an in-process uncertain-commit recovery
  operation, but a crashed controller still needs durable intent/idempotency records and documented
  filesystem assumptions to reconcile publication after restart.
- Returned stdout and stderr are capped, but their temporary spool needs a disk quota, streaming,
  retention, and a structured truncation field.
- Hostname and helper payload size are bounded, but argv/environment counts and individual values
  need explicit parser-side bounds. An oversized programmatically built payload is currently
  discovered by the helper only after launch.
- State needs launcher identity, kernel process identity (preferably pidfd), reason codes, and a way
  to reconcile a stale `RUNNING` record after controller death.
- Namespace support and util-linux behavior vary. A startup capability probe and versioned protocol
  are needed instead of treating every `unshare` failure alike.
- The readiness pipe is bounded and closes across successful exec, but its private text protocol has
  no versioned structured reason codes. Integration tests must cover missing, partial, duplicate,
  oversized, and `READY`-then-`ERROR` status as well as launcher failure after readiness.
- A network namespace called `none` still needs a precise loopback, route, DNS, and egress contract.
- Audit logs should be durable and must not be inferred from user-controlled stdout or stderr.

## Review questions for any change

1. Does untrusted text cross into a shell, host path lookup, state filename, mount source, or log field?
2. Is validation repeated at the privilege boundary, with unknown fields and wrong types rejected?
3. Can the rootfs change between validation and use? Which directory or file descriptors pin it?
4. Does every state mutation name a legal predecessor and increment exactly one revision?
5. Are setup errors, timeout, signals, and target exit codes represented without ambiguity?
6. Can a failure leave a partial state document, orphaned descendants, mounted filesystems, or a
   terminal success claim without runtime-controlled evidence?
7. Does a test exercise the real kernel behavior, or only a fake backend? Both have value, but they
   prove different things.

## Recommended validation layers

Use deterministic unit tests for strict schema handling, resolution, plan construction, transition
enforcement, atomic replacement failures, and backend injection. Add property tests for identifiers,
paths, and protocol messages. Run privileged integration tests only in a dedicated nested-virtualized
runner, checking namespace inode differences, proc contents, hostname isolation, filesystem view,
network behavior, signal cleanup, and mount cleanup. Finally, conduct adversarial tests with a
concurrently mutated rootfs and crash injection at each persistence boundary.
