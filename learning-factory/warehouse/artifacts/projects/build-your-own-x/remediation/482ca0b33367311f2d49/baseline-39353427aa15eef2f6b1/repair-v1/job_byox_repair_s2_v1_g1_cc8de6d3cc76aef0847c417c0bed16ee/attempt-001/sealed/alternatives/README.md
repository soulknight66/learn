# Alternative designs

## In-memory teaching model

Represent layers as dictionaries from normalized path to bytes/tombstone and lifecycle state as a
Python map. This makes overlay semantics easy to visualize but removes archive parsing, crash
durability, and cross-process claims—the most valuable systems boundaries in this challenge.

## Directory plus append-only journal

Write content trees normally and append state events with checksums and fsync. Recovery replays the
journal and rejects incomplete tails. This can make execution history clearer than mutable rows, but
correct locking, compaction, and atomic publication become a substantial storage-engine exercise.

## Linux-native supervisor

Use a small privileged, memory-safe native launcher for namespaces, mounts, credentials, cgroups,
seccomp, and exec; keep the Python CLI as an unprivileged client over an authenticated local socket.
This is the credible direction for real isolation, but it needs kernel-specific integration tests and
a far stronger threat model than the portable reference.

## Rootless OCI backend

Delegate execution to an installed, independently maintained rootless OCI runtime after generating a
strict bundle. This reduces bespoke kernel code while introducing an external dependency, versioned
OCI contracts, runtime discovery, and transfer validation. It would be more appropriate for a tool
whose objective is orchestration rather than learning internals.

## Content-addressed chunk store

Hash individual files and directory nodes rather than whole materialized snapshots. Containers can
share immutable blobs and create a writable metadata overlay. Space use improves, but hard-linking
blobs into writable roots is unsafe unless the blobs are protected; copy-on-write support or strict
read-only mounts is still needed.
