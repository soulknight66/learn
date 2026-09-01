# Design tradeoffs

## Shell as the implementation language

Bash makes namespace tools and argv flow visible, which serves the learning
goal. It also has weak types, global process state, subtle trap scope, limited
binary-safe data handling, and awkward transactions. Arrays, strict parsing,
small functions, atomic filesystem primitives, and black-box tests mitigate
some risks. They do not make Bash a good foundation for a privileged,
multi-tenant runtime.

## Directory state versus a database

Per-instance directories keep the artifact inspectable and require no service
dependency. Atomic `mkdir` is enough to claim a name, and a rename can publish
a small record. The cost is that multi-file transactions, schema evolution,
crash recovery, durable flushing, and rich queries are manual. A production
control plane would normally use a transactional store and explicit state
transitions.

## Per-name coordination versus one global lock

A global lock is simple and gives deterministic serialization, but an unrelated
slow operation blocks every container. Per-name coordination permits unrelated
instances to progress independently and directly models the exclusion that
run/delete need. It adds stale-lock and ownership complexity; lock scope must
remain narrow, especially around a long-running child.

## PID plus start token versus PID files

A PID file is portable and easy but becomes false after PID reuse. Linux's
`/proc/PID/stat` start token cheaply strengthens identity without holding a
supervisor connection. It is Linux-specific and parsing `/proc` has edge cases.
Pidfds would give stronger kernel-backed identity in a language with suitable
system-call support, but are not practical from a tiny Bash runtime.

## Direct namespace tools versus an OCI runtime

Direct `unshare`, mount, and chroot calls expose the concepts being taught and
keep the code small. They implement only a narrow subset, depend on host policy,
and are easy to misconfigure. An OCI runtime supplies a mature specification,
resource controls, hooks, and broader hardening at the cost of a large external
dependency and less transparent mechanics.

## Chroot and a mount namespace versus filesystem copying

A mount namespace plus chroot avoids copying a whole rootfs and keeps teardown
cheap. Chroot alone is not a security boundary; safe setup requires privilege,
private propagation, careful mount ordering, and capability handling. Copying
is easier to inspect but slow, storage-heavy, and still does not isolate kernel
resources. Overlay filesystems add useful copy-on-write behavior but introduce
kernel/filesystem prerequisites and cleanup failure modes, so they are outside
the reference scope.

## Injectable isolator versus hard-coded system tools

One `MINICTR_ISOLATOR` executable makes the deterministic control plane testable
without root and proves exact argv/status behavior. It also means anyone who
can set the runtime environment controls what is executed; this interface is
appropriate only when the caller and environment share a trust boundary. A
setuid or service deployment must discard such overrides and use a fixed,
authenticated helper interface.

## Line-oriented metadata versus richer encoding

The rootfs record is readable and easy to consume in shell. Rejecting newline
and tab keeps it unambiguous. This narrows valid host paths and still lacks
versioning and checksums. NUL framing is awkward in shell files, while JSON
requires a reliable parser; either becomes preferable as the schema grows.

## Fail closed versus aggressive stale-state repair

Treating malformed state as an error avoids guessing about ownership. Treating
a verifiably dead `(pid, start-token)` as stale prevents an instance from being
wedged forever after a crash. The compromise is to automate only repairs that
can be established from strong evidence and report other corruption rather
than deleting it opportunistically.

