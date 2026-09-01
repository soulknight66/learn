# Tradeoffs and rejected scope

## Full copies instead of overlay mounts

Copying an image rootfs for each container is slow and space-heavy, but deterministic and testable without mount privileges. Overlayfs would better model Docker storage while introducing kernel, mount-cleanup, whiteout, and privilege dependencies.

## SQLite plus filesystem payloads

SQLite gives atomic state transitions and auditable history. Rootfs trees remain outside the database, so a crash can leave an orphaned staging or published directory. A production design needs reconciliation records and ownership-safe garbage collection.

## Reject all links

Real images commonly contain symbolic and hard links. Supporting them safely requires carefully defined within-root resolution and link-order semantics. This challenge rejects them to keep the archive boundary understandable; compatibility is intentionally sacrificed.

## Threads for pipe draining

Two small reader threads work portably and bound retained output. An event loop could scale to many concurrent containers, while redirecting to quota-controlled log files would improve durability. Neither changes the need to drain both pipes concurrently.

## `unshare` as an external backend

Using util-linux keeps the Python code small and argv-auditable. Direct syscalls would expose clone flags and UID/GID mappings precisely but require platform bindings and substantially more cleanup code. Depending on `unshare` also makes feature availability version-specific.
