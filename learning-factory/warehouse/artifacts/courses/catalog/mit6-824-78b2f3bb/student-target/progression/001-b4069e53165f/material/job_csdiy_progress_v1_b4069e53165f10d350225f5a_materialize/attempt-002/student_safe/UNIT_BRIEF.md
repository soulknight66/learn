# Epoch-Fenced Failover for a Deterministic Work Queue

## What this bounded unit is

This is a locally authored implementation and debugging exercise about failover in a distributed work queue. It belongs only to batch `csdiy-unit-batch-v1-b4069e53165f10d350225f5a` and normalized record `unit_8b606201b492edd35c65efd7eaa1843d`.

The source record is a `normalized_catalog_resource_record` titled “Course Website.” Its `official_course_unit` flag is `false`. The staged record contains the locator <https://pdos.csail.mit.edu/6.824/schedule.html>, marked `LINKED`; the target was not opened or copied. Consequently, no lecture, schedule position, paper, assignment, starter code, or test has been derived from it.

This packet is not official MIT material and is not a reconstruction of an MIT assignment. Preparing or completing it does not establish study, a pass, transfer of knowledge, official credit, or completion of MIT6.824 or any other course.

## Why this exercise

Prior bounded examiner evidence supports careful reasoning about request identity, replay, and retry ambiguity. It does not establish scalable synchronization, race freedom, or production readiness. This exercise therefore treats retry-safe request history as a baseline and concentrates on a different failure boundary: preventing a paused former primary from writing after failover, while making the incident diagnosable from deterministic evidence.

## Scenario: ParcelQ

ParcelQ is a fictional primary-controlled work queue. A coordinator grants a time-bounded lease to one dispatcher. The durable queue accepts `CLAIM` and `COMPLETE` commands. Messages can be delayed, dropped, or duplicated; a dispatcher can pause and resume after its lease has expired. A newly elected dispatcher must not be undermined by a stale one.

The exercise uses a deterministic, single-process semantic model—not sockets, threads, a real consensus protocol, or a production lease service. All time is an integer logical tick supplied by the simulator. This makes every failure trace replayable and keeps the claims bounded.

## Learning goals

By working through the task, you will practice:

- identifying the exact atomic boundary between granting authority and fencing old authority;
- separating local lease checks from authoritative sink-side validation;
- handling expiry boundaries, stale messages, retries, and command-ID conflicts without accidental mutation;
- building a deterministic event runner whose same-tick ordering is explicit;
- turning safety invariants into executable traces and useful structured diagnostics;
- stating what a semantic model does—and does not—justify about a production system.

## Model boundaries

The model has one coordinator, one durable queue, and any number of dispatcher nodes. Coordinator state and queue state survive dispatcher pauses. The coordinator and queue operation used to install a new fence is atomic in this model. The logical tick seen by the coordinator and queue is trusted simulator input; nodes do not supply authoritative time.

Network behavior is represented only by deciding when, whether, and how often a node submission event is delivered. Crashes, storage corruption, coordinator failover, Byzantine behavior, token cryptography, real-clock skew, multi-core races, and cross-process durability are outside scope. You should name these gaps rather than silently treating them as solved.

## Core vocabulary

A lease is the immutable tuple `(owner, epoch, start_tick, expires_tick)` and is valid only on the half-open interval `start_tick <= tick < expires_tick`. An epoch is a monotonically increasing fencing number. Installing a lease makes its exact owner and epoch the durable queue’s active fence before the lease is returned to its owner.

A logical request is identified by `command_id`; its payload is `(action, job_id, worker_id)`. Authority metadata—the lease owner and epoch—is not part of that logical payload. This distinction lets the same client operation be safely retried through a later dispatcher without changing its identity.

## Timebox and expected evidence

Use a six-hour target and an eight-hour hard stop. Favor a small, readable Python standard-library implementation over extra features. Preserve the implementation, deterministic tests, a short design note, and a debugging record described in the learning task. Those files are candidate evidence for later independent examination; their existence alone proves nothing.

Do not use the catalog link or search for course solutions. Everything needed for this bounded exercise is stated in this packet.
