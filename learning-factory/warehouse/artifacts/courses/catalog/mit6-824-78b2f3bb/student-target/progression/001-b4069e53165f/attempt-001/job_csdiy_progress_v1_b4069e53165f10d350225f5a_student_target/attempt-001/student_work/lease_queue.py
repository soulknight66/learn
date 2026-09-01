"""Deterministic semantic model for the locally authored ParcelQ exercise.

The module intentionally uses logical time and a single-process event runner.  It
is a model of lease fencing, not a network service or a consensus protocol.

Provenance: locally authored from UNIT_BRIEF.md, LEARNING_TASK.md, and
SELF_CHECK.md only.  Validation label: SELF-VALIDATED by test_lease_queue.py;
independent validation is not claimed.
"""

import heapq
import json
from typing import Any, Dict, Iterable, List, NamedTuple, Optional, Tuple


def _is_plain_int(value: object) -> bool:
    """Return true for integers but not bool, which is an int subclass."""

    return type(value) is int


class Lease(NamedTuple):
    owner: str
    epoch: int
    start_tick: int
    expires_tick: int

    def valid_at(self, tick: int) -> bool:
        return self.start_tick <= tick < self.expires_tick


class Request(NamedTuple):
    command_id: str
    action: str
    job_id: str
    worker_id: str

    @property
    def payload(self) -> Tuple[str, str, str]:
        """Logical identity deliberately excludes lease authority metadata."""

        return (self.action, self.job_id, self.worker_id)


class Response(NamedTuple):
    code: str


class JobState(NamedTuple):
    status: str
    worker_id: Optional[str]


class HistoryEntry(NamedTuple):
    payload: Tuple[str, str, str]
    response: Response


class StructuredLog:
    """Append-only structured records shared by all model components."""

    REQUIRED_FIELDS = (
        "tick",
        "event",
        "command_id",
        "owner",
        "epoch",
        "active_owner",
        "active_epoch",
        "decision",
        "state_changed",
        "job_before",
        "job_after",
    )

    def __init__(self) -> None:
        self.records = []  # type: List[Dict[str, Any]]

    def emit(self, **values: Any) -> Dict[str, Any]:
        record = {name: None for name in self.REQUIRED_FIELDS}
        record.update(values)
        self.records.append(record)
        return record

    def to_json(self) -> str:
        return json.dumps(self.records, indent=2, sort_keys=True)


def _job_view(state: Optional[JobState]) -> Optional[Dict[str, Optional[str]]]:
    if state is None:
        return None
    return {"status": state.status, "worker_id": state.worker_id}


