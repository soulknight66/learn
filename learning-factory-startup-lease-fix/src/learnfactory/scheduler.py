from __future__ import annotations

import asyncio
import os
import signal
import socket
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from .config import FactorySettings
from .db import Database
from .jobs import JobRepository
from .retained_logs import BoundedBinaryCapture
from .util import new_id, now
from .workspace import WorkspaceManager


AUTO_COURSE_REFILL_INTERVAL_SECONDS = 5.0
SCHEDULER_MAINTENANCE_INTERVAL_SECONDS = 1.0
AUTO_COURSE_REFILL_MAX_COURSES = 32
AUTO_BYOX_REPAIR_REFILL_MAX_PROJECTS = 32


@dataclass
class _ManagedChild:
    process: asyncio.subprocess.Process
    stdout_capture: BoundedBinaryCapture
    stderr_capture: BoundedBinaryCapture
    stdout_path: Path
    stderr_path: Path
    drain_tasks: tuple[asyncio.Task[None], asyncio.Task[None]]


class Scheduler:
    def __init__(self, settings: FactorySettings, db: Database):
        self.settings = settings
        self.db = db
        self.jobs = JobRepository(
            db, retry_base=settings.retry_base_seconds, retry_max=settings.retry_max_seconds
        )
        self.owner = f"scheduler-{socket.gethostname()}-{os.getpid()}-{new_id('instance')[-8:]}"
        self.children: dict[str, _ManagedChild] = {}
        self.stop_requested = asyncio.Event()
        self._byox_repair_cursor: str | None = None
        self.blocked_validator_types = (
            frozenset()
            if settings.allow_host_command_validators
            else frozenset({"command"})
        )

    async def run(self, *, until_idle: bool = False, max_jobs: int | None = None) -> int:
        completed_at_start: int | None = None
        dispatched = 0
        started = False
        run_error: BaseException | None = None
        next_refill_at = 0.0
        next_maintenance_at = 0.0
        try:
            WorkspaceManager(
                self.settings.warehouse, self.db
            ).reconcile_published_artifacts()
            self.jobs.promote_eligible()
            self.jobs.recover_expired()
            next_maintenance_at = (
                time.monotonic() + SCHEDULER_MAINTENANCE_INTERVAL_SECONDS
            )
            completed_at_start = self._terminal_count()
            self.db.emit_event(
                "scheduler",
                "SCHEDULER_STARTED",
                payload={
                    "owner": self.owner,
                    "blocked_validator_types": sorted(
                        self.blocked_validator_types
                    ),
                },
            )
            started = True
            while not self.stop_requested.is_set():
                reaped = await self._reap_children()
                monotonic_now = time.monotonic()
                if reaped or monotonic_now >= next_maintenance_at:
                    self.jobs.recover_expired()
                    self.jobs.promote_eligible()
                    monotonic_now = time.monotonic()
                    next_maintenance_at = (
                        monotonic_now + SCHEDULER_MAINTENANCE_INTERVAL_SECONDS
                    )
                paused = self._is_paused()
                if (
                    not paused
                    and self._catalog_refill_due(
                        monotonic_now=monotonic_now,
                        next_refill_at=next_refill_at,
                    )
                ):
                    next_refill_at = self._refill_catalogs()
                    next_maintenance_at = (
                        time.monotonic()
                        + SCHEDULER_MAINTENANCE_INTERVAL_SECONDS
                    )
                    # A refill can take longer than the interval on NFS. Never
                    # dispatch from the pause value sampled before that work.
                    paused = self._is_paused()
                if not paused:
                    dispatched = await self._fill_capacity(
                        dispatched=dispatched,
                        max_jobs=max_jobs,
                    )
                if max_jobs is not None and dispatched >= max_jobs and not self.children:
                    break
                if until_idle and not self.children and not self._has_pending_work():
                    break
                await asyncio.sleep(self.settings.poll_seconds)
            return dispatched
        except BaseException as error:
            run_error = error
            raise
        finally:
            cleanup_error: BaseException | None = None
            try:
                await self._shutdown_children()
            except BaseException as error:
                cleanup_error = error
            if started:
                try:
                    finished = (
                        self._terminal_count() - completed_at_start
                        if completed_at_start is not None
                        else 0
                    )
                    self.db.emit_event(
                        "scheduler",
                        "SCHEDULER_STOPPED",
                        payload={
                            "owner": self.owner,
                            "dispatched": dispatched,
                            "new_terminal_jobs": finished,
                            "aborted": run_error is not None,
                        },
                    )
                except BaseException as error:
                    if cleanup_error is None:
                        cleanup_error = error
            if cleanup_error is not None:
                if run_error is not None:
                    run_error.add_note(
                        f"scheduler cleanup also failed: {cleanup_error!r}"
                    )
                else:
                    raise cleanup_error

    def _is_paused(self) -> bool:
        return bool(self.db.get_system_value("paused", False))

    def _catalog_refill_due(
        self, *, monotonic_now: float, next_refill_at: float
    ) -> bool:
        """Keep heavyweight graph writes outside an active worker wave.

        SQLite uses a rollback journal on the NFS workspace.  Catalog refill
        can legitimately take tens of seconds there, and running it while
        children heartbeat makes the single control-plane writer a lease
        hazard.  A wave already has all the work it can execute; defer refill
        until every child has been reaped, then replenish before the next
        claims are issued.
        """

        return not self.children and monotonic_now >= next_refill_at

    def _refill_catalogs(self) -> float:
        """Refill bounded graphs and return a deadline measured after completion."""

        self._auto_refill_byox_remediation()
        self._auto_refill_course_progression()
        self.jobs.promote_eligible()
        return time.monotonic() + AUTO_COURSE_REFILL_INTERVAL_SECONDS

    async def _fill_capacity(
        self, *, dispatched: int, max_jobs: int | None
    ) -> int:
        """Claim and launch work while rechecking the durable pause fence."""

        while len(self.children) < self.settings.max_concurrency:
            if max_jobs is not None and dispatched >= max_jobs:
                break
            # This closes the stale outer-loop window. claim_next repeats the
            # check under BEGIN IMMEDIATE to linearize against operator pause.
            if self._is_paused():
                break
            claimed = self.jobs.claim_next(
                self.owner,
                self.settings.lease_seconds,
                max_total=self.settings.max_concurrency,
                type_limits=self.settings.limits,
                blocked_validator_types=self.blocked_validator_types,
            )
            if claimed is None:
                break
            try:
                child = await self._launch(
                    claimed.job_id,
                    claimed.lease_token,
                    claimed.attempt_count,
                )
            except OSError as error:
                self.jobs.fail(
                    claimed.job_id,
                    self.owner,
                    claimed.lease_token,
                    None,
                    kind="launch_failure",
                    error=str(error),
                    retryable=True,
                )
                continue
            self.children[claimed.job_id] = child
            dispatched += 1
        return dispatched

    async def _launch(
        self, job_id: str, lease_token: str, attempt_count: int
    ) -> _ManagedChild:
        log_dir = (
            self.settings.warehouse
            / "logs"
            / job_id
            / f"attempt-{attempt_count:03d}"
        )
        log_dir.mkdir(parents=True, exist_ok=True)
        stdout_path = log_dir / "worker.stdout.log"
        stderr_path = log_dir / "worker.stderr.log"
        stdout_capture = BoundedBinaryCapture()
        stderr_capture = BoundedBinaryCapture()
        env = os.environ.copy()
        source_path = str(self.settings.root / "src")
        env["PYTHONPATH"] = source_path + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            "learnfactory.worker",
            "--job",
            job_id,
            "--owner",
            self.owner,
            "--lease-token",
            lease_token,
            "--config",
            str(self.settings.config_path or self.settings.root / "config/factory.toml"),
            cwd=self.settings.root,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
            start_new_session=True,
        )
        child: _ManagedChild | None = None
        try:
            assert process.stdout is not None
            assert process.stderr is not None
            drain_tasks = (
                asyncio.create_task(
                    _drain_stream(process.stdout, stdout_capture),
                    name=f"worker-stdout-{job_id}-attempt-{attempt_count}",
                ),
                asyncio.create_task(
                    _drain_stream(process.stderr, stderr_capture),
                    name=f"worker-stderr-{job_id}-attempt-{attempt_count}",
                ),
            )
            child = _ManagedChild(
                process,
                stdout_capture,
                stderr_capture,
                stdout_path,
                stderr_path,
                drain_tasks,
            )
            self.db.emit_event(
                "scheduler", "WORKER_PROCESS_STARTED", job_id=job_id,
                payload={
                    "pid": process.pid,
                    "owner": self.owner,
                    "attempt": attempt_count,
                    "stdout_path": str(stdout_path),
                    "stderr_path": str(stderr_path),
                },
            )
            return child
        except BaseException:
            if child is not None:
                await self._terminate_child(child)
            else:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                await process.wait()
            raise

    async def _reap_children(self) -> int:
        finished = [
            job_id
            for job_id, child in self.children.items()
            if child.process.returncode is not None
        ]
        for job_id in finished:
            child = self.children[job_id]
            await self._finalize_child_logs(child)
            self.db.emit_event(
                "scheduler", "WORKER_PROCESS_EXITED", job_id=job_id,
                payload={
                    "pid": child.process.pid,
                    "exit_code": child.process.returncode,
                    "stdout_bytes": child.stdout_capture.total_bytes,
                    "stderr_bytes": child.stderr_capture.total_bytes,
                },
            )
            del self.children[job_id]
        return len(finished)

    def _auto_refill_course_progression(self) -> dict[str, object] | None:
        """Deterministically admit bounded post-kickoff CSDIY work.

        The scheduler invokes this at startup, periodically, and after worker
        exits.  The course progression module owns eligibility and its durable
        sequence reservations; no model output can directly create or order a
        follow-on batch.
        """

        from .course_progression import seed_next_csdiy_course_batches
        from .seeding import CODEX_BACKEND_GATE_JOB_ID

        with self.db.connect() as connection:
            prerequisites = connection.execute(
                """
                SELECT
                  EXISTS(
                    SELECT 1 FROM jobs
                    WHERE job_id=? AND state='SUCCEEDED'
                  ) AS gate_ready,
                  EXISTS(
                    SELECT 1 FROM students WHERE student_id='student-target'
                  ) AS student_ready,
                  EXISTS(
                    SELECT 1
                    FROM courses c JOIN sources s ON s.source_id=c.source_id
                    WHERE s.is_active=1 AND (
                      s.type='course_catalog' OR lower(s.name) LIKE '%csdiy%'
                    )
                  ) AS catalog_ready
                """,
                (CODEX_BACKEND_GATE_JOB_ID,),
            ).fetchone()
        if prerequisites is None or not all(
            bool(prerequisites[name])
            for name in ("gate_ready", "student_ready", "catalog_ready")
        ):
            return None

        limit = max(
            1,
            min(
                AUTO_COURSE_REFILL_MAX_COURSES,
                self.settings.max_concurrency,
            ),
        )
        result = seed_next_csdiy_course_batches(
            self.db,
            self.jobs,
            max_courses=limit,
            max_revisions=self.settings.course_revision_limit,
        )
        if any(
            int(value)
            for value in result["invalidated_legacy_learner_evidence"].values()
        ):
            from .learners import sync_student_memory

            sync_student_memory(
                self.db, self.settings.warehouse, "student-target"
            )
        if int(result["scheduled_courses"]):
            self.db.emit_event(
                "scheduler",
                "COURSE_PROGRESSION_REFILLED",
                payload={
                    "policy_version": result["policy_version"],
                    "batch_size": result["batch_size"],
                    "examined_courses": result["examined_courses"],
                    "scheduled_courses": result["scheduled_courses"],
                    "seeded_batches": result["seeded_batches"],
                    "resumed_batches": result["resumed_batches"],
                    "seeded_revisions": result["seeded_revisions"],
                    "resumed_revisions": result["resumed_revisions"],
                    "max_revisions": result["max_revisions"],
                    "created_jobs": result["created_jobs"],
                    "status_counts": result["status_counts"],
                    "max_courses": limit,
                },
            )
        return result

    def _auto_refill_byox_remediation(self) -> dict[str, object] | None:
        """Advance a rotating bounded page of externally validated BYOX repairs."""

        from .byox_remediation import (
            DEFAULT_MAX_REPAIR_GENERATIONS,
            seed_byox_remediation_jobs,
        )
        from .seeding import CODEX_BACKEND_GATE_JOB_ID

        limit = max(
            1,
            min(
                AUTO_BYOX_REPAIR_REFILL_MAX_PROJECTS,
                max(1, self.settings.max_concurrency) * 4,
            ),
        )
        candidate_query = """
            WITH negative_projects AS (
                SELECT DISTINCT
                       CAST(json_extract(j.payload_json,'$.project_id') AS TEXT)
                       AS project_id
                FROM jobs j
                JOIN validations v
                  ON v.job_id=j.job_id
                 AND v.attempt_number=j.attempt_count
                 AND v.validator='byox-independent-review-verdict'
                 AND v.status='PASS'
                JOIN build_projects p
                  ON p.project_id=json_extract(j.payload_json,'$.project_id')
                JOIN sources s ON s.source_id=p.source_id AND s.is_active=1
                WHERE j.state='SUCCEEDED'
                  AND json_valid(j.payload_json)
                  AND (
                    json_extract(j.payload_json,'$.seed_policy.kind')
                      ='byox_reference_review'
                    OR (
                      json_extract(j.payload_json,'$.seed_policy.kind') IN (
                        'byox_reference_review_s2',
                        'byox_reference_repair_review_s2'
                      )
                      AND EXISTS (
                        SELECT 1 FROM byox_baseline_job_bindings binding
                        WHERE binding.job_id=j.job_id
                          AND binding.role='reviewer'
                      )
                    )
                  )
                  AND json_valid(v.evidence_json)
                  AND json_extract(v.evidence_json,'$.verdict') IN ('REVISE','FAIL')
            )
            SELECT project_id
            FROM negative_projects
            WHERE (? IS NULL OR project_id > ?)
            ORDER BY project_id
            LIMIT ?
        """
        with self.db.connect() as connection:
            gate_ready = connection.execute(
                """
                SELECT EXISTS(
                    SELECT 1
                    FROM jobs g JOIN artifacts a
                      ON a.job_id=g.job_id AND a.attempt_number=g.attempt_count
                    WHERE g.job_id=? AND g.state='SUCCEEDED'
                      AND a.type='backend-capability-gate'
                      AND a.checksum_algorithm='tree-sha256-v2'
                      AND a.integrity_status='VERIFIED_V2'
                ) AS ready
                """,
                (CODEX_BACKEND_GATE_JOB_ID,),
            ).fetchone()
            if gate_ready is None or not bool(gate_ready["ready"]):
                return None
            rows = list(
                connection.execute(
                    candidate_query,
                    (self._byox_repair_cursor, self._byox_repair_cursor, limit),
                )
            )
            if len(rows) < limit and self._byox_repair_cursor is not None:
                wrapped = connection.execute(
                    candidate_query,
                    (None, None, limit - len(rows)),
                )
                seen = {str(row["project_id"]) for row in rows}
                rows.extend(
                    row for row in wrapped if str(row["project_id"]) not in seen
                )
        project_ids = [str(row["project_id"]) for row in rows]
        if not project_ids:
            return None
        self._byox_repair_cursor = project_ids[-1]
        result = seed_byox_remediation_jobs(
            self.db,
            self.jobs,
            warehouse=self.settings.warehouse,
            max_repair_generations=DEFAULT_MAX_REPAIR_GENERATIONS,
            project_ids=project_ids,
            max_projects=limit,
        )
        if int(result["created_jobs"]):
            status_counts: dict[str, int] = {}
            for project in result["projects"].values():
                status = str(project["status"])
                status_counts[status] = status_counts.get(status, 0) + 1
            self.db.emit_event(
                "scheduler",
                "BYOX_REMEDIATION_REFILLED",
                payload={
                    "policy_version": result["policy_version"],
                    "max_repair_generations": result["max_repair_generations"],
                    "max_projects": limit,
                    "candidate_projects": len(project_ids),
                    "created_repair_builders": result["created_repair_builders"],
                    "created_reviewers": result["created_reviewers"],
                    "created_jobs": result["created_jobs"],
                    "status_counts": status_counts,
                },
            )
        return result

    async def _terminate_child(self, child: _ManagedChild) -> None:
        """Stop and reap one spawned child before relinquishing supervision."""

        process = child.process
        if process.returncode is None:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                await asyncio.wait_for(process.wait(), timeout=1)
            except asyncio.TimeoutError:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                await process.wait()
        await self._finalize_child_logs(child)

    async def _finalize_child_logs(self, child: _ManagedChild) -> None:
        process = child.process
        if process.returncode is None:
            await process.wait()
        # The direct worker may have exited while an accidental descendant still
        # owns its supervisor pipes. Reconcile that process group before waiting
        # for EOF so log retention cannot hang the scheduler.
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        drains = asyncio.gather(*child.drain_tasks)
        try:
            await asyncio.wait_for(asyncio.shield(drains), timeout=0.25)
        except asyncio.TimeoutError:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            try:
                await asyncio.wait_for(asyncio.shield(drains), timeout=1)
            except asyncio.TimeoutError:
                for task in child.drain_tasks:
                    task.cancel()
                await asyncio.gather(*child.drain_tasks, return_exceptions=True)
        child.stdout_capture.persist_redacted(child.stdout_path)
        child.stderr_capture.persist_redacted(child.stderr_path)

    async def _shutdown_children(self) -> None:
        if not self.children:
            return
        event_error: BaseException | None = None
        try:
            self.db.emit_event(
                "scheduler",
                "SCHEDULER_DRAINING",
                payload={"active_children": len(self.children)},
            )
        except BaseException as error:
            event_error = error
        try:
            await asyncio.wait_for(
                asyncio.gather(
                    *(child.process.wait() for child in self.children.values())
                ),
                timeout=self.settings.shutdown_grace_seconds,
            )
        except asyncio.TimeoutError:
            # A controller stop is not a job cancellation. Workers translate this
            # supervisor signal into a retryable interruption unless the job's
            # durable cancel_requested flag was set separately.
            for child in self.children.values():
                if child.process.returncode is None:
                    try:
                        os.killpg(child.process.pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
            try:
                await asyncio.wait_for(
                    asyncio.gather(
                        *(child.process.wait() for child in self.children.values())
                    ),
                    timeout=5,
                )
            except asyncio.TimeoutError:
                for child in self.children.values():
                    if child.process.returncode is None:
                        try:
                            os.killpg(child.process.pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                await asyncio.gather(
                    *(child.process.wait() for child in self.children.values())
                )
        finalizations = await asyncio.gather(
            *(self._finalize_child_logs(child) for child in self.children.values()),
            return_exceptions=True,
        )
        self.children.clear()
        finalization_error = next(
            (result for result in finalizations if isinstance(result, BaseException)),
            None,
        )
        if event_error is not None:
            raise event_error
        if finalization_error is not None:
            raise finalization_error

    def request_stop(self) -> None:
        self.stop_requested.set()

    def _has_pending_work(self) -> bool:
        with self.db.connect() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS n FROM jobs
                WHERE state IN ('CLAIMED','RUNNING','RETRY_WAIT')
                """
            ).fetchone()
        return bool(row["n"]) or bool(
            self.jobs.count_ready_claimable(
                self.blocked_validator_types,
                type_limits=self.settings.limits,
            )
        )

    def _terminal_count(self) -> int:
        with self.db.connect() as connection:
            return int(
                connection.execute(
                    "SELECT COUNT(*) AS n FROM jobs WHERE state IN ('SUCCEEDED','FAILED','CANCELLED')"
                ).fetchone()["n"]
            )


async def run_scheduler(settings: FactorySettings, db: Database, **kwargs: object) -> int:
    scheduler = Scheduler(settings, db)
    loop = asyncio.get_running_loop()
    for signum in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(signum, scheduler.request_stop)
        except NotImplementedError:
            pass
    return await scheduler.run(**kwargs)


async def _drain_stream(
    stream: asyncio.StreamReader, capture: BoundedBinaryCapture
) -> None:
    while chunk := await stream.read(64 * 1024):
        capture.feed(chunk)
