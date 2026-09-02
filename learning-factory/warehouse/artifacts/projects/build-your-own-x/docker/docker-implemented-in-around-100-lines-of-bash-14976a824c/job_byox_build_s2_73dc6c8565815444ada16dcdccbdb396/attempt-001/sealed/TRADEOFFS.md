# Sealed tradeoffs

## Full copies versus layers

Full directory copies are easy to inspect and make ownership obvious, but cost time and disk space
proportional to every rootfs. Overlay or content-addressed layers would be closer to a practical
runtime but add mount lifecycle, whiteout, integrity, and garbage-collection problems that distract
from the initial namespace exercise.

## Directory locks versus a transactional database

`mkdir` is an atomic, portable local-filesystem claim and keeps the mechanism visible in Bash. It
does not provide owner identity, expiry, crash recovery, multi-record transactions, or reliable
semantics on every network filesystem. SQLite with explicit transactions would be a more durable
controller foundation once reconciliation and concurrent readers matter.

## Synchronous run versus supervision

The synchronous CLI naturally returns the workload's status and has no daemon. It cannot reliably
reattach, supervise an orphan after controller death, retain structured logs, or reconcile a stale
`RUNNING` record. A supervisor would solve those problems at substantial complexity.

## User namespaces versus privileged setup

Mapping the caller to root inside a user namespace minimizes required host privilege. Many managed
hosts disable or restrict that feature, and user namespaces do not supply all production hardening.
A privileged helper broadens compatibility but creates a sensitive API that requires authentication,
strict validation, auditing, and a much narrower implementation language/runtime surface.

## Bash versus a systems language

Bash makes argv quoting, process structure, and filesystem atomics tangible. It has weak data types,
awkward error propagation, no built-in syscall API, and fragile signal/concurrency behavior. Rust,
Go, or C would allow direct namespace/mount syscalls, typed state, clearer resource ownership, and
more comprehensive tests.