class DurableQueue:
    """Authoritative sink for fences, request history, and job transitions."""

    def __init__(
        self, job_ids: Iterable[str], log: Optional[StructuredLog] = None
    ) -> None:
        ids = list(job_ids)
        if any(not isinstance(job_id, str) or not job_id for job_id in ids):
            raise ValueError("job IDs must be non-empty strings")
        if len(set(ids)) != len(ids):
            raise ValueError("job IDs must be unique")
        self.log = log if log is not None else StructuredLog()
        self.jobs = {  # type: Dict[str, JobState]
            job_id: JobState("READY", None) for job_id in ids
        }
        self.history = {}  # type: Dict[str, HistoryEntry]
        self._active_lease = None  # type: Optional[Lease]
        self._coordinator = None  # type: Optional[Coordinator]

    @property
    def active_lease(self) -> Optional[Lease]:
        return self._active_lease

    @property
    def active_owner(self) -> Optional[str]:
        return None if self._active_lease is None else self._active_lease.owner

    @property
    def active_epoch(self) -> Optional[int]:
        return None if self._active_lease is None else self._active_lease.epoch

    def _bind_coordinator(self, coordinator: "Coordinator") -> None:
        if self._coordinator is not None and self._coordinator is not coordinator:
            raise RuntimeError("queue already has a coordinator")
        self._coordinator = coordinator

    def _validate_fence_install(
        self, lease: Lease, coordinator: "Coordinator"
    ) -> None:
        if coordinator is not self._coordinator:
            raise PermissionError("only the bound coordinator may install a fence")
        if (
            not isinstance(lease.owner, str)
            or not lease.owner
            or not _is_plain_int(lease.epoch)
            or lease.epoch <= 0
            or not _is_plain_int(lease.start_tick)
            or not _is_plain_int(lease.expires_tick)
            or lease.start_tick < 0
            or lease.expires_tick <= lease.start_tick
        ):
            raise ValueError("invalid lease")
        expected_epoch = 1 if self._active_lease is None else self._active_lease.epoch + 1
        if lease.epoch != expected_epoch:
            raise ValueError("fence epoch is not the next epoch")

    def _install_fence(
        self,
        lease: Lease,
        tick: int,
        coordinator: "Coordinator",
        insertion_index: Optional[int],
    ) -> None:
        """Install a validated fence.

        This private capability boundary is a model convention.  It is not
        cryptographic protection against hostile Python code.
        """

        self._validate_fence_install(lease, coordinator)
        self._active_lease = lease
        self.log.emit(
            tick=tick,
            event="fence_install",
            owner=lease.owner,
            epoch=lease.epoch,
            active_owner=lease.owner,
            active_epoch=lease.epoch,
            decision="INSTALLED",
            state_changed=True,
            insertion_index=insertion_index,
            start_tick=lease.start_tick,
            expires_tick=lease.expires_tick,
            history_changed=False,
        )

    def _rollback_fence(
        self,
        old_lease: Optional[Lease],
        log_length: int,
        coordinator: "Coordinator",
    ) -> None:
        if coordinator is not self._coordinator:
            raise PermissionError("only the bound coordinator may roll back")
        self._active_lease = old_lease
        del self.log.records[log_length:]

    def _authority_fields(self) -> Dict[str, object]:
        return {
            "active_owner": self.active_owner,
            "active_epoch": self.active_epoch,
        }

    def apply(
        self,
        request: Request,
        lease: Optional[Lease],
        tick: int,
        insertion_index: Optional[int] = None,
    ) -> Response:
        if not isinstance(request, Request):
            raise TypeError("request must be a Request")
        if not _is_plain_int(tick) or tick < 0:
            raise ValueError("tick must be a non-negative integer")

        before = self.jobs.get(request.job_id)
        presented_owner = None if lease is None else lease.owner
        presented_epoch = None if lease is None else lease.epoch
        common = {
            "tick": tick,
            "command_id": request.command_id,
            "owner": presented_owner,
            "epoch": presented_epoch,
            "job_before": _job_view(before),
            "job_after": _job_view(before),
            "insertion_index": insertion_index,
            "payload": list(request.payload),
            **self._authority_fields(),
        }
        self.log.emit(
            event="queue_attempt",
            decision="RECEIVED",
            state_changed=False,
            history_changed=False,
            **common,
        )

        historical = self.history.get(request.command_id)
        if historical is not None:
            if historical.payload == request.payload:
                self.log.emit(
                    event="replay",
                    decision="REPLAY",
                    response_code=historical.response.code,
                    state_changed=False,
                    history_changed=False,
                    **common,
                )
                return historical.response
            response = Response("ID_CONFLICT")
            self.log.emit(
                event="conflict",
                decision=response.code,
                response_code=response.code,
                original_payload=list(historical.payload),
                state_changed=False,
                history_changed=False,
                **common,
            )
            return response

        # Equality checks owner, epoch, start, and expiry.  The authoritative
        # validity check uses the installed interval, not caller-supplied time.
        authority_matches = (
            lease is not None
            and self._active_lease is not None
            and lease == self._active_lease
            and self._active_lease.valid_at(tick)
        )
        if not authority_matches:
            response = Response("FENCED")
            self.log.emit(
                event="queue_decision",
                decision=response.code,
                response_code=response.code,
                state_changed=False,
                history_changed=False,
                **common,
            )
            return response

        response, after = self._transition(request, before)
        state_changed = after != before
        if state_changed:
            # after cannot be None on a mutating transition.
            assert after is not None
            self.jobs[request.job_id] = after
        self.history[request.command_id] = HistoryEntry(
            request.payload, response
        )
        self.log.emit(
            event="business_decision",
            decision=response.code,
            response_code=response.code,
            state_changed=state_changed,
            history_changed=True,
            job_after=_job_view(after),
            **{key: value for key, value in common.items() if key != "job_after"},
        )
        return response

    @staticmethod
    def _transition(
        request: Request, before: Optional[JobState]
    ) -> Tuple[Response, Optional[JobState]]:
        # Unknown-job precedence is intentional and documented in DESIGN.md.
        if before is None:
            return Response("NOT_FOUND"), before
        if request.action not in {"CLAIM", "COMPLETE"}:
            return Response("INVALID"), before

        if request.action == "CLAIM":
            if before.status == "READY":
                return Response("OK_CLAIMED"), JobState("CLAIMED", request.worker_id)
            if before.status == "CLAIMED":
                if before.worker_id == request.worker_id:
                    return Response("ALREADY_CLAIMED"), before
                return Response("CLAIMED_BY_OTHER"), before
            return Response("ALREADY_DONE"), before

        if before.status == "READY":
            return Response("NOT_CLAIMED"), before
        if before.status == "CLAIMED":
            if before.worker_id != request.worker_id:
                return Response("NOT_OWNER"), before
            return Response("OK_DONE"), JobState("DONE", request.worker_id)
        if before.worker_id == request.worker_id:
            return Response("ALREADY_DONE"), before
        return Response("DONE_BY_OTHER"), before


