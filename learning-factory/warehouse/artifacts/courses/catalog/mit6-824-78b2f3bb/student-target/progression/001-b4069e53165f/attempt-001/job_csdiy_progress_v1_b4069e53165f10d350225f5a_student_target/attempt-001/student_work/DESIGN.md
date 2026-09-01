# ParcelQ design

Provenance: locally authored from `UNIT_BRIEF.md`, `LEARNING_TASK.md`, and
`SELF_CHECK.md` only. The catalog locator was not opened. Validation label:
**SELF-VALIDATED** against the local deterministic tests; no independent
validation is claimed.

## State and ownership

`Lease(owner, epoch, start_tick, expires_tick)` is an immutable `NamedTuple`.
Its interval is half-open: `start_tick <= tick < expires_tick`. `DurableQueue`
owns the installed lease, named job states, and request history. `Coordinator`
owns the current granted lease and the last committed epoch. A `Node` only holds
a copy of a lease and is never authoritative.

Jobs begin as `JobState("READY", None)` and can move only as follows:

```text
READY --CLAIM(w)--> CLAIMED(w) --COMPLETE(w)--> DONE(w)
```

Other business evaluations do not change job state, but they are still saved in
request history after authority validation.

## Lease grant and atomic fence installation

`Coordinator.grant` requires a nonempty owner, a nonnegative integer logical
tick, and a positive integer TTL; `bool` is deliberately not accepted as an
integer. If the current lease is valid, the grant returns `None` without
changing the coordinator epoch, current lease, or queue fence. At the expiry
tick the old half-open interval is no longer valid, so the next epoch may be
installed.

For a successful grant, the coordinator constructs the next immutable lease and
calls the queue's private validation/install operation. Queue installation,
coordinator-current assignment, and committed-epoch assignment occur inside one
non-interleavable model method before the lease is returned. Pre-state and the
log boundary are retained; any validation or installation exception restores
both objects and removes a partial installation record. An injected-installation
test exercises this rollback.

The queue binds exactly one coordinator and checks the bound object on private
install/rollback calls. This is only a single-process capability convention.
Hostile Python code could inspect or call private members, so it is not
cryptographic authentication or authorization.

## Sink-side authority

For an unseen request, `DurableQueue.apply` accepts authority only if all of the
following are true:

- a lease and installed fence both exist;
- the entire presented immutable lease equals the installed lease, covering
  owner, epoch, start, and expiry;
- authoritative logical time lies in the installed half-open interval.

Thus lower, higher, wrong-owner, altered-interval, not-yet-valid, and expired
tokens all return `FENCED`. A fence rejection changes neither the job nor
history. Nodes only return `NO_LEASE` when no token is held; apparent expiry is
sent to the queue so the authoritative rejection is observable and an already
accepted request can still take the history-first replay path.

## Request identity and evaluation order

A request's logical payload fingerprint is exactly
`(action, job_id, worker_id)`. It excludes owner, epoch, and lease interval.
Evaluation order is fixed:

1. Look up `command_id`.
2. If found and the payload is equal, return the same saved `Response` object.
3. If found and the payload differs, return `ID_CONFLICT` without mutation.
4. For an unseen ID, validate the full installed fence and logical tick.
5. If authorized, evaluate the business transition and save its payload and
   exact response, including nonmutating business outcomes.

This order lets an accepted logical request replay after failover without
re-evaluation, while a request that was only fenced can later be retried through
valid authority because fencing did not reserve its ID.

## Stable business response codes

| Action and prior state | Response | Job change |
|---|---|---|
| `CLAIM`, `READY` | `OK_CLAIMED` | to `CLAIMED(worker_id)` |
| `CLAIM`, claimed by same worker | `ALREADY_CLAIMED` | none |
| `CLAIM`, claimed by another worker | `CLAIMED_BY_OTHER` | none |
| `CLAIM`, done | `ALREADY_DONE` | none |
| `COMPLETE`, ready | `NOT_CLAIMED` | none |
| `COMPLETE`, claimed by same worker | `OK_DONE` | to `DONE(worker_id)` |
| `COMPLETE`, claimed by another worker | `NOT_OWNER` | none |
| `COMPLETE`, done by same worker | `ALREADY_DONE` | none |
| `COMPLETE`, done by another worker | `DONE_BY_OTHER` | none |

An unknown job takes precedence and returns `NOT_FOUND`. For a known job, an
unsupported action returns `INVALID`. Both are authorized business results and
are recorded. `FENCED`, `NO_LEASE`, and `ID_CONFLICT` do not create a new
history entry.

## Deterministic events and evidence

`EventRunner` stores immutable events in a heap ordered by
`(tick, insertion_index)`. The index is unique and monotonic, so object identity,
mapping order, and host scheduling cannot break ties. Pause and resume are
explicit trace markers; delivery, delay, loss, and duplication are expressed by
which submit events are scheduled and at which tick.

Every record starts with the required structured fields. Applicable records add
`insertion_index`, `history_changed`, `response_code`, payload, and lease
interval. Python `None` serializes to JSON `null`. Records are appended only
after the represented fact or decision, and no transition reads log content.
Replacing the collector with a compatible no-op emitter therefore does not
change state-machine decisions or responses.

Run all evidence from this directory with:

```bash
python3 -m unittest -v test_lease_queue.py
```

The suite covers the six public traces plus forged authority, no-lease rejection,
nonmutating-history stability, rollback, coordinator binding, common log fields,
and repeat-run equality.

## Non-goals and unavailable production prerequisites

This implementation does not use sockets, threads, subprocesses, wall clocks,
randomness, or persistent storage. It assumes trusted integer simulator time, a
single durable coordinator and queue, and indivisible Python method execution.
It does not address real-clock skew, process races, coordinator or storage
failover, crash recovery, disk corruption, Byzantine behavior, credential
security, multi-core memory ordering, or a real network. Making claims in those
areas would require authenticated fencing tokens, a replicated linearizable
authority, transactional durable storage and recovery tests, clock/lease
assumptions, concurrent stress and model checking, and fault-injected
multi-process evidence. Those production prerequisites were not available or
attempted in this bounded workspace.

> This submission models one locally authored epoch-fenced queue exercise. It does not implement a consensus protocol, establish production correctness, complete an official assignment, or claim course completion.
