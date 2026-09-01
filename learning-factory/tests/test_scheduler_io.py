from __future__ import annotations

import asyncio
import io
import json
import sqlite3
import tempfile
import threading
import time
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock

from learnfactory import course_kickoff_revisions, course_progression
from learnfactory.config import FactorySettings, load_settings
from learnfactory.db import Database
from learnfactory.jobs import JobError, JobRepository, JobState
from learnfactory.scheduler import AUTO_COURSE_REFILL_INTERVAL_SECONDS, Scheduler
from learnfactory.worker import (
    _HeartbeatPublicationGate,
    _LeaseDeadline,
    _WorkerBoundaryStop,
    _fence_worker_boundary,
    _heartbeat_loop,
    _quiesced_heartbeat_publication,
    _startup_heartbeat_delay,
)
from learnfactory.workspace import WorkspaceManager


ROOT = Path(__file__).resolve().parents[1]


class SchedulerIoAndPauseTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="learnfactory-scheduler-io-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.settings = FactorySettings(
            root=ROOT,
            database=self.root / "factory.db",
            warehouse=self.root / "warehouse",
            max_concurrency=3,
            limits={"test": 3},
        )
        self.database = Database(self.settings.database, ROOT / "migrations")
        self.database.migrate()
        WorkspaceManager(self.settings.warehouse, self.database).initialize()
        self.jobs = JobRepository(self.database)

    def _ready(self, job_id: str, priority: float) -> None:
        self.jobs.create(
            "fake", "test", {}, job_id=job_id, priority=priority
        )
        self.jobs.promote_eligible()

    def test_inner_fill_rechecks_pause_between_each_launch(self) -> None:
        self._ready("job_pause_fill_first", 2)
        self._ready("job_pause_fill_second", 1)
        scheduler = Scheduler(self.settings, self.database)

        async def launch_and_pause(*_args: object) -> object:
            self.database.set_system_value("paused", True)
            return object()

        with mock.patch.object(
            scheduler, "_launch", side_effect=launch_and_pause
        ) as launch:
            dispatched = asyncio.run(
                scheduler._fill_capacity(dispatched=0, max_jobs=None)
            )

        self.assertEqual(1, dispatched)
        self.assertEqual(1, launch.await_count)
        self.assertEqual(1, len(scheduler.children))
        second = self.jobs.get("job_pause_fill_second")
        self.assertEqual("READY", second["state"])
        self.assertEqual(0, second["attempt_count"])
        scheduler.children.clear()

    def test_idle_maintenance_and_claim_probes_do_not_open_write_transactions(
        self,
    ) -> None:
        with mock.patch.object(
            self.database,
            "transaction",
            side_effect=AssertionError("idle path acquired a write transaction"),
        ):
            self.assertEqual(0, self.jobs.promote_eligible())
            self.assertEqual(0, self.jobs.recover_expired())
            self.assertIsNone(
                self.jobs.claim_next(
                    "idle-owner", 30, max_total=1, type_limits={}
                )
            )

    def test_pause_during_slow_refill_prevents_any_following_claim(self) -> None:
        self._ready("job_pause_during_refill", 1)
        scheduler = Scheduler(self.settings, self.database)

        def refill_then_pause() -> None:
            self.database.set_system_value("paused", True)
            scheduler.stop_requested.set()

        with mock.patch.object(
            scheduler, "_auto_refill_byox_remediation", return_value=None
        ), mock.patch.object(
            scheduler,
            "_auto_refill_course_progression",
            side_effect=refill_then_pause,
        ), mock.patch.object(scheduler, "_launch") as launch:
            dispatched = asyncio.run(scheduler.run(max_jobs=1))

        self.assertEqual(0, dispatched)
        self.assertEqual(0, launch.await_count)
        job = self.jobs.get("job_pause_during_refill")
        self.assertEqual("READY", job["state"])
        self.assertEqual(0, job["attempt_count"])

    def test_refill_deadline_is_sampled_only_after_refill_finishes(self) -> None:
        scheduler = Scheduler(self.settings, self.database)
        completed: list[str] = []

        def clock() -> float:
            self.assertEqual(["byox", "course", "promote"], completed)
            return 125.0

        with mock.patch.object(
            scheduler,
            "_auto_refill_byox_remediation",
            side_effect=lambda: completed.append("byox"),
        ), mock.patch.object(
            scheduler,
            "_auto_refill_course_progression",
            side_effect=lambda: completed.append("course"),
        ), mock.patch.object(
            scheduler.jobs,
            "promote_eligible",
            side_effect=lambda: completed.append("promote"),
        ), mock.patch(
            "learnfactory.scheduler.time.monotonic", side_effect=clock
        ):
            deadline = scheduler._refill_catalogs()

        self.assertEqual(
            125.0 + AUTO_COURSE_REFILL_INTERVAL_SECONDS, deadline
        )

    def test_course_group_helpers_scan_only_legacy_and_v2_namespaces(self) -> None:
        markers = {
            "job_csdiy_progress_v1_fixture": "progress-v1",
            "job_csdiy_progress_v2_fixture": "progress-v2",
            "job_csdiy_revision_v1_fixture": "unit-revision-v1",
            "job_csdiy_revision_v2_fixture": "unit-revision-v2",
            "job_csdiy_kickoff_rev_v1_fixture": "kickoff-v1",
            "job_csdiy_kickoff_rev_v2_fixture": "kickoff-v2",
            "job_unrelated_payload_sentinel": "must-not-be-read",
        }
        with self.database.transaction(immediate=True) as connection:
            connection.executemany(
                """
                INSERT INTO jobs(
                    job_id,type,worker_type,state,payload_json,created_at
                ) VALUES (?,?,?,'READY',?,?)
                """,
                [
                    (job_id, "fixture", "test", json.dumps({"marker": marker}), index)
                    for index, (job_id, marker) in enumerate(markers.items())
                ],
            )

        progression_seen: list[str] = []
        real_progression_decode = course_progression._decoded

        def track_progression(
            raw: object, expected: type, default: object
        ) -> object:
            value = real_progression_decode(raw, expected, default)
            if isinstance(value, dict) and "marker" in value:
                progression_seen.append(str(value["marker"]))
            return value

        with mock.patch.object(
            course_progression, "_decoded", side_effect=track_progression
        ):
            self.assertEqual({}, course_progression._progression_groups(self.database))

        kickoff_seen: list[str] = []
        real_kickoff_decode = course_kickoff_revisions._decoded

        def track_kickoff(raw: object, expected: type, default: object) -> object:
            value = real_kickoff_decode(raw, expected, default)
            if isinstance(value, dict) and "marker" in value:
                kickoff_seen.append(str(value["marker"]))
            return value

        with mock.patch.object(
            course_kickoff_revisions, "_decoded", side_effect=track_kickoff
        ):
            self.assertEqual(
                {},
                course_kickoff_revisions._revision_groups_by_course(
                    self.database,
                    {"course-fixture": ("source-fixture", "f" * 40)},
                ),
            )

        self.assertEqual(
            {
                "progress-v1",
                "progress-v2",
                "unit-revision-v1",
                "unit-revision-v2",
            },
            set(progression_seen),
        )
        self.assertEqual({"kickoff-v1", "kickoff-v2"}, set(kickoff_seen))
        self.assertNotIn("must-not-be-read", progression_seen + kickoff_seen)

    def test_kickoff_revisions_are_decoded_once_for_twelve_courses(self) -> None:
        course_sources = {
            f"course-{course:02d}": (f"source-{course:02d}", f"commit-{course:02d}")
            for course in range(12)
        }
        records: list[tuple[str, str, str, str, float]] = []
        index = 0
        for course_id, (source_id, commit_hash) in course_sources.items():
            for attempt in range(2, 7):
                snapshot = {
                    "attempt_number": attempt,
                    "source": {
                        "source_id": source_id,
                        "commit_hash": commit_hash,
                    },
                }
                for role in ("student_revision", "examiner_revision"):
                    payload = {
                        "course_id": course_id,
                        "seed_policy": {
                            "kind": course_kickoff_revisions.KICKOFF_REVISION_POLICY_KIND,
                            "version": course_kickoff_revisions.KICKOFF_REVISION_POLICY_VERSION,
                            "attempt_number": attempt,
                            "role": role,
                        },
                        "revision_snapshot": snapshot,
                    }
                    records.append(
                        (
                            "job_csdiy_kickoff_rev_"
                            f"v{course_kickoff_revisions.KICKOFF_REVISION_POLICY_VERSION}_"
                            f"{index:024x}_{role}",
                            "fixture",
                            "test",
                            json.dumps(payload, separators=(",", ":")),
                            float(index),
                        )
                    )
                    index += 1
        with self.database.transaction(immediate=True) as connection:
            connection.executemany(
                """
                INSERT INTO jobs(
                    job_id,type,worker_type,state,payload_json,created_at
                ) VALUES (?,?,?,'READY',?,?)
                """,
                records,
            )

        decode_count = 0
        real_decode = course_kickoff_revisions._decoded

        def count_decode(raw: object, expected: type, default: object) -> object:
            nonlocal decode_count
            decode_count += 1
            return real_decode(raw, expected, default)

        with mock.patch.object(
            course_kickoff_revisions,
            "_decoded",
            side_effect=count_decode,
        ):
            groups = course_kickoff_revisions._revision_groups_by_course(
                self.database,
                course_sources,
            )

        self.assertEqual(120, decode_count)
        self.assertEqual(set(course_sources), set(groups))
        self.assertTrue(all(len(attempts) == 5 for attempts in groups.values()))


