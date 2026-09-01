"""Deterministic epoch-fenced work-queue semantic model.

The module intentionally uses only Python's standard library and logical ticks.
It models contracts and replayable traces; it is not a distributed lease service.
"""

from __future__ import print_function

import heapq
from typing import Any, Dict, Iterable, List, Mapping, NamedTuple, Optional, Tuple


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
        # Authority deliberately is not part of logical request identity.
        return (self.action, self.job_id, self.worker_id)


class Response(NamedTuple):
    code: str


class HistoryEntry(NamedTuple):
    payload: Tuple[str, str, str]
    response: Response


class JobState(NamedTuple):
    state: str
    worker_id: Optional[str]


class ScheduledEvent(NamedTuple):
    tick: int
    insertion_index: int
    event: str
    arguments: Tuple[Any, ...]


class EventResult(NamedTuple):
    tick: int
    insertion_index: int
    event: str
    value: Any


def _is_integer(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _lease_is_valid(lease, tick):
    return lease.start_tick <= tick < lease.expires_tick


def _job_record(job):
    if job is None:
        return None
    return {"state": job.state, "worker_id": job.worker_id}


class StructuredLog(object):
    """Append-only in-memory facts with a common queryable schema."""

    def __init__(self):
        self.records = []  # type: List[Dict[str, Any]]

    def emit(
        self,
        tick,
        event,
        decision,
        command_id=None,
        owner=None,
        epoch=None,
        active_lease=None,
        state_changed=False,
        job_before=None,
        job_after=None,
        insertion_index=None,
        **extra
    ):
        record = {
            "tick": tick,
            "event": event,
            "command_id": command_id,
            "owner": owner,
            "epoch": epoch,
            "active_owner": (
                active_lease.owner if active_lease is not None else None
            ),
            "active_epoch": (
                active_lease.epoch if active_lease is not None else None
            ),
            "decision": decision,
            "state_changed": bool(state_changed),
            "job_before": job_before,
            "job_after": job_after,
            "insertion_index": insertion_index,
        }
        record.update(extra)
        self.records.append(record)
        return record

    def truncate(self, length):
        del self.records[length:]


class DurableQueue(object):
    """Authoritative fence, job state, and request history."""

    def __init__(self, job_ids, audit_log=None):
        self.log = audit_log if audit_log is not None else StructuredLog()
        self._jobs = {}  # type: Dict[str, JobState]
        for job_id in job_ids:
            if job_id in self._jobs:
                raise ValueError("duplicate job_id: {0}".format(job_id))
            self._jobs[job_id] = JobState("READY", None)
        self._history = {}  # type: Dict[str, HistoryEntry]
        self._active_lease = None  # type: Optional[Lease]
        self._coordinator_token = None

    @property
    def active_lease(self):
        return self._active_lease

    @property
    def history(self):
        return dict(self._history)

    @property
    def jobs(self):
        return dict(self._jobs)

    def job_state(self, job_id):
        return self._jobs.get(job_id)

    def _bind_coordinator(self):
        if self._coordinator_token is not None:
            raise RuntimeError("queue already has a coordinator")
        self._coordinator_token = object()
        return self._coordinator_token

    def _validate_fence_install(self, lease, authority):
        if authority is not self._coordinator_token:
            raise PermissionError("only the bound coordinator may install a fence")
        if not isinstance(lease, Lease):
            raise TypeError("fence must be a Lease")
        if not _is_integer(lease.epoch) or lease.epoch <= 0:
            raise ValueError("epoch must be a positive integer")
        if not _is_integer(lease.start_tick) or not _is_integer(lease.expires_tick):
            raise ValueError("lease ticks must be integers")
        if lease.expires_tick <= lease.start_tick:
            raise ValueError("lease interval must be nonempty")
        expected_epoch = (
            1 if self._active_lease is None else self._active_lease.epoch + 1
        )
        if lease.epoch != expected_epoch:
            raise ValueError("fence epoch is not the next epoch")

    def _install_fence(self, lease, tick, authority, insertion_index=None):
        self._validate_fence_install(lease, authority)
        previous = self._active_lease
        self._active_lease = lease
        self.log.emit(
            tick=tick,
            event="fence_install",
            decision="INSTALLED",
            owner=lease.owner,
            epoch=lease.epoch,
            active_lease=lease,
            insertion_index=insertion_index,
            previous_active_owner=(
                previous.owner if previous is not None else None
            ),
            previous_active_epoch=(
                previous.epoch if previous is not None else None
            ),
            lease_start_tick=lease.start_tick,
            lease_expires_tick=lease.expires_tick,
            history_changed=False,
        )

    def _restore_fence(self, lease, authority):
        if authority is not self._coordinator_token:
            raise PermissionError("only the bound coordinator may restore a fence")
        self._active_lease = lease

    def _authority_fields(self, lease):
        return {
            "owner": getattr(lease, "owner", None),
            "epoch": getattr(lease, "epoch", None),
            "lease_start_tick": getattr(lease, "start_tick", None),
            "lease_expires_tick": getattr(lease, "expires_tick", None),
            "active_start_tick": (
                self._active_lease.start_tick
                if self._active_lease is not None
                else None
            ),
            "active_expires_tick": (
                self._active_lease.expires_tick
                if self._active_lease is not None
                else None
            ),
        }

    def _emit_request_fact(
        self,
        request,
        lease,
        tick,
        insertion_index,
        event,
        decision,
        before,
        after,
        state_changed,
        history_changed,
        response
    ):
        authority = self._authority_fields(lease)
        self.log.emit(
            tick=tick,
            event=event,
            decision=decision,
            command_id=request.command_id,
            owner=authority.pop("owner"),
            epoch=authority.pop("epoch"),
            active_lease=self._active_lease,
            state_changed=state_changed,
            job_before=_job_record(before),
            job_after=_job_record(after),
            insertion_index=insertion_index,
            history_changed=history_changed,
            response_code=response.code if response is not None else None,
            payload=list(request.payload),
            **authority
        )

    def apply(self, request, lease, tick, insertion_index=None):
        if not isinstance(request, Request):
            raise TypeError("request must be a Request")
        if not _is_integer(tick):
            raise ValueError("tick must be an integer")

        before = self._jobs.get(request.job_id)
        self._emit_request_fact(
            request,
            lease,
            tick,
            insertion_index,
            "queue_attempt",
            "RECEIVED",
            before,
            before,
            False,
            False,
            None,
        )

        historical = self._history.get(request.command_id)
        if historical is not None:
            current = self._jobs.get(request.job_id)
            if historical.payload == request.payload:
                self._emit_request_fact(
                    request,
                    lease,
                    tick,
                    insertion_index,
                    "replay",
                    "REPLAY",
                    current,
                    current,
                    False,
                    False,
                    historical.response,
                )
                # Return the exact saved Response object.
                return historical.response
            response = Response("ID_CONFLICT")
            self._emit_request_fact(
                request,
                lease,
                tick,
                insertion_index,
                "conflict",
                "ID_CONFLICT",
                current,
                current,
                False,
                False,
                response,
            )
            return response

        installed = self._active_lease
        authorized = (
            isinstance(lease, Lease)
            and installed is not None
            and lease == installed
            and _lease_is_valid(installed, tick)
        )
        if not authorized:
            response = Response("FENCED")
            current = self._jobs.get(request.job_id)
            self._emit_request_fact(
                request,
                lease,
                tick,
                insertion_index,
                "fence_rejection",
                "FENCED",
                current,
                current,
                False,
                False,
                response,
            )
            return response

        response, after, changed = self._evaluate(request, before)
        if before != after and request.job_id in self._jobs:
            self._jobs[request.job_id] = after
        self._history[request.command_id] = HistoryEntry(
            request.payload, response
        )
        self._emit_request_fact(
            request,
            lease,
            tick,
            insertion_index,
            "business_decision",
            response.code,
            before,
            after,
            changed,
            True,
            response,
        )
        return response

    def _evaluate(self, request, before):
        if before is None:
            return Response("NOT_FOUND"), None, False

        if request.action == "CLAIM":
            if before.state == "READY":
                after = JobState("CLAIMED", request.worker_id)
                return Response("OK_CLAIMED"), after, True
            if before.state == "CLAIMED":
                if before.worker_id == request.worker_id:
                    return Response("ALREADY_CLAIMED"), before, False
                return Response("CLAIMED_BY_OTHER"), before, False
            return Response("ALREADY_DONE"), before, False

        if request.action == "COMPLETE":
            if before.state == "READY":
                return Response("NOT_CLAIMED"), before, False
            if before.state == "CLAIMED":
                if before.worker_id != request.worker_id:
                    return Response("NOT_OWNER"), before, False
                after = JobState("DONE", request.worker_id)
                return Response("OK_DONE"), after, True
            return Response("ALREADY_DONE"), before, False

        return Response("INVALID"), before, False


class Coordinator(object):
    """The only model component holding queue fence-install authority."""

    def __init__(self, queue):
        self.queue = queue
        self.log = queue.log
        self._authority = queue._bind_coordinator()
        self.current = None  # type: Optional[Lease]
        self.epoch = 0

    def _emit(self, tick, event, decision, owner, epoch, insertion_index, **extra):
        self.log.emit(
            tick=tick,
            event=event,
            decision=decision,
            owner=owner,
            epoch=epoch,
            active_lease=self.queue.active_lease,
            insertion_index=insertion_index,
            history_changed=False,
            **extra
        )

    def grant(self, owner, tick, ttl, insertion_index=None):
        self._emit(
            tick,
            "grant_attempt",
            "RECEIVED",
            owner,
            None,
            insertion_index,
            requested_ttl=ttl,
        )
        if not _is_integer(tick):
            self._emit(
                tick,
                "grant_decision",
                "INVALID_TICK",
                owner,
                None,
                insertion_index,
                requested_ttl=ttl,
            )
            raise ValueError("tick must be an integer")
        if not _is_integer(ttl) or ttl <= 0:
            self._emit(
                tick,
                "grant_decision",
                "INVALID_TTL",
                owner,
                None,
                insertion_index,
                requested_ttl=ttl,
            )
            raise ValueError("ttl must be a positive integer")

        if self.current is not None and _lease_is_valid(self.current, tick):
            self._emit(
                tick,
                "grant_decision",
                "DENIED_ACTIVE",
                owner,
                self.current.epoch,
                insertion_index,
                requested_ttl=ttl,
            )
            return None

        candidate = Lease(owner, self.epoch + 1, tick, tick + ttl)
        old_current = self.current
        old_epoch = self.epoch
        old_fence = self.queue.active_lease
        install_log_boundary = len(self.log.records)
        try:
            self.queue._install_fence(
                candidate, tick, self._authority, insertion_index
            )
            self.current = candidate
            self.epoch = candidate.epoch
        except Exception as error:
            self.current = old_current
            self.epoch = old_epoch
            self.queue._restore_fence(old_fence, self._authority)
            self.log.truncate(install_log_boundary)
            self._emit(
                tick,
                "grant_decision",
                "INSTALL_FAILED",
                owner,
                candidate.epoch,
                insertion_index,
                requested_ttl=ttl,
                error_type=type(error).__name__,
            )
            raise

        self._emit(
            tick,
            "grant_decision",
            "GRANTED",
            owner,
            candidate.epoch,
            insertion_index,
            requested_ttl=ttl,
            lease_start_tick=candidate.start_tick,
            lease_expires_tick=candidate.expires_tick,
        )
        return candidate


class Node(object):
    """Dispatcher endpoint; the queue remains the authority."""

    def __init__(self, owner, queue):
        self.owner = owner
        self.queue = queue
        self.log = queue.log
        self.lease = None  # type: Optional[Lease]

    def receive_lease(self, lease, tick, insertion_index=None):
        if not isinstance(lease, Lease) or lease.owner != self.owner:
            raise ValueError("node may receive only its own lease")
        self.lease = lease
        self.log.emit(
            tick=tick,
            event="lease_received",
            decision="RECEIVED",
            owner=lease.owner,
            epoch=lease.epoch,
            active_lease=self.queue.active_lease,
            insertion_index=insertion_index,
            lease_start_tick=lease.start_tick,
            lease_expires_tick=lease.expires_tick,
            history_changed=False,
        )

    def pause(self, tick, insertion_index=None):
        # Network delivery is represented by scheduled events, so this is a
        # trace marker rather than a source of autonomous timing behavior.
        self.log.emit(
            tick=tick,
            event="node_pause",
            decision="PAUSED",
            owner=self.owner,
            epoch=self.lease.epoch if self.lease is not None else None,
            active_lease=self.queue.active_lease,
            insertion_index=insertion_index,
            history_changed=False,
        )

    def resume(self, tick, insertion_index=None):
        self.log.emit(
            tick=tick,
            event="node_resume",
            decision="RESUMED",
            owner=self.owner,
            epoch=self.lease.epoch if self.lease is not None else None,
            active_lease=self.queue.active_lease,
            insertion_index=insertion_index,
            history_changed=False,
        )

    def submit(self, request, tick, insertion_index=None):
        if self.lease is None:
            before = self.queue.job_state(request.job_id)
            response = Response("NO_LEASE")
            self.log.emit(
                tick=tick,
                event="node_rejection",
                decision="NO_LEASE",
                command_id=request.command_id,
                owner=self.owner,
                epoch=None,
                active_lease=self.queue.active_lease,
                state_changed=False,
                job_before=_job_record(before),
                job_after=_job_record(before),
                insertion_index=insertion_index,
                history_changed=False,
                response_code=response.code,
                payload=list(request.payload),
            )
            return response
        # Even an apparently expired token reaches the sink. This preserves
        # history-first replay while leaving unseen authority checks to Queue.
        return self.queue.apply(request, self.lease, tick, insertion_index)


class EventRunner(object):
    """Executes events strictly by (logical tick, insertion index)."""

    def __init__(self, coordinator, nodes):
        self.coordinator = coordinator
        self.nodes = dict(nodes)  # type: Dict[str, Node]
        self._pending = []  # type: List[ScheduledEvent]
        self._next_index = 0
        self.results = []  # type: List[EventResult]
        self._last_tick = None  # type: Optional[int]

        for owner, node in self.nodes.items():
            if owner != node.owner:
                raise ValueError("node mapping key must equal node owner")
            if node.queue is not coordinator.queue:
                raise ValueError("all nodes must use the coordinator queue")

    def _schedule(self, tick, event, arguments):
        if not _is_integer(tick):
            raise ValueError("event tick must be an integer")
        if self._last_tick is not None and tick < self._last_tick:
            raise ValueError("cannot schedule an event before executed time")
        insertion_index = self._next_index
        self._next_index += 1
        heapq.heappush(
            self._pending,
            ScheduledEvent(tick, insertion_index, event, arguments),
        )
        return insertion_index

    def schedule_grant(self, tick, owner, ttl):
        if owner not in self.nodes:
            raise KeyError("unknown node owner: {0}".format(owner))
        return self._schedule(tick, "grant", (owner, ttl))

    def schedule_submit(self, tick, owner, request):
        if owner not in self.nodes:
            raise KeyError("unknown node owner: {0}".format(owner))
        if not isinstance(request, Request):
            raise TypeError("request must be a Request")
        return self._schedule(tick, "submit", (owner, request))

    def schedule_pause(self, tick, owner):
        if owner not in self.nodes:
            raise KeyError("unknown node owner: {0}".format(owner))
        return self._schedule(tick, "pause", (owner,))

    def schedule_resume(self, tick, owner):
        if owner not in self.nodes:
            raise KeyError("unknown node owner: {0}".format(owner))
        return self._schedule(tick, "resume", (owner,))

    def run(self):
        while self._pending:
            scheduled = heapq.heappop(self._pending)
            self._last_tick = scheduled.tick
            value = None
            if scheduled.event == "grant":
                owner, ttl = scheduled.arguments
                value = self.coordinator.grant(
                    owner,
                    scheduled.tick,
                    ttl,
                    scheduled.insertion_index,
                )
                if value is not None:
                    self.nodes[owner].receive_lease(
                        value, scheduled.tick, scheduled.insertion_index
                    )
            elif scheduled.event == "submit":
                owner, request = scheduled.arguments
                value = self.nodes[owner].submit(
                    request,
                    scheduled.tick,
                    scheduled.insertion_index,
                )
            elif scheduled.event == "pause":
                owner = scheduled.arguments[0]
                self.nodes[owner].pause(
                    scheduled.tick, scheduled.insertion_index
                )
            elif scheduled.event == "resume":
                owner = scheduled.arguments[0]
                self.nodes[owner].resume(
                    scheduled.tick, scheduled.insertion_index
                )
            else:
                raise AssertionError("unknown scheduled event")
            self.results.append(
                EventResult(
                    scheduled.tick,
                    scheduled.insertion_index,
                    scheduled.event,
                    value,
                )
            )
        return list(self.results)

    def result_for(self, insertion_index):
        for result in self.results:
            if result.insertion_index == insertion_index:
                return result.value
        raise KeyError("event has not produced a result")


__all__ = [
    "Coordinator",
    "DurableQueue",
    "EventResult",
    "EventRunner",
    "HistoryEntry",
    "JobState",
    "Lease",
    "Node",
    "Request",
    "Response",
    "ScheduledEvent",
    "StructuredLog",
]
