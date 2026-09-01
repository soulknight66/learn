# Adversarial expected findings

This instructor material gives expected properties, not proof that every platform backend satisfies
them.

## Input and path cases

- An ID is accepted only when it matches `[a-z0-9][a-z0-9_.-]{0,63}` exactly. Dots after the first
  character are legal flat-name characters; `/`, a leading dot, uppercase text, and overlong IDs are
  rejected before selecting a state filename.
- Empty argv, an empty or non-string argument element, non-finite or nonpositive timeouts, invalid
  environment names or values, unsupported network modes, and malformed hostnames must fail strict
  validation.
- `/../bin/tool`, relative traversal, malicious `PATH` entries, prefix-sibling roots, and any symlink
  component must not resolve. Under Minibox's strict policy, an entirely internal symlink is rejected
  too. Directories, devices, sockets, and non-executable regular files are not commands.
- Command lookup must not fall back to the host's `PATH` or host root when the rootfs candidate is
  absent.

## Protocol and process cases

The real backend must preserve literal argv boundaries and send JSON on stdin; metacharacters cannot
become a host shell program. The helper should reject malformed JSON, trailing or unexpected
structure, wrong types, unknown fields, and excessive input according to its documented limits.
Production hardening should additionally reject duplicate keys explicitly; ordinary JSON parsing
does not guarantee that policy.

A target returning nonzero is an `EXITED` workload with that exit code. Resolution, process-start,
I/O, or timeout exceptions become `FAILED`. The close-on-exec status pipe must also make malformed
helper input and namespace/chroot/mount/exec setup errors `FAILED`. Test an absent marker, malformed
or oversized status, `READY` followed by `ERROR`, and a target that genuinely returns 125; only the
last case is `EXITED`. Timeout and interruption tests must look for surviving descendants, not only
the immediate `unshare` process.

## State and race cases

Only `CREATED -> RUNNING` and `RUNNING -> EXITED|FAILED` are legal, each with one revision increment.
A corrupt document, duplicate creation, direct terminal transition, or terminal rewrite fails closed.
Crash injection should leave an old or new complete document. Same-ID multi-process operations are
serialized by a no-follow regular lock file and `flock`, so a race between two transitions from the
same revision has at most one winner. Cross-record atomicity and distributed-filesystem locking are
outside the guarantee.

Mutating a rootfs after resolution probes a known design limit. The educational no-symlink walk is
not equivalent to descriptor-pinned lookup. A successful race is a high-severity production blocker,
not a reason to weaken the test.

## Isolation evidence

Privileged tests should compare namespace identities, the target's proc view, host and target
hostnames, network reachability, mount propagation, and post-exit mounts. Plan equality is necessary
unit evidence but cannot demonstrate kernel isolation. Run these cases only on a disposable host.