class ConfigurationLeaseMarginTests(unittest.TestCase):
    def _write_config(
        self, root: Path, *, busy_timeout: float | None = None
    ) -> Path:
        lines = [
            "[factory]",
            f'database = "{root / "factory.db"}"',
            f'warehouse = "{root / "warehouse"}"',
            "lease_seconds = 1",
            "heartbeat_seconds = 0.2",
            "poll_seconds = 0.05",
        ]
        if busy_timeout is not None:
            lines.append(f"database_busy_timeout_seconds = {busy_timeout}")
        path = root / "factory.toml"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path

    def test_default_busy_timeout_preserves_lease_headroom(self) -> None:
        with tempfile.TemporaryDirectory(prefix="learnfactory-config-margin-") as raw:
            settings = load_settings(self._write_config(Path(raw)))

        self.assertAlmostEqual(0.64, settings.database_busy_timeout_seconds)
        self.assertLess(
            settings.heartbeat_seconds + settings.database_busy_timeout_seconds,
            settings.lease_seconds,
        )

    def test_explicit_busy_timeout_cannot_consume_the_lease_margin(self) -> None:
        with tempfile.TemporaryDirectory(prefix="learnfactory-config-margin-") as raw:
            with self.assertRaisesRegex(ValueError, "leave lease headroom"):
                load_settings(
                    self._write_config(Path(raw), busy_timeout=0.8)
                )


