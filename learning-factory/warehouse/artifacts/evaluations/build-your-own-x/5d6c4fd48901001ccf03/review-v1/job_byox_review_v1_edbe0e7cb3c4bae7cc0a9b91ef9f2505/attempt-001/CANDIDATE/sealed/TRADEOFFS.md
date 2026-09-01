# Minibox tradeoffs

Minibox optimizes for a reviewable learning surface. The choices below are not claims that the
smallest implementation is the strongest production design.

## Strict specification versus convenience

A narrow schema rejects coercions, unknown modes, invalid identifiers, non-string arguments, and
ambiguous timeouts early. This makes test outcomes deterministic and prevents values from crossing a
privilege boundary by accident. The cost is that callers must normalize their own input and cannot
silently inherit a host environment. In particular, an empty environment is safer and more
reproducible than copying `os.environ`, but less convenient for interactive use.

## Reject every symlink versus normal filesystem semantics

Refusing all symlink components is stricter than typical command lookup. It makes the educational
containment rule easy to state and catches both absolute and relative link escapes. It also rejects
common root filesystems where `/bin` or a command is a benign link. A production resolver would
normally use descriptor-relative traversal (`openat2` with appropriate resolution flags where
available), preserve a carefully specified subset of link behavior, and execute an already-opened
object. A simple preflight walk still has check-to-use races.

## Per-container JSON versus a transactional database

JSON makes state inspectable and allows a focused atomic-replacement exercise. A no-follow regular
lock file and `flock` serialize same-ID operations on the supported local platform; exclusive create,
same-directory temporary inodes, atomic link/replacement, file synchronization, and directory
synchronization make the persistence sequence explicit. JSON still provides no cross-record
transaction, secondary index, lease, or portable
distributed locking. SQLite or another transactional store would be preferable for a daemon,
especially for atomic claims and recovery scans.

## Pure plans and backend injection versus direct execution

An injected backend lets unprivileged tests verify the security-sensitive inputs and lifecycle. It
also makes platform limitations explicit. The extra interface permits a malicious or buggy backend,
so the control plane must distrust backend claims and validate results. Integration tests against a
real kernel remain necessary; mocks cannot prove namespace isolation.

The subprocess backend uses a minimal deterministic environment to locate trusted host tools and the
Python helper. This avoids unintentionally forwarding host variables into bootstrap. It makes package
location and locale part of the explicit launcher contract and still requires the selected Python
interpreter and package tree to be trusted.

## `unshare` subprocess versus direct syscalls

Calling the system `unshare` program avoids a large native binding and keeps the learning project in
Python. Passing argv arrays and JSON on stdin avoids shell parsing. The behavior still depends on the
installed util-linux version, kernel configuration, user-namespace policy, and privilege model.
Direct syscalls or a small audited launcher would offer tighter control over flags, file descriptors,
signals, credentials, and error reporting, at the cost of substantially more platform-specific code.

## Readiness pipe versus interpreting an exit code

A bounded inherited status pipe separates pre-exec setup failure from a target that legitimately
returns the helper's conventional error code. The explicit marker records readiness; close-on-exec
prevents the target from inheriting the writer and forging later status, while an `execve` exception
can still append an error before the helper exits. This is small and testable, but depends on correct
descriptor handling by the launcher and has only a tiny private text protocol. A mature supervisor
would use versioned structured reasons and stable process identities, and would test every
pipe-close, launcher-exit, signal, and exec-failure ordering.

## `chroot` helper versus a mounted container root

`chroot` demonstrates filesystem-view changes with little machinery. It is not equivalent to
`pivot_root`, does not close inherited file descriptors by itself, and can be escaped by a suitably
privileged process. A stronger launcher would construct a private mount tree, bind a verified root
read-only where appropriate, use `pivot_root`, detach the old root, and minimize capabilities before
executing untrusted code.

## Fail-fast state transitions versus automatic recovery

The four-state machine (`CREATED`, `RUNNING`, `EXITED`, `FAILED`) makes evidence understandable.
Invalid or corrupt state fails closed rather than being guessed into a terminal status. This leaves
manual recovery work after a controller crash and cannot distinguish all runtime phases. Production
systems usually add ownership, process identity, start/finish reasons, leases, restart policy, and a
reconciler whose decisions are themselves durable.

## Captured output versus streaming

Returning capped byte strings preserves exact output up to a configured limit and is easy to test.
The real backend spools complete streams to temporary files before returning the capped prefix, so a
noisy process can exhaust temporary-disk space even though result memory is bounded. Fixed caps can
also lose diagnostics. Production execution should stream to quota-controlled durable logs, record
truncation as structured metadata, and define backpressure and retention.
