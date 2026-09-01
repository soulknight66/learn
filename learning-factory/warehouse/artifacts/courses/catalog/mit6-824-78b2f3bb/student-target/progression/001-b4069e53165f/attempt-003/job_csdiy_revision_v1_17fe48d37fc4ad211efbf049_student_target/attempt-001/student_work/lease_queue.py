"""Deterministic semantic model for the bounded ParcelQ exercise.

The model deliberately uses logical integer ticks and a single event loop.  It
does not use wall-clock time, threads, subprocesses, randomness, or I/O.
"""

from __future__ import absolute_import

import heapq
from typing import Any, Dict, Iterable, List, NamedTuple, Optional, Tuple


class Lease(NamedTuple):
    owner: str
    epoch: int
    start_tick: int
    expires_tick: int


class Request(NamedTuple):
    command_id: str
    action: str
    job_id: str
    worker_id: str

    @property
    def payload(self):
        # Authority metadata is intentionally absent from logical identity.
        return (self.action, self.job_id, self.worker_id)


class Response(NamedTuple):
    code: str


class JobState(NamedTuple):
    status: str
    worker_id: Optional[str]


class HistoryEntry(NamedTuple):
    payload: Tuple[str, str, str]
    response: Response


class EventOutcome(NamedTuple):
    tick: int
    insertion_index: int
    kind: str
    value: Any


READY = "READY"
CLAIMED = "CLAIMED"
DONE = "DONE"


RECORD_FIELDS = (
    "tick",
    "insertion_index",
    "event",
    "command_id",
    "owner",
    "epoch",
    "active_owner",
    "active_epoch",
    "decision",
    "state_changed",
    "history_changed",
    "job_before",
    "job_after",
    "response_code",
    "payload",
    "presented_start_tick",
    "presented_expires_tick",
    "active_start_tick",
    "active_expires_tick",
)


def _job_view(state):
    if state is None:
        return None
    return {"status": state.status, "worker_id": state.worker_id}


def _authority_fields(presented, active):
    return {
        "owner": getattr(presented, "owner", None),
        "epoch": getattr(presented, "epoch", None),
        "presented_start_tick": getattr(presented, "start_tick", None),
        "presented_expires_tick": getattr(presented, "expires_tick", None),
        "active_owner": getattr(active, "owner", None),
        "active_epoch": getattr(active, "epoch", None),
        "active_start_tick": getattr(active, "start_tick", None),
        "active_expires_tick": getattr(active, "expires_tick", None),
    }


def _require_tick(tick):
    if type(tick) is not int:
        raise ValueError("tick must be an integer")


class AuditLog(object):
    """Append-only ordered structured records used only for observability."""

    def __init__(self):
        self.records = []  # type: List[Dict[str, Any]]

    def make(self, **fields):
        record = dict((name, None) for name in RECORD_FIELDS)
        record.update(fields)
        return record

    def emit(self, **fields):
        record = self.make(**fields)
        self.records.append(record)
        return record

    def append(self, record):
        self.records.append(record)

    def truncate(self, length):
        del self.records[length:]