class _DeterministicClock:
    def __init__(self) -> None:
        self.monotonic_value = 0.0
        self.wall_value = 100.0

    def monotonic(self) -> float:
        return self.monotonic_value

    def wall(self) -> float:
        return self.wall_value

    def advance(self, seconds: float) -> None:
        self.monotonic_value += seconds
        self.wall_value += seconds


class _ControlledEvent:
    def __init__(self, clock: _DeterministicClock, stop_after_waits: int):
        self.clock = clock
        self.stop_after_waits = stop_after_waits
        self.waits: list[float] = []
        self.was_set = False

    def wait(self, timeout: float) -> bool:
        if self.was_set:
            return True
        self.waits.append(timeout)
        if len(self.waits) >= self.stop_after_waits:
            return True
        self.clock.advance(timeout)
        return False

    def set(self) -> None:
        self.was_set = True

    def is_set(self) -> bool:
        return self.was_set


class HeartbeatDiagnosticsTests(unittest.TestCase):
    def test_startup_heartbeat_phase_is_deterministic_early_and_distributed(
        self,
    ) -> None:
        values = {
            _startup_heartbeat_delay(f"job-{index}", f"lease-{index}", 5.0)
            for index in range(24)
        }

        self.assertEqual(
            _startup_heartbeat_delay("job-1", "lease-1", 5.0),
            _startup_heartbeat_delay("job-1", "lease-1", 5.0),
        )
        self.assertGreaterEqual(min(values), 0.5)
        self.assertLessEqual(max(values), 2.5)
        self.assertGreater(len(values), 20)

    def test_out_of_order_renewal_cannot_shorten_shared_deadline(self) -> None:
        deadline = _LeaseDeadline(
            110.0,
            monotonic_clock=lambda: 10.0,
            wall_clock=lambda: 100.0,
        )

        self.assertTrue(deadline.renew(130.0, observed_at=11.0))
        advanced = deadline.current()
        self.assertTrue(deadline.renew(115.0, observed_at=12.0))

        self.assertEqual(41.0, advanced)
        self.assertEqual(advanced, deadline.current())

    def test_recovered_cancellation_still_fences_without_owned_lease(self) -> None:
        class Jobs:
            def cancellation_requested(self, _job_id: str) -> bool:
                return True

            def finish_cancelled(self, *_args: object) -> None:
                raise JobError("claim already recovered")

        gate = _HeartbeatPublicationGate(threading.Event())
        with self.assertRaises(_WorkerBoundaryStop) as raised:
            _fence_worker_boundary(  # type: ignore[arg-type]
                Jobs(),
                job_id="job-recovered-cancel",
                owner="old-owner",
                lease_token="old-lease",
                worker_id=None,
                stop_gate=gate,
                supervisor_stop_event=threading.Event(),
                boundary="after recovery",
            )

        self.assertEqual(130, raised.exception.exit_code)

    def test_supervisor_wins_race_at_local_failure_classification(self) -> None:
        supervisor_stop = threading.Event()

        class RacingCancellationEvent(threading.Event):
            def is_set(self) -> bool:
                # Deterministically model SIGTERM arriving after the first
                # supervisor read but while local cancellation is observed.
                supervisor_stop.set()
                return True

        cancel_event = RacingCancellationEvent()
        gate = _HeartbeatPublicationGate(cancel_event)

        class Jobs:
            interrupted = False

            def cancellation_requested(self, _job_id: str) -> bool:
                return False

            def interrupt(self, *_args: object, **_kwargs: object) -> JobState:
                self.interrupted = True
                return JobState.RETRY_WAIT

            def fail(self, *_args: object, **_kwargs: object) -> JobState:
                raise AssertionError("SIGTERM was misclassified as local failure")

        jobs = Jobs()
        with self.assertRaises(_WorkerBoundaryStop) as raised:
            _fence_worker_boundary(  # type: ignore[arg-type]
                jobs,
                job_id="job-signal-race",
                owner="owner",
                lease_token="lease",
                worker_id="worker",
                stop_gate=gate,
                supervisor_stop_event=supervisor_stop,
                boundary="during deterministic race",
            )

        self.assertEqual(143, raised.exception.exit_code)
        self.assertTrue(jobs.interrupted)

    def test_heartbeat_completed_after_expiry_cancels_before_publication_stop(
        self,
    ) -> None:
        clock = _DeterministicClock()
        cancel_event = _ControlledEvent(clock, stop_after_waits=100)

        class Gate:
            stopped = False

            def wait(self, timeout: float) -> bool:
                clock.advance(timeout)
                return cancel_event.is_set()

            def stop_requested(self) -> bool:
                return self.stopped

            def request_local_cancel(self) -> None:
                cancel_event.set()

        gate = Gate()

        class Jobs:
            def heartbeat(self, *_args: object) -> float:
                gate.stopped = True
                clock.advance(0.1)
                return clock.wall() + 1

        output = io.StringIO()
        with redirect_stderr(output):
            _heartbeat_loop(  # type: ignore[arg-type]
                Jobs(),
                "job-late-renewal-during-quiesce",
                "owner",
                "lease",
                "worker",
                1,
                0.01,
                clock.wall() + 0.1,
                0.1,
                cancel_event,  # type: ignore[arg-type]
                monotonic_clock=clock.monotonic,
                wall_clock=clock.wall,
                _start_watchdog=False,
                _publication_gate=gate,  # type: ignore[arg-type]
            )

        self.assertTrue(cancel_event.was_set)
        events = [json.loads(line)["event"] for line in output.getvalue().splitlines()]
        self.assertEqual(["HEARTBEAT_LEASE_AT_RISK"], events)

    def test_lease_loss_returned_after_publication_stop_still_cancels(self) -> None:
        entered_heartbeat = threading.Event()
        release_heartbeat = threading.Event()
        cancel_event = threading.Event()
        gate = _HeartbeatPublicationGate(cancel_event)

        class Jobs:
            def heartbeat(self, *_args: object) -> None:
                entered_heartbeat.set()
                self_test.assertTrue(release_heartbeat.wait(timeout=2))
                return None

        self_test = self
        output = io.StringIO()

        def heartbeat() -> None:
            with redirect_stderr(output):
                _heartbeat_loop(  # type: ignore[arg-type]
                    Jobs(),
                    "job-lost-during-quiesce",
                    "owner",
                    "lease",
                    "worker",
                    1,
                    0.01,
                    time.time() + 1,
                    0.1,
                    cancel_event,
                    _start_watchdog=False,
                    _publication_gate=gate,
                )

        thread = threading.Thread(target=heartbeat)
        thread.start()
        self.assertTrue(entered_heartbeat.wait(timeout=2))
        gate.request_stop()
        release_heartbeat.set()
        thread.join(timeout=2)

        self.assertFalse(thread.is_alive())
        self.assertTrue(cancel_event.is_set())
        with _quiesced_heartbeat_publication(gate, thread):
            self.assertTrue(cancel_event.is_set())
        events = [json.loads(line)["event"] for line in output.getvalue().splitlines()]
        self.assertIn("HEARTBEAT_LEASE_LOST_OR_CANCELLED", events)

    def test_transient_contention_is_reported_and_recovery_is_confirmed(self) -> None:
        clock = _DeterministicClock()

        class Jobs:
            calls = 0

            def heartbeat(self, *_args: object) -> float:
                self.calls += 1
                if self.calls == 1:
                    clock.advance(0.25)
                    raise sqlite3.OperationalError("database is locked")
                clock.advance(0.1)
                return clock.wall() + 10

        event = _ControlledEvent(clock, stop_after_waits=3)
        output = io.StringIO()
        with redirect_stderr(output):
            _heartbeat_loop(  # type: ignore[arg-type]
                Jobs(),
                "job",
                "owner",
                "lease",
                "worker",
                10,
                2,
                clock.wall() + 10,
                1,
                event,
                monotonic_clock=clock.monotonic,
                wall_clock=clock.wall,
                _start_watchdog=False,
            )

        diagnostics = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual(
            ["HEARTBEAT_DATABASE_CONTENTION", "HEARTBEAT_RECOVERED"],
            [record["event"] for record in diagnostics],
        )
        self.assertFalse(event.was_set)
        self.assertEqual([2, 0.05, 2], event.waits)

    def test_persistent_contention_stops_work_before_local_lease_horizon(self) -> None:
        clock = _DeterministicClock()

        class Jobs:
            def heartbeat(self, *_args: object) -> float:
                per_lock_timeout = float(_args[-1])
                clock.advance(2 * per_lock_timeout)
                raise sqlite3.OperationalError("database is locked")

        event = _ControlledEvent(clock, stop_after_waits=10)
        output = io.StringIO()
        with redirect_stderr(output):
            _heartbeat_loop(  # type: ignore[arg-type]
                Jobs(),
                "job",
                "owner",
                "lease",
                "worker",
                10,
                2,
                clock.wall() + 10,
                3,
                event,
                monotonic_clock=clock.monotonic,
                wall_clock=clock.wall,
                _start_watchdog=False,
            )

        diagnostics = [json.loads(line) for line in output.getvalue().splitlines()]
        events = [record["event"] for record in diagnostics]
        self.assertGreaterEqual(events.count("HEARTBEAT_DATABASE_CONTENTION"), 2)
        self.assertEqual("HEARTBEAT_LEASE_AT_RISK", events[-1])
        self.assertTrue(event.was_set)
        self.assertEqual([2, 0.05], event.waits[:2])
        self.assertLess(clock.monotonic(), 10)

    def test_tiny_remaining_budget_cancels_before_entering_database(self) -> None:
        clock = _DeterministicClock()

        class Jobs:
            def heartbeat(self, *_args: object) -> float:
                raise AssertionError("tiny budget entered SQLite")

        event = _ControlledEvent(clock, stop_after_waits=10)
        output = io.StringIO()
        with redirect_stderr(output):
            _heartbeat_loop(  # type: ignore[arg-type]
                Jobs(),
                "job",
                "owner",
                "lease",
                "worker",
                1,
                0.02,
                clock.wall() + 0.021,
                0.3,
                event,
                monotonic_clock=clock.monotonic,
                wall_clock=clock.wall,
                _start_watchdog=False,
            )

        diagnostics = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual(["HEARTBEAT_LEASE_AT_RISK"], [row["event"] for row in diagnostics])
        self.assertTrue(event.was_set)
        self.assertLess(clock.monotonic(), 0.021)


class HeartbeatRealLockTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="learnfactory-heartbeat-locks-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.database = Database(
            self.root / "factory.db",
            ROOT / "migrations",
            busy_timeout_seconds=0.3,
        )
        self.database.migrate()
        self.jobs = JobRepository(self.database)

    def _running_job(self) -> tuple[str, str, str, str, float]:
        job_id = self.jobs.create("fake", "test", {}, job_id="job_real_lock_heartbeat")
        self.jobs.promote_eligible()
        owner = "real-lock-owner"
        claim = self.jobs.claim_next(
            owner,
            0.5,
            max_total=1,
            type_limits={"test": 1},
        )
        assert claim is not None
        worker_id = "worker_real_lock_heartbeat"
        workspace = self.root / "workspace"
        workspace.mkdir()
        timestamp = time.time()
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                """
                INSERT INTO workers(
                    worker_id,type,state,started_at,last_activity,current_job,workspace
                ) VALUES (?,?,?,?,?,?,?)
                """,
                (
                    worker_id,
                    "test",
                    "STARTING",
                    timestamp,
                    timestamp,
                    job_id,
                    str(workspace),
                ),
            )
        expiry = self.jobs.start(
            job_id,
            owner,
            claim.lease_token,
            worker_id,
            str(workspace),
            lease_seconds=0.5,
        )
        return job_id, owner, claim.lease_token, worker_id, expiry

    def _two_locks(self) -> tuple[sqlite3.Connection, sqlite3.Connection]:
        writer = self.database.connect()
        reader = self.database.connect()
        try:
            writer.execute("BEGIN IMMEDIATE")
            reader.execute("BEGIN")
            reader.execute("SELECT COUNT(*) FROM jobs").fetchone()
            return writer, reader
        except BaseException:
            writer.close()
            reader.close()
            raise

    def test_real_begin_and_commit_locks_cancel_before_durable_expiry(self) -> None:
        job_id, owner, lease_token, worker_id, expiry = self._running_job()
        writer, reader = self._two_locks()
        cancel_event = threading.Event()
        failures: list[BaseException] = []

        def heartbeat() -> None:
            try:
                _heartbeat_loop(
                    self.jobs,
                    job_id,
                    owner,
                    lease_token,
                    worker_id,
                    0.5,
                    0.02,
                    expiry,
                    0.3,
                    cancel_event,
                )
            except BaseException as error:
                failures.append(error)

        started = time.monotonic()
        deadline = started + max(0.0, expiry - time.time())
        output = io.StringIO()
        with redirect_stderr(output):
            thread = threading.Thread(target=heartbeat)
            thread.start()
            time.sleep(0.15)
            writer.rollback()
            writer.close()
            self.assertTrue(cancel_event.wait(timeout=1))
            cancelled_at = time.monotonic()
            reader.rollback()
            reader.close()
            thread.join(timeout=2)

        self.assertFalse(thread.is_alive())
        self.assertEqual([], failures)
        self.assertLess(cancelled_at, deadline)
        events = [json.loads(line)["event"] for line in output.getvalue().splitlines()]
        self.assertIn("HEARTBEAT_DATABASE_CONTENTION", events)
        self.assertIn("HEARTBEAT_LEASE_AT_RISK", events)

    def test_watchdog_cancels_even_when_two_lock_heartbeat_commits_late(self) -> None:
        job_id, owner, lease_token, worker_id, expiry = self._running_job()
        writer, reader = self._two_locks()
        cancel_event = threading.Event()
        gate = _HeartbeatPublicationGate(cancel_event)
        failures: list[BaseException] = []
        publication_observation: list[bool] = []

        class FullTimeoutRepository:
            def heartbeat(self, *args: object) -> float | None:
                return self_repository.heartbeat(
                    *args[:5],  # type: ignore[arg-type]
                    busy_timeout_seconds=0.3,
                )

        self_repository = self.jobs

        def heartbeat() -> None:
            try:
                _heartbeat_loop(  # type: ignore[arg-type]
                    FullTimeoutRepository(),
                    job_id,
                    owner,
                    lease_token,
                    worker_id,
                    0.5,
                    0.02,
                    expiry,
                    0.3,
                    cancel_event,
                    _publication_gate=gate,
                )
            except BaseException as error:
                failures.append(error)

        started = time.monotonic()
        deadline = started + max(0.0, expiry - time.time())
        output = io.StringIO()
        with redirect_stderr(output):
            thread = threading.Thread(target=heartbeat)
            thread.start()
            time.sleep(0.23)
            writer.rollback()
            writer.close()
            self.assertTrue(cancel_event.wait(timeout=1))
            cancelled_at = time.monotonic()
            self.assertLess(cancelled_at, deadline)
            gate.request_stop()

            def attempt_publication() -> None:
                with _quiesced_heartbeat_publication(gate, thread):
                    publication_observation.append(cancel_event.is_set())

            publication = threading.Thread(target=attempt_publication)
            publication.start()
            time.sleep(max(0.0, deadline + 0.015 - time.monotonic()))
            reader.rollback()
            reader.close()
            thread.join(timeout=2)
            publication.join(timeout=2)

        self.assertFalse(thread.is_alive())
        self.assertFalse(publication.is_alive())
        self.assertEqual([], failures)
        self.assertEqual([True], publication_observation)
        self.assertGreater(self.jobs.get(job_id)["lease_expires_at"], expiry)


if __name__ == "__main__":
    unittest.main()
