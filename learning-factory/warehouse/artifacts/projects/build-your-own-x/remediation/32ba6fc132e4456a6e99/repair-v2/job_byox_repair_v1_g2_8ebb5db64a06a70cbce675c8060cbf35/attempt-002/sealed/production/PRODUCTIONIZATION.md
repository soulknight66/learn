# Productionization gap and plan

## Current verdict

Do not deploy this artifact. It is an in-memory Java learning model with explicit
method-driven faults. It has no durability, wire protocol, independent nodes,
security boundary, capacity controls, or operational evidence. This document is
a plan, not a production implementation, certification, or validation label.

## Phase 0: specify before scaling

Write an executable protocol specification covering:

- record identity, offset and batch formats;
- acknowledgement levels and durability meaning;
- leader terms, fencing, voting, and commit calculation;
- retry, duplicate, timeout, and cancellation behavior;
- recovery and divergent-suffix rules;
- membership and partition reassignment;
- retention, compaction, and disk-full behavior; and
- client-visible error codes and compatibility rules.

Model-check election and commit safety under message loss, duplication,
reordering, pauses, crashes, and restarts. Minimum ISR is a policy input, not a
replacement for quorum intersection or fencing.

## Phase 1: durable local storage

Implement versioned segment and index formats with length bounds and checksums.
Define the exact write, flush, rename, and directory-sync order. On startup, scan
segments, verify indexes, distinguish a repairable tail from mid-file corruption,
and fail closed when history cannot be trusted.

Test with process kills at every persistence boundary, truncated writes, corrupt
bytes, stale metadata, read-only filesystems, disk full, and lost directories.
Provide retention and compaction with crash-safe file replacement. Protect
against unbounded allocation when parsing corrupt lengths.

## Phase 2: distributed authority

Run replicas as independent processes. Add durable term/epoch and vote metadata,
leader fencing on every write path, log matching, retransmission, commit rules,
and snapshot or segment transfer. A recovered node must validate history, remove
only an authority-proven conflicting suffix, catch up, and then become eligible.

Use a real transport with bounded frame sizes, request IDs, deadlines,
backpressure, connection lifecycle, and protocol version negotiation. Test
partitions, asymmetric reachability, delayed old leaders, clock jumps, duplicated
responses, and rolling restarts.

## Phase 3: service controls and security

Add authenticated workload and operator identities, authorization by operation
and resource, transport encryption, certificate rotation, secret management, and
tamper-evident audit events. Treat payloads, IDs, error strings, metrics labels,
and configuration as untrusted input.

Enforce quotas for connections, requests, bytes, partitions, and catch-up
bandwidth. Bound queues and memory. Define overload behavior that preserves
control-plane progress and avoids acknowledging work that cannot be retained.

## Phase 4: operations

Expose low-cardinality metrics for append latency, error classes, ISR changes,
replica lag, commit position, disk usage, flush time, election term, recovery
progress, and queue saturation. Add structured logs and trace correlation without
recording secrets or payloads.

Supply readiness and liveness semantics, graceful drain, backups or snapshots,
restore drills, partition movement, rolling upgrades, downgrade constraints,
configuration validation, and runbooks for corruption, quorum loss, certificate
expiry, and disk exhaustion. Define service-level objectives only after measuring
representative workloads.

## Phase 5: independent evidence

Required evidence includes deterministic unit and state-machine tests, protocol
model results, randomized network fault tests, crash-consistency tests on target
filesystems, corruption tests, compatibility tests across versions, load and soak
tests, recovery-time measurements, security review, dependency and artifact
provenance, and disaster-recovery exercises.

Benchmark reports must include source revision, JDK and OS, hardware, JVM flags,
dataset, payload distribution, warm-up, run duration, raw samples, percentiles,
allocation/GC data, and failure rate. No benchmark values were generated for this
challenge.

## Release gates

A candidate remains non-production until independent reviewers can demonstrate:

1. no two fenced leaders can both commit incompatible history;
2. acknowledged durability survives the documented failure budget;
3. restart and repair never invent, reorder, or silently rewrite records;
4. overload and disk full fail predictably without unbounded resources;
5. authentication and authorization cover every data and administrative path;
6. monitoring detects loss of redundancy before the remaining copy is lost; and
7. upgrade, rollback, backup, and restore procedures work on production-like
   data.

Completing the educational API tests does not satisfy any of these gates.