class DurableQueue(object):
    """Authoritative fence, request history, and job state machine."""

    def __init__(self, job_ids, audit=None):
        # Constructing in input order avoids depending on set iteration.
        self._jobs = {}  # type: Dict[str, JobState]
        for job_id in job_ids:  # type: str
            self._jobs[job_id] = JobState(READY, None)
        self._history = {}  # type: Dict[str, HistoryEntry]
        self._active_lease = None  # type: Optional[Lease]
        self._coordinator = None
        self.audit = audit if audit is not None else AuditLog()

    @property
    def active_lease(self):
        return self._active_lease

    @property
    def history(self):
        return self._history

    @property
    def jobs(self):
        return self._jobs

    def job_state(self, job_id):
        return self._jobs.get(job_id)

    def _bind_coordinator(self, coordinator):
        if self._coordinator is not None and self._coordinator is not coordinator:
            raise RuntimeError("queue already has a coordinator")
        self._coordinator = coordinator

    def _install_fence(self, lease, tick, caller, insertion_index=None):
        """Install a fence for the bound coordinator and return its log record.

        The identity check is an in-process model guard.  It is not a
        cryptographic capability and is not presented as one.
        """
        if caller is not self._coordinator:
            raise PermissionError("only the bound coordinator may install a fence")
        if not isinstance(lease, Lease):
            raise ValueError("fence must be a Lease")
        if lease.start_tick != tick or lease.expires_tick <= lease.start_tick:
            raise ValueError("invalid lease interval")
        expected_epoch = 1 if self._active_lease is None else self._active_lease.epoch + 1
        if lease.epoch != expected_epoch:
            raise ValueError("fence epoch is not the next epoch")

        self._active_lease = lease
        fields = _authority_fields(lease, lease)
        fields.update(
            tick=tick,
            insertion_index=insertion_index,
            event="fence_install",
            decision="INSTALLED",
            state_changed=False,
            history_changed=False,
        )
        # Coordinator appends this only after both authority objects commit.
        return self.audit.make(**fields)

    def _restore_fence(self, lease):
        self._active_lease = lease

    def apply(self, request, lease, tick, insertion_index=None):
        """Apply one delivered request using history-first authority ordering."""
        _require_tick(tick)
        before = self._jobs.get(request.job_id)
        common = _authority_fields(lease, self._active_lease)
        common.update(
            tick=tick,
            insertion_index=insertion_index,
            command_id=request.command_id,
            payload=request.payload,
            job_before=_job_view(before),
            job_after=_job_view(before),
            state_changed=False,
            history_changed=False,
        )

        attempt = dict(common)
        attempt.update(event="queue_attempt", decision="RECEIVED")
        self.audit.emit(**attempt)

        existing = self._history.get(request.command_id)
        if existing is not None:
            if existing.payload == request.payload:
                replay = dict(common)
                replay.update(
                    event="replay",
                    decision="REPLAY",
                    response_code=existing.response.code,
                )
                self.audit.emit(**replay)
                # This is the exact response value stored on first evaluation.
                return existing.response

            conflict = dict(common)
            conflict.update(
                event="conflict",
                decision="ID_CONFLICT",
                response_code="ID_CONFLICT",
                original_payload=existing.payload,
            )
            self.audit.emit(**conflict)
            return Response("ID_CONFLICT")

        active = self._active_lease
        authorized = (
            isinstance(lease, Lease)
            and active is not None
            and lease == active
            and active.start_tick <= tick < active.expires_tick
        )
        if not authorized:
            fenced = dict(common)
            fenced.update(
                event="fence_rejection",
                decision="FENCED",
                response_code="FENCED",
            )
            self.audit.emit(**fenced)
            return Response("FENCED")

        response, after = self._evaluate(request, before)
        changed = after != before
        if changed:
            self._jobs[request.job_id] = after
        self._history[request.command_id] = HistoryEntry(request.payload, response)

        business = dict(common)
        business.update(
            event="business_decision",
            decision=response.code,
            response_code=response.code,
            state_changed=changed,
            history_changed=True,
            job_after=_job_view(after),
        )
        self.audit.emit(**business)
        return response

    def _evaluate(self, request, before):
        if request.action not in ("CLAIM", "COMPLETE"):
            return Response("INVALID"), before
        if before is None:
            return Response("NOT_FOUND"), before

        if request.action == "CLAIM":
            if before.status == READY:
                return Response("OK_CLAIMED"), JobState(CLAIMED, request.worker_id)
            if before.status == CLAIMED:
                if before.worker_id == request.worker_id:
                    return Response("ALREADY_CLAIMED"), before
                return Response("CLAIMED_BY_OTHER"), before
            return Response("ALREADY_DONE"), before

        if before.status == READY:
            return Response("NOT_CLAIMED"), before
        if before.status == CLAIMED:
            if before.worker_id != request.worker_id:
                return Response("NOT_OWNER"), before
            return Response("OK_DONE"), JobState(DONE, request.worker_id)
        return Response("ALREADY_DONE"), before


class Coordinator(object):
    """Grants monotonically fenced leases as one non-interleaved model action."""

    def __init__(self, queue):
        self.queue = queue
        self.audit = queue.audit
        self._epoch = 0
        self._current = None  # type: Optional[Lease]
        queue._bind_coordinator(self)

    @property
    def epoch(self):
        return self._epoch

    @property
    def current(self):
        return self._current

    def grant(self, owner, tick, ttl, insertion_index=None):
        _require_tick(tick)
        active = self.queue.active_lease

        if type(ttl) is not int or ttl <= 0:
            fields = _authority_fields(None, active)
            fields.update(
                tick=tick,
                insertion_index=insertion_index,
                event="grant_attempt",
                owner=owner,
                decision="INVALID_TTL",
                state_changed=False,
                history_changed=False,
            )
            self.audit.emit(**fields)
            raise ValueError("ttl must be a positive integer")

        # Ordered logical time is assumed.  This also safely denies a rewind to
        # before the current start rather than issuing overlapping authority.
        if self._current is not None and tick < self._current.expires_tick:
            fields = _authority_fields(None, active)
            fields.update(
                tick=tick,
                insertion_index=insertion_index,
                event="grant_attempt",
                owner=owner,
                decision="DENIED_CURRENT_LEASE",
                state_changed=False,
                history_changed=False,
            )
            self.audit.emit(**fields)
            return None

        candidate = Lease(owner, self._epoch + 1, tick, tick + ttl)
        old_epoch = self._epoch
        old_current = self._current
        old_fence = self.queue.active_lease
        old_log_length = len(self.audit.records)

        try:
            fence_record = self.queue._install_fence(
                candidate, tick, self, insertion_index=insertion_index
            )
            self._epoch = candidate.epoch
            self._current = candidate
        except Exception:
            self._epoch = old_epoch
            self._current = old_current
            self.queue._restore_fence(old_fence)
            self.audit.truncate(old_log_length)
            fields = _authority_fields(None, old_fence)
            fields.update(
                tick=tick,
                insertion_index=insertion_index,
                event="grant_attempt",
                owner=owner,
                epoch=candidate.epoch,
                decision="INSTALL_FAILED",
                state_changed=False,
                history_changed=False,
            )
            self.audit.emit(**fields)
            raise

        fields = _authority_fields(candidate, candidate)
        fields.update(
            tick=tick,
            insertion_index=insertion_index,
            event="grant_attempt",
            decision="GRANTED",
            state_changed=False,
            history_changed=False,
        )
        self.audit.emit(**fields)
        self.audit.append(fence_record)
        return candidate