class Coordinator:
    """Sole model authority that grants leases and installs queue fences."""

    def __init__(self, queue: DurableQueue) -> None:
        self.queue = queue
        self.log = queue.log
        self.current = None  # type: Optional[Lease]
        self.epoch = 0
        queue._bind_coordinator(self)

    def _active_fields(self) -> Dict[str, object]:
        return {
            "active_owner": self.queue.active_owner,
            "active_epoch": self.queue.active_epoch,
        }

    def grant(
        self,
        owner: str,
        tick: int,
        ttl: int,
        insertion_index: Optional[int] = None,
    ) -> Optional[Lease]:
        self.log.emit(
            tick=tick,
            event="grant_attempt",
            owner=owner,
            decision="RECEIVED",
            state_changed=False,
            history_changed=False,
            insertion_index=insertion_index,
            **self._active_fields(),
        )

        if not isinstance(owner, str) or not owner:
            self._invalid_grant(owner, tick, "INVALID_OWNER", insertion_index)
            raise ValueError("owner must be a non-empty string")
        if not _is_plain_int(tick) or tick < 0:
            self._invalid_grant(owner, tick, "INVALID_TICK", insertion_index)
            raise ValueError("tick must be a non-negative integer")
        if not _is_plain_int(ttl) or ttl <= 0:
            self._invalid_grant(owner, tick, "INVALID_TTL", insertion_index)
            raise ValueError("ttl must be a positive integer")
        if self.current is not None and tick < self.current.start_tick:
            self._invalid_grant(owner, tick, "TIME_REGRESSION", insertion_index)
            raise ValueError("grant tick precedes the current lease")

        if self.current is not None and self.current.valid_at(tick):
            self.log.emit(
                tick=tick,
                event="grant_decision",
                owner=owner,
                epoch=self.current.epoch,
                decision="DENIED_ACTIVE",
                state_changed=False,
                history_changed=False,
                insertion_index=insertion_index,
                **self._active_fields(),
            )
            return None

        next_epoch = self.epoch + 1
        lease = Lease(owner, next_epoch, tick, tick + ttl)
        old_active = self.queue.active_lease
        old_current = self.current
        old_epoch = self.epoch
        # Keep the received-attempt record, but remove any partial install log
        # if an exception occurs during this indivisible model action.
        rollback_log_length = len(self.log.records)
        try:
            self.queue._install_fence(
                lease, tick, self, insertion_index=insertion_index
            )
            self.current = lease
            self.epoch = next_epoch
            self.log.emit(
                tick=tick,
                event="grant_decision",
                owner=owner,
                epoch=next_epoch,
                decision="GRANTED",
                state_changed=True,
                history_changed=False,
                insertion_index=insertion_index,
                start_tick=lease.start_tick,
                expires_tick=lease.expires_tick,
                **self._active_fields(),
            )
        except Exception:
            self.queue._rollback_fence(old_active, rollback_log_length, self)
            self.current = old_current
            self.epoch = old_epoch
            self.log.emit(
                tick=tick,
                event="grant_decision",
                owner=owner,
                decision="INSTALL_FAILED",
                state_changed=False,
                history_changed=False,
                insertion_index=insertion_index,
                **self._active_fields(),
            )
            raise
        return lease

    def _invalid_grant(
        self,
        owner: object,
        tick: object,
        decision: str,
        insertion_index: Optional[int],
    ) -> None:
        self.log.emit(
            tick=tick,
            event="grant_decision",
            owner=owner,
            decision=decision,
            state_changed=False,
            history_changed=False,
            insertion_index=insertion_index,
            **self._active_fields(),
        )


