# Learning Task: Repair and Implement ParcelQ

## Mission

Build a deterministic Python model of the ParcelQ lease, fence, and work-queue contract. Start by analyzing the unsafe excerpt below, then implement the specified behavior and demonstrate it with reproducible failure traces. This is a local exercise; do not fetch the linked course website, official materials, or solution repositories.

Use only the Python standard library. Do not use wall-clock time, sleeping, threads, randomness, subprocesses, or network access. Your model must produce the same state, responses, and ordered log for the same event list on every run.

## Intentionally unsafe excerpt

Treat this manager-authored excerpt as incident evidence, not as starter code to trust:

```python
class Coordinator:
    def grant(self, owner, tick, ttl):
        if self.current is not None and tick <= self.current.expires_tick:
            return None
        self.epoch += 1
        self.current = Lease(owner, self.epoch, tick, tick + ttl)
        return self.current

class Queue:
    def apply(self, request, lease, tick):
        response = self.transition(request)
        if request.command_id in self.history:
            return self.history[request.command_id]
        if lease.epoch < self.active_epoch:
            return Response("FENCED")
        self.active_epoch = lease.epoch
        self.history[request.command_id] = response
        return response

class Node:
    def submit(self, request, tick):
        if self.lease is None or tick > self.lease.expires_tick:
            return Response("NO_LEASE")
        return self.queue.apply(request, self.lease, tick)
```

Before rewriting it, capture at least three distinct hypotheses about how a stale or duplicate command could produce an incorrect or misleading outcome. Test each hypothesis with the smallest deterministic trace you can construct.

## Required contract

### Lease and grant

Represent a lease as immutable fields `owner`, `epoch`, `start_tick`, and `expires_tick`. Require a positive integer TTL. A lease is valid only on `[start_tick, expires_tick)`.

A grant attempted while the current lease is valid is denied without consuming an epoch or changing the queue’s active fence. At or after expiry, a successful grant uses the next epoch. Installing that exact lease in the queue and making it the coordinator’s current lease occur as one atomic model action before the lease is returned. If validation or installation fails, neither object may expose a partial grant.

The model’s trust boundary permits only the coordinator to call the queue’s fence-install operation. Document that this is a model assumption, not cryptographic enforcement.

### Queue authority checks

For every unseen logical request, the queue—not merely the node—must require all of the following at the supplied logical tick:

- the presented lease exactly matches the installed fence’s owner and epoch;
- the lease interval exactly matches the installed lease;
- the tick is inside the installed half-open interval.

A token with a lower, higher, wrong-owner, altered-interval, not-yet-valid, or expired value is `FENCED`. A fenced attempt must not mutate job state or create a request-history entry. The node may reject an obviously unusable local lease early, but sink-side checks remain authoritative.

### Request history

A request has `command_id`, `action`, `job_id`, and `worker_id`. The logical payload fingerprint is exactly `(action, job_id, worker_id)`.

When a history entry already exists, compare the payload before checking the caller’s current lease:

- the same ID and same payload returns the exact historical response without mutation;
- the same ID with a different payload returns `ID_CONFLICT` without mutation or replacement of the original entry.

This ordering applies even after a newer fence is installed. Fence rejections are not entered in history, so an operation that never reached the state machine may later be retried through a valid dispatcher using the same logical identity.

### Job transitions

Initialize named jobs in state `READY`. Support these actions:

- `CLAIM`: `READY` becomes `CLAIMED(worker_id)` and returns `OK_CLAIMED`. Repeating the semantic operation against an already claimed or completed job returns a descriptive nonmutating response.
- `COMPLETE`: `CLAIMED(worker_id)` becomes `DONE(worker_id)` and returns `OK_DONE`. A ready job, a claim owned by another worker, or an already completed job returns a descriptive nonmutating response.

Use stable response codes of your choice for the descriptive cases and document them. An unknown job returns `NOT_FOUND`. An unsupported action returns `INVALID`. Once a request passes the fence and is evaluated by the job state machine, record its payload and exact response even when the business result is nonmutating. Only `FENCED`, an early node-side `NO_LEASE`, and `ID_CONFLICT` lack a new history entry.

### Deterministic events and observability

Represent event order with `(tick, insertion_index)`. The insertion index must be monotonic and must break same-tick ties; never rely on a set, map iteration, object identity, or scheduler accident. Network delay, loss, duplication, and pause/resume are modeled by the events the test schedules and delivers.

Emit an ordered structured record for every grant attempt, fence installation, node rejection, queue attempt, replay, conflict, and business decision. Each applicable record should make these fields queryable without parsing prose:

`tick`, `event`, `command_id`, `owner`, `epoch`, `active_owner`, `active_epoch`, `decision`, `state_changed`, `job_before`, and `job_after`.

Use `null` for inapplicable values. Logs must reflect decisions already made and must not alter behavior.

## Minimum public traces

Write deterministic `unittest` coverage for at least these scenarios:

1. A dispatcher pauses, its lease expires, a new dispatcher receives the next fence, and the old dispatcher’s previously unseen delayed command is rejected without mutation.
2. The same accepted request is delivered twice and causes one state transition while returning a stable historical response.
3. The same command ID is reused with a different payload and the original history and job state remain intact.
4. A historical request is replayed after a newer fence and returns its original response without reverting newer job state.
5. A grant attempted one tick before expiry is denied without an epoch gap; a grant exactly at expiry succeeds.
6. Two business events at the same tick execute in insertion order, and the structured log makes the winning order visible.

For each trace, assert responses, state, history size or contents, active fence, and relevant log landmarks. Assertions only on “no exception” or final state are insufficient.

## Learner deliverables

Preserve these four artifacts in your submission area:

- `lease_queue.py`: the model and deterministic event runner;
- `test_lease_queue.py`: runnable standard-library `unittest` tests;
- `DESIGN.md`: the state, request-history, lease/fence, atomicity, and trust-boundary contract plus explicit non-goals;
- `INCIDENT.md`: at least three hypothesis → experiment → observation → revision cycles based on the unsafe excerpt, including exact commands used and relevant structured log excerpts.

Include a command such as `python3 -m unittest -v test_lease_queue.py` that runs from a clean copy of the submission. Tests must not depend on files outside the submission, execution order, locale, current date, or network state.

End `DESIGN.md` with this exact scope statement:

> This submission models one locally authored epoch-fenced queue exercise. It does not implement a consensus protocol, establish production correctness, complete an official assignment, or claim course completion.

## Stop rule

Stop at the hard timebox even if some tests remain red. Preserve the smallest reproducer, actual output, current hypothesis, and next diagnostic step. Do not hide or rewrite failed evidence as success.