class Node(object):
    """Dispatcher facade; the queue remains the authoritative checker."""

    def __init__(self, owner, queue):
        self.owner = owner
        self.queue = queue
        self.lease = None  # type: Optional[Lease]

    def install_lease(self, lease):
        self.lease = lease

    def submit(self, request, tick, insertion_index=None):
        _require_tick(tick)
        if self.lease is None:
            before = self.queue.job_state(request.job_id)
            fields = _authority_fields(None, self.queue.active_lease)
            fields.update(
                tick=tick,
                insertion_index=insertion_index,
                event="node_rejection",
                command_id=request.command_id,
                node_owner=self.owner,
                payload=request.payload,
                decision="NO_LEASE",
                response_code="NO_LEASE",
                state_changed=False,
                history_changed=False,
                job_before=_job_view(before),
                job_after=_job_view(before),
            )
            self.queue.audit.emit(**fields)
            return Response("NO_LEASE")

        # Even an apparently stale or expired token is sent to the sink.  That
        # preserves the required history-first replay semantics.
        return self.queue.apply(
            request, self.lease, tick, insertion_index=insertion_index
        )


class _ScheduledEvent(object):
    __slots__ = ("tick", "insertion_index", "kind", "data")

    def __init__(self, tick, insertion_index, kind, data):
        self.tick = tick
        self.insertion_index = insertion_index
        self.kind = kind
        self.data = data

    def __lt__(self, other):
        return (self.tick, self.insertion_index) < (
            other.tick,
            other.insertion_index,
        )


class EventRunner(object):
    """Deterministic event scheduler ordered only by (tick, insertion_index)."""

    def __init__(self, coordinator, queue):
        if coordinator.queue is not queue:
            raise ValueError("coordinator and runner must use the same queue")
        self.coordinator = coordinator
        self.queue = queue
        self.nodes = {}  # type: Dict[str, Node]
        self._events = []  # type: List[_ScheduledEvent]
        self._next_index = 0
        self.outcomes = []  # type: List[EventOutcome]

    def add_node(self, owner):
        node = self.nodes.get(owner)
        if node is None:
            node = Node(owner, self.queue)
            self.nodes[owner] = node
        return node

    def _schedule(self, tick, kind, data):
        _require_tick(tick)
        index = self._next_index
        self._next_index += 1
        heapq.heappush(self._events, _ScheduledEvent(tick, index, kind, data))
        return index

    def schedule_grant(self, tick, owner, ttl):
        return self._schedule(tick, "grant", (owner, ttl))

    def schedule_delivery(self, tick, node_owner, request):
        return self._schedule(tick, "delivery", (node_owner, request))

    def run(self):
        while self._events:
            event = heapq.heappop(self._events)
            if event.kind == "grant":
                owner, ttl = event.data
                value = self.coordinator.grant(
                    owner,
                    event.tick,
                    ttl,
                    insertion_index=event.insertion_index,
                )
                if value is not None:
                    self.add_node(owner).install_lease(value)
            elif event.kind == "delivery":
                owner, request = event.data
                value = self.add_node(owner).submit(
                    request,
                    event.tick,
                    insertion_index=event.insertion_index,
                )
            else:
                raise AssertionError("unknown scheduled event kind")
            self.outcomes.append(
                EventOutcome(
                    event.tick, event.insertion_index, event.kind, value
                )
            )
        return list(self.outcomes)


__all__ = [
    "AuditLog",
    "Coordinator",
    "DONE",
    "DurableQueue",
    "EventOutcome",
    "EventRunner",
    "HistoryEntry",
    "JobState",
    "Lease",
    "Node",
    "Request",
    "Response",
    "CLAIMED",
    "READY",
]