class Node:
    """Dispatcher holding a lease; the queue remains the authority."""

    def __init__(self, owner: str, queue: DurableQueue) -> None:
        if not isinstance(owner, str) or not owner:
            raise ValueError("owner must be a non-empty string")
        self.owner = owner
        self.queue = queue
        self.lease = None  # type: Optional[Lease]

    def receive_lease(
        self,
        lease: Lease,
        tick: int,
        insertion_index: Optional[int] = None,
    ) -> None:
        if lease.owner != self.owner:
            raise ValueError("node cannot receive another owner's lease")
        self.lease = lease
        self.queue.log.emit(
            tick=tick,
            event="lease_received",
            owner=lease.owner,
            epoch=lease.epoch,
            active_owner=self.queue.active_owner,
            active_epoch=self.queue.active_epoch,
            decision="RECEIVED",
            state_changed=False,
            history_changed=False,
            insertion_index=insertion_index,
        )

    def submit(
        self,
        request: Request,
        tick: int,
        insertion_index: Optional[int] = None,
    ) -> Response:
        if self.lease is None:
            response = Response("NO_LEASE")
            before = self.queue.jobs.get(request.job_id)
            self.queue.log.emit(
                tick=tick,
                event="node_rejection",
                command_id=request.command_id,
                owner=self.owner,
                active_owner=self.queue.active_owner,
                active_epoch=self.queue.active_epoch,
                decision=response.code,
                response_code=response.code,
                state_changed=False,
                history_changed=False,
                job_before=_job_view(before),
                job_after=_job_view(before),
                insertion_index=insertion_index,
            )
            return response
        # Deliberately defer even an apparent local expiry to the queue.  This
        # keeps sink-side validation observable and permits history-first replay.
        return self.queue.apply(request, self.lease, tick, insertion_index)


class ScheduledEvent(NamedTuple):
    tick: int
    insertion_index: int
    kind: str
    node: Node
    ttl: Optional[int]
    request: Optional[Request]


class EventRunner:
    """Orders every scheduled event by ``(tick, insertion_index)``."""

    def __init__(self, coordinator: Coordinator) -> None:
        self.coordinator = coordinator
        self.log = coordinator.log
        self._events = []  # type: List[ScheduledEvent]
        self._next_index = 0
        self.results = {}  # type: Dict[int, object]

    def _schedule(
        self,
        tick: int,
        kind: str,
        node: Node,
        ttl: Optional[int] = None,
        request: Optional[Request] = None,
    ) -> int:
        if not _is_plain_int(tick) or tick < 0:
            raise ValueError("event tick must be a non-negative integer")
        index = self._next_index
        self._next_index += 1
        heapq.heappush(
            self._events,
            ScheduledEvent(tick, index, kind, node, ttl, request),
        )
        return index

    def schedule_grant(self, tick: int, node: Node, ttl: int) -> int:
        return self._schedule(tick, "grant", node, ttl=ttl)

    def schedule_submit(self, tick: int, node: Node, request: Request) -> int:
        return self._schedule(tick, "submit", node, request=request)

    def schedule_pause(self, tick: int, node: Node) -> int:
        return self._schedule(tick, "pause", node)

    def schedule_resume(self, tick: int, node: Node) -> int:
        return self._schedule(tick, "resume", node)

    def run(self) -> Dict[int, object]:
        while self._events:
            event = heapq.heappop(self._events)
            self.log.emit(
                tick=event.tick,
                event="event_dispatch",
                owner=event.node.owner,
                active_owner=self.coordinator.queue.active_owner,
                active_epoch=self.coordinator.queue.active_epoch,
                decision=event.kind.upper(),
                state_changed=False,
                history_changed=False,
                insertion_index=event.insertion_index,
                command_id=(
                    None if event.request is None else event.request.command_id
                ),
            )
            if event.kind == "grant":
                assert event.ttl is not None
                value = self.coordinator.grant(
                    event.node.owner,
                    event.tick,
                    event.ttl,
                    event.insertion_index,
                )
                if value is not None:
                    event.node.receive_lease(
                        value, event.tick, event.insertion_index
                    )
            elif event.kind == "submit":
                assert event.request is not None
                value = event.node.submit(
                    event.request, event.tick, event.insertion_index
                )
            elif event.kind in {"pause", "resume"}:
                # Pause/resume are explicit trace markers.  Network delivery is
                # represented by which submit events are scheduled and when.
                value = None
                self.log.emit(
                    tick=event.tick,
                    event=f"node_{event.kind}",
                    owner=event.node.owner,
                    epoch=(
                        None
                        if event.node.lease is None
                        else event.node.lease.epoch
                    ),
                    active_owner=self.coordinator.queue.active_owner,
                    active_epoch=self.coordinator.queue.active_epoch,
                    decision=event.kind.upper(),
                    state_changed=False,
                    history_changed=False,
                    insertion_index=event.insertion_index,
                )
            else:  # pragma: no cover - construction is private and exhaustive.
                raise AssertionError(f"unknown event kind: {event.kind}")
            self.results[event.insertion_index] = value
        return self.results
