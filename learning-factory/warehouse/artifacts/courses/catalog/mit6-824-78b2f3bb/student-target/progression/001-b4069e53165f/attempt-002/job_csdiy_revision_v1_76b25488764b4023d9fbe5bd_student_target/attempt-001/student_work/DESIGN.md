# ParcelQ semantic-model design

Validation label: **LOCALLY IMPLEMENTED AND TESTED**. This document describes
`lease_queue.py`; independent harness validation has not yet occurred.

## State and ownership

`DurableQueue` is the only business-state mutator. Each configured job contains
an immutable `JobState(state, worker_id)` and begins as `READY` with no worker.
The other states are `CLAIMED(worker_id)` and `DONE(worker_id)`. The queue also
owns the installed `Lease` fence and the command-history map. Coordinator and
queue state survive node pause markers in this semantic model.

A `Lease` is the immutable value
`(owner, epoch, start_tick, expires_tick)`. Its interval is half-open:

```text
start_tick <= tick < expires_tick
```

The coordinator requires a positive integer TTL (booleans are rejected as
integers). A grant while its current lease is valid returns `None`, consumes no
epoch, and does not install or log a new fence. At the expiry tick the old lease
is no longer valid, so a successful grant receives the next epoch.

## Fence installation and atomicity

`Coordinator.grant` constructs the next immutable lease and calls the queue's
private fence-install operation. The queue validates that the caller holds the
identity token created when the single coordinator was bound, that the interval
is nonempty, and that the epoch is exactly one greater than the installed
epoch. Only after the queue fence is installed does the coordinator publish the
same value as `current` and advance `epoch`; only after both commits does the
method return the lease.

No runner event can interleave inside this single-process call. The grant takes
snapshots of both authority objects and the installation-log boundary. If
validation or installation raises, it restores the queue fence, coordinator
current lease, coordinator epoch, and installation log, then records
`INSTALL_FAILED` and re-raises. Thus a failed call exposes neither a candidate
lease nor a misleading `fence_install` record. The injected-failure test covers
the case where the queue changed its fence and logged installation before
raising.

The binding token and private Python methods are an in-model trust convention,
not authentication, access control, or cryptographic proof. Python code with
object internals can bypass it. A real system would need an enforceable
coordinator identity and a durable atomic protocol.

## Request identity and decision order

A `Request` has `command_id`, `action`, `job_id`, and `worker_id`. Its payload
fingerprint is exactly:

```text
(action, job_id, worker_id)
```

Lease owner, epoch, and interval are intentionally excluded, permitting the
same operation to be retried through a later valid dispatcher.

For every queue delivery, processing order is:

1. If `command_id` is in history and the payload matches, return the exact saved
   `Response` object without checking current authority or mutating anything.
2. If the ID exists but the payload differs, return `ID_CONFLICT` without
   replacing history or changing a job.
3. For an unseen ID, require the presented value to be a `Lease`, equal the
   entire installed lease, and contain the authoritative tick in its installed
   half-open interval. Otherwise return `FENCED` without history or mutation.
4. Evaluate the business transition and store both payload and exact response.
   This history write occurs even for an authorized nonmutating business result.

`Node` rejects only the absence of a lease as `NO_LEASE`. A node deliberately
forwards an apparently expired token so the queue remains authoritative and a
matching historical request can replay before the fence check. An unseen
expired request is still fenced by the queue.

## Business responses

Unknown-job lookup precedes action validation, so any action against a missing
job returns `NOT_FOUND`. For an existing job, unsupported actions return
`INVALID`.

| Action | Current state / condition | Response | New state |
|---|---|---|---|
| `CLAIM` | `READY` | `OK_CLAIMED` | `CLAIMED(request.worker_id)` |
| `CLAIM` | claimed by same worker | `ALREADY_CLAIMED` | unchanged |
| `CLAIM` | claimed by another worker | `CLAIMED_BY_OTHER` | unchanged |
| `CLAIM` | `DONE` | `ALREADY_DONE` | unchanged |
| `COMPLETE` | `READY` | `NOT_CLAIMED` | unchanged |
| `COMPLETE` | claimed by another worker | `NOT_OWNER` | unchanged |
| `COMPLETE` | claimed by same worker | `OK_DONE` | `DONE(request.worker_id)` |
| `COMPLETE` | `DONE` | `ALREADY_DONE` | unchanged |

Only `FENCED`, early `NO_LEASE`, and `ID_CONFLICT` fail to create a new history
entry. Replays use an existing entry but create no additional one. Saving
nonmutating business responses makes their retries stable even if another
command later changes the job.

## Determinism and evidence

`EventRunner` assigns each scheduled event a unique monotonically increasing
`insertion_index`. Its heap ordering is the tuple `(tick, insertion_index, ...)`;
because the second component is unique, later fields never decide a tie. Grant,
submit, pause, and resume events therefore have repeatable order. Delay is a
later submission tick, duplication is multiple submit events, and loss is the
absence of a delivery event. Pause and resume are explicit trace markers; the
model has no autonomous threads to stop or start.

Every structured log record has the common fields `tick`, `event`,
`command_id`, `owner`, `epoch`, `active_owner`, `active_epoch`, `decision`,
`state_changed`, `job_before`, and `job_after`, with `None` (JSON `null`) when a
field is inapplicable. Request records additionally expose the payload,
presented and active intervals, response code, `history_changed`, and insertion
index. The model records grant attempts and decisions, fence installations,
node rejections, queue attempts, replays, conflicts, fence rejections, and
business decisions. Logging occurs after each corresponding decision and is
never consulted to choose a response or job transition.

From the submission directory, the clean command is:

```bash
python3 -m unittest -v test_lease_queue.py
```

The suite contains the six required public traces, seven additional contract
checks, and four executable reproducers of the unsafe excerpt.

## Explicit non-goals

This is a deterministic single-process, in-memory model with trusted integer
ticks. It does not provide wall-clock leases, concurrency, a transport, storage
durability, crash recovery, coordinator failover, replication, consensus,
linearizability across processes, protection from Byzantine inputs, or secure
tokens. It does not derive from or retrieve the linked catalog target and is not
official course material. Local tests are not production validation,
independent validation, credit, or transfer evidence.

> This submission models one locally authored epoch-fenced queue exercise. It does not implement a consensus protocol, establish production correctness, complete an official assignment, or claim course completion.
