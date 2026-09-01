from __future__ import annotations

import hashlib
import multiprocessing
import shutil
import sqlite3
import tempfile
import threading
import time
import traceback
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest import mock

from learnfactory.db import Database, MigrationError
from learnfactory.jobs import (
    JobError,
    JobRepository,
    JobState,
    _credential_values_from_environment,
)
from learnfactory.validation import Validator


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
INITIAL_MIGRATION = REPOSITORY_ROOT / "migrations" / "001_initial.sql"
MIGRATION_FILES = sorted((REPOSITORY_ROOT / "migrations").glob("[0-9][0-9][0-9]_*.sql"))


def _copy_migrations(destination: Path) -> Path:
    destination.mkdir(parents=True)
    for migration in MIGRATION_FILES:
        shutil.copy2(migration, destination / migration.name)
    return destination


def _claim_in_process(
    database_path: str,
    migrations_path: str,
    owner: str,
    start_event: object,
    ready_queue: object,
    result_queue: object,
) -> None:
    """Process target kept at module scope so the spawn start method can import it."""
    try:
        repository = JobRepository(Database(Path(database_path), Path(migrations_path)))
        ready_queue.put(owner)  # type: ignore[attr-defined]
        if not start_event.wait(20):  # type: ignore[attr-defined]
            result_queue.put(("error", owner, "start event timed out"))  # type: ignore[attr-defined]
            return
        claimed = repository.claim_next(
            owner,
            lease_seconds=30,
            max_total=8,
            type_limits={},
        )
        result_queue.put(  # type: ignore[attr-defined]
            ("ok", owner, claimed.job_id if claimed is not None else None)
        )
    except BaseException:
        result_queue.put(("error", owner, traceback.format_exc()))  # type: ignore[attr-defined]


def _migrate_in_process(database_path: str, migrations_path: str, result_queue: object) -> None:
    try:
        applied = Database(Path(database_path), Path(migrations_path)).migrate()
        result_queue.put(("ok", applied))  # type: ignore[attr-defined]
    except BaseException:
        result_queue.put(("error", traceback.format_exc()))  # type: ignore[attr-defined]


def _remove_sqlite_test_files(database_path: Path) -> None:
    for suffix in ("", "-journal", "-wal", "-shm"):
        Path(f"{database_path}{suffix}").unlink(missing_ok=True)


class DatabaseTestCase(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="learnfactory-jobs-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.migrations = _copy_migrations(self.root / "migrations")
        self.database_path = self.root / "factory.db"
        self.database = Database(self.database_path, self.migrations)
        self.assertEqual([migration.name for migration in MIGRATION_FILES], self.database.migrate())
        self.jobs = JobRepository(self.database, retry_base=0.01, retry_max=0.1)

    def _new_ready_job(
        self,
        *,
        worker_type: str = "test",
        priority: float = 0,
        max_attempts: int = 3,
        dependencies: list[str] | None = None,
        job_id: str | None = None,
    ) -> str:
        identifier = self.jobs.create(
            "test_job",
            worker_type,
            {},
            priority=priority,
            max_attempts=max_attempts,
            dependencies=dependencies,
            job_id=job_id,
        )
        self.jobs.promote_eligible()
        return identifier

    def _claim_and_start(self, job_id: str, owner: str) -> tuple[str, str, Path]:
        claimed = self.jobs.claim_next(
            owner,
            lease_seconds=30,
            max_total=100,
            type_limits={},
        )
        self.assertIsNotNone(claimed)
        assert claimed is not None
        self.assertEqual(job_id, claimed.job_id)
        worker_id = f"worker_{job_id}_{claimed.attempt_count}"
        workspace = self.root / "workspaces" / job_id / f"attempt-{claimed.attempt_count}"
        workspace.mkdir(parents=True)
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
        self.jobs.start(job_id, owner, claimed.lease_token, worker_id, str(workspace))
        return claimed.lease_token, worker_id, workspace

    def _validate_and_succeed(
        self,
        job_id: str,
        owner: str,
        lease_token: str,
        worker_id: str,
        workspace: Path,
    ) -> None:
        results = Validator(self.database).run(
            job_id,
            workspace,
            [
                {
                    "type": "handler_evidence",
                    "name": "independent-test-evidence",
                    "passed": True,
                    "evidence": {"source": "deterministic-test"},
                }
            ],
            self.root / "logs" / job_id,
        )
        self.assertEqual(["PASS"], [result.status for result in results])
        self.jobs.succeed(job_id, owner, lease_token, worker_id)


class PayloadCredentialGuardTests(DatabaseTestCase):
    def test_literal_controller_credential_is_rejected_before_transaction(self) -> None:
        credential = "lf-fixture-credential-7d3210"
        jobs = JobRepository(
            self.database,
            secret_value_provider=lambda: (credential,),
        )

        with mock.patch.object(
            self.database,
            "transaction",
            side_effect=AssertionError("a database transaction was opened"),
        ) as transaction:
            with self.assertRaises(JobError) as raised:
                jobs.create(
                    "guarded",
                    "test",
                    {"nested": {"prompt": f"prefix:{credential}:suffix"}},
                )

        transaction.assert_not_called()
        self.assertNotIn(credential, str(raised.exception))
        self.assertEqual(
            "job payload contains a controller credential",
            str(raised.exception),
        )
        with self.database.connect() as connection:
            self.assertEqual(0, connection.execute("SELECT COUNT(*) FROM jobs").fetchone()[0])

    def test_json_escaped_controller_credential_is_rejected(self) -> None:
        credential = 'lf-fixture-"quoted"\\branch-5539'
        jobs = JobRepository(
            self.database,
            secret_value_provider=lambda: (credential,),
        )

        with self.assertRaisesRegex(JobError, "contains a controller credential"):
            jobs.create(
                "guarded",
                "test",
                {"prompt": f"prefix:{credential}:suffix"},
            )

    def test_surrounding_whitespace_is_normalized_before_comparison(self) -> None:
        credential = "lf-fixture-spaced-credential-4172"
        environment_value = f" \t{credential}\n "
        jobs = JobRepository(
            self.database,
            secret_value_provider=lambda: (environment_value,),
        )

        with self.assertRaisesRegex(JobError, "contains a controller credential"):
            jobs.create("guarded", "test", {"value": credential})

    def test_environment_provider_reads_only_credential_named_values(self) -> None:
        ordinary_value = "lf-fixture-ordinary-value-8219"
        credential = "lf-fixture-controller-secret-1903"

        class GuardedEnvironment(dict[str, str]):
            def get(self, key: str, default: str | None = None) -> str | None:
                if key in {
                    "ORDINARY_SETTING",
                    "TOKENIZERS_PARALLELISM",
                    "AUTH_ENDPOINT",
                    "CONTROLLER_PASSWORD_FILE",
                }:
                    raise AssertionError("read a non-credential environment value")
                return super().get(key, default)

        environment = GuardedEnvironment(
            {
                "ORDINARY_SETTING": ordinary_value,
                "TOKENIZERS_PARALLELISM": ordinary_value,
                "AUTH_ENDPOINT": ordinary_value,
                "CONTROLLER_PASSWORD_FILE": ordinary_value,
                "OPENAI_API_KEY": credential,
            }
        )
        jobs = JobRepository(
            self.database,
            secret_value_provider=lambda: _credential_values_from_environment(environment),
        )

        accepted = jobs.create("guarded", "test", {"value": ordinary_value})
        self.assertEqual(ordinary_value, jobs.get(accepted)["payload"]["value"])
        with self.assertRaisesRegex(JobError, "contains a controller credential"):
            jobs.create("guarded", "test", {"value": credential})

    def test_short_placeholders_and_nonsecret_references_are_ignored(self) -> None:
        values = (
            "",
            "short",
            "not-a-real-token",
            "/var/run/learnfactory/credential-reference.json",
            "https://auth.example.test/token",
        )
        jobs = JobRepository(
            self.database,
            secret_value_provider=lambda: values,
        )

        job_id = jobs.create("guarded", "test", {"documented_values": list(values)})
        self.assertIsNotNone(jobs.get(job_id))

    def test_credential_words_without_the_value_do_not_trigger(self) -> None:
        credential = "lf-fixture-controller-token-6431"
        jobs = JobRepository(
            self.database,
            secret_value_provider=lambda: (credential,),
        )

        job_id = jobs.create(
            "guarded",
            "test",
            {"text": "Discuss token, auth, secret, password, and credential handling."},
        )
        self.assertIsNotNone(jobs.get(job_id))

    def test_provider_failure_is_reported_without_provider_details(self) -> None:
        sensitive_detail = "lf-fixture-provider-detail-9081"

        def fail_provider() -> tuple[str, ...]:
            raise RuntimeError(sensitive_detail)

        jobs = JobRepository(self.database, secret_value_provider=fail_provider)
        with self.assertRaises(JobError) as raised:
            jobs.create("guarded", "test", {})
        self.assertEqual(
            "job payload credential check could not be completed",
            str(raised.exception),
        )
        self.assertNotIn(sensitive_detail, str(raised.exception))


class MigrationTests(unittest.TestCase):
    def test_migrations_are_idempotent_and_checksums_are_enforced(self) -> None:
        with tempfile.TemporaryDirectory(prefix="learnfactory-migration-") as raw_root:
            root = Path(raw_root)
            migrations = _copy_migrations(root / "migrations")
            migration = migrations / INITIAL_MIGRATION.name
            database = Database(root / "factory.db", migrations)

            self.assertEqual([item.name for item in MIGRATION_FILES], database.migrate())
            self.assertEqual([], database.migrate())

            expected_checksum = hashlib.sha256(migration.read_bytes()).hexdigest()
            with database.connect() as connection:
                row = connection.execute(
                    "SELECT version,checksum FROM schema_migrations WHERE version=?",
                    (INITIAL_MIGRATION.name,),
                ).fetchone()
            self.assertIsNotNone(row)
            assert row is not None
            self.assertEqual(INITIAL_MIGRATION.name, row["version"])
            self.assertEqual(expected_checksum, row["checksum"])

            migration.write_text(
                migration.read_text(encoding="utf-8") + "\n-- checksum mutation\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(MigrationError, "applied migration changed"):
                database.migrate()

    def test_concurrent_migration_startup_is_serialized(self) -> None:
        with tempfile.TemporaryDirectory(prefix="learnfactory-migration-race-") as raw_root:
            root = Path(raw_root)
            migrations = _copy_migrations(root / "migrations")
            database_path = root / "factory.db"
            context = multiprocessing.get_context("spawn")
            results = context.Queue()
            processes = [
                context.Process(
                    target=_migrate_in_process,
                    args=(str(database_path), str(migrations), results),
                )
                for _ in range(6)
            ]
            for process in processes:
                process.start()
            outcomes = [results.get(timeout=40) for _ in processes]
            for process in processes:
                process.join(timeout=10)
            self.assertEqual([], [outcome for outcome in outcomes if outcome[0] == "error"])
            self.assertTrue(all(process.exitcode == 0 for process in processes))
            with Database(database_path, migrations).connect() as connection:
                count = connection.execute(
                    "SELECT COUNT(*) AS n FROM schema_migrations"
                ).fetchone()["n"]
            self.assertEqual(len(MIGRATION_FILES), count)


class StateAndDependencyTests(DatabaseTestCase):
    EXPECTED_TRANSITIONS = {
        ("DISCOVERED", "READY"),
        ("DISCOVERED", "BLOCKED"),
        ("DISCOVERED", "CANCELLED"),
        ("READY", "CLAIMED"),
        ("READY", "BLOCKED"),
        ("READY", "CANCELLED"),
        ("CLAIMED", "RUNNING"),
        ("CLAIMED", "RETRY_WAIT"),
        ("CLAIMED", "FAILED"),
        ("CLAIMED", "CANCELLED"),
        ("RUNNING", "SUCCEEDED"),
        ("RUNNING", "RETRY_WAIT"),
        ("RUNNING", "BLOCKED"),
        ("RUNNING", "FAILED"),
        ("RUNNING", "CANCELLED"),
        ("RETRY_WAIT", "READY"),
        ("RETRY_WAIT", "FAILED"),
        ("RETRY_WAIT", "CANCELLED"),
        ("BLOCKED", "READY"),
        ("BLOCKED", "CANCELLED"),
        ("FAILED", "READY"),
        ("FAILED", "CANCELLED"),
    }

    def test_job_id_is_a_single_safe_path_component(self) -> None:
        with self.assertRaisesRegex(JobError, "invalid job id"):
            self.jobs.create("test", "test", {}, job_id="job_x/../../../escape")
        with self.assertRaisesRegex(sqlite3.IntegrityError, "invalid job id"):
            with self.database.transaction(immediate=True) as connection:
                connection.execute(
                    """
                    INSERT INTO jobs(
                        job_id,type,worker_type,state,payload_json,created_at
                    ) VALUES ('job_bad/path','test','test','DISCOVERED','{}',?)
                    """,
                    (time.time(),),
                )

    def test_transition_table_and_trigger_allow_only_declared_edges(self) -> None:
        job_id = self.jobs.create("transition", "test", {})
        with self.database.connect() as connection:
            actual = {
                (row["from_state"], row["to_state"])
                for row in connection.execute(
                    "SELECT from_state,to_state FROM allowed_job_transitions"
                )
            }
        self.assertEqual(self.EXPECTED_TRANSITIONS, actual)

        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                "UPDATE jobs SET state='READY' WHERE job_id=?",
                (job_id,),
            )
        with self.assertRaisesRegex(sqlite3.IntegrityError, "invalid job state transition"):
            with self.database.transaction(immediate=True) as connection:
                connection.execute(
                    "UPDATE jobs SET state='SUCCEEDED' WHERE job_id=?",
                    (job_id,),
                )
        self.assertEqual(JobState.READY.value, self.jobs.get(job_id)["state"])

    def test_dependency_waits_for_validated_parent_success(self) -> None:
        parent = self.jobs.create("parent", "test", {}, priority=10)
        child = self.jobs.create("child", "test", {}, dependencies=[parent])

        self.assertEqual(1, self.jobs.promote_eligible())
        self.assertEqual(JobState.READY.value, self.jobs.get(parent)["state"])
        self.assertEqual(JobState.DISCOVERED.value, self.jobs.get(child)["state"])

        lease_token, worker_id, workspace = self._claim_and_start(parent, "owner-parent")
        self._validate_and_succeed(
            parent, "owner-parent", lease_token, worker_id, workspace
        )

        self.assertEqual(1, self.jobs.promote_eligible())
        self.assertEqual(JobState.READY.value, self.jobs.get(child)["state"])

    def test_failed_dependency_blocks_child(self) -> None:
        parent = self.jobs.create("parent", "test", {}, priority=10, max_attempts=1)
        child = self.jobs.create("child", "test", {}, dependencies=[parent])
        self.jobs.promote_eligible()
        claimed = self.jobs.claim_next(
            "owner-parent",
            lease_seconds=30,
            max_total=1,
            type_limits={},
        )
        self.assertIsNotNone(claimed)
        self.assertEqual(
            JobState.FAILED,
            self.jobs.fail(
                parent,
                "owner-parent",
                claimed.lease_token,
                None,
                kind="deterministic",
                error="permanent failure",
                retryable=False,
            ),
        )

        self.assertEqual(0, self.jobs.promote_eligible())
        record = self.jobs.get(child)
        self.assertEqual(JobState.BLOCKED.value, record["state"])
        self.assertEqual("blocked_dependency", record["failure_kind"])

        with self.assertRaisesRegex(JobError, "unsatisfied dependencies"):
            self.jobs.retry(child)

        self.jobs.retry(parent)
        parent_record = self.jobs.get(parent)
        self.assertEqual(JobState.READY.value, parent_record["state"])
        self.assertEqual(2, parent_record["max_attempts"])
        lease_token, worker_id, workspace = self._claim_and_start(parent, "owner-parent-2")
        self._validate_and_succeed(parent, "owner-parent-2", lease_token, worker_id, workspace)

        self.assertEqual(1, self.jobs.promote_eligible())
        self.assertEqual(JobState.READY.value, self.jobs.get(child)["state"])


class ClaimAndCapacityTests(DatabaseTestCase):
    def test_capacity_scan_does_not_starve_type_beyond_first_hundred_jobs(self) -> None:
        for index in range(101):
            self.jobs.create(
                "bulk",
                "ingestion",
                {},
                priority=1000 - index,
                job_id=f"job_bulk_{index:03d}",
            )
        student = self.jobs.create(
            "student", "student", {}, priority=1, job_id="job_fair_student"
        )
        self.jobs.promote_eligible()
        first = self.jobs.claim_next(
            "owner-ingestion", 30, max_total=2,
            type_limits={"ingestion": 1, "student": 1},
        )
        second = self.jobs.claim_next(
            "owner-student", 30, max_total=2,
            type_limits={"ingestion": 1, "student": 1},
        )
        self.assertEqual("ingestion", first.worker_type if first else None)
        self.assertEqual(student, second.job_id if second else None)

    def test_atomic_claim_across_threads_dispatches_job_once(self) -> None:
        job_id = self._new_ready_job()
        contenders = 8
        barrier = threading.Barrier(contenders)

        def claim(index: int) -> str | None:
            repository = JobRepository(Database(self.database_path, self.migrations))
            barrier.wait(timeout=10)
            result = repository.claim_next(
                f"thread-owner-{index}",
                lease_seconds=30,
                max_total=contenders,
                type_limits={},
            )
            return result.job_id if result is not None else None

        with ThreadPoolExecutor(max_workers=contenders) as executor:
            results = list(executor.map(claim, range(contenders)))

        self.assertEqual([job_id], [result for result in results if result is not None])
        record = self.jobs.get(job_id)
        self.assertEqual(JobState.CLAIMED.value, record["state"])
        self.assertEqual(1, record["attempt_count"])

    def test_atomic_claim_across_spawned_processes_dispatches_job_once(self) -> None:
        # Put this database on the same filesystem as the repository. In production that is
        # NFSv3, so this test exercises the real lock manager while retaining tempfile cleanup.
        with tempfile.NamedTemporaryFile(
            prefix=".learnfactory-claim-race-",
            suffix=".db",
            dir=REPOSITORY_ROOT,
            delete=False,
        ) as database_file:
            race_database_path = Path(database_file.name)
        self.addCleanup(_remove_sqlite_test_files, race_database_path)
        race_database = Database(race_database_path, REPOSITORY_ROOT / "migrations")
        race_database.migrate()
        race_jobs = JobRepository(race_database)
        job_id = race_jobs.create("claim-race", "test", {})
        self.assertEqual(1, race_jobs.promote_eligible())
        context = multiprocessing.get_context("spawn")
        start_event = context.Event()
        ready_queue = context.Queue()
        result_queue = context.Queue()
        processes = [
            context.Process(
                target=_claim_in_process,
                args=(
                    str(race_database_path),
                    str(REPOSITORY_ROOT / "migrations"),
                    f"process-owner-{index}",
                    start_event,
                    ready_queue,
                    result_queue,
                ),
            )
            for index in range(4)
        ]
        for process in processes:
            process.start()
        try:
            ready = {ready_queue.get(timeout=30) for _ in processes}
            self.assertEqual(4, len(ready))
            start_event.set()
            outcomes = [result_queue.get(timeout=40) for _ in processes]
        finally:
            start_event.set()
            for process in processes:
                process.join(timeout=10)
                if process.is_alive():
                    process.terminate()
                    process.join(timeout=10)

        errors = [outcome for outcome in outcomes if outcome[0] == "error"]
        self.assertEqual([], errors)
        self.assertTrue(all(process.exitcode == 0 for process in processes))
        claimed_ids = [outcome[2] for outcome in outcomes if outcome[2] is not None]
        self.assertEqual([job_id], claimed_ids)
        self.assertEqual(1, race_jobs.get(job_id)["attempt_count"])

    def test_worker_type_capacity_skips_saturated_higher_priority_type(self) -> None:
        first_ingestion = self.jobs.create(
            "ingest-1", "ingestion", {}, priority=30, job_id="job_ingest_first"
        )
        second_ingestion = self.jobs.create(
            "ingest-2", "ingestion", {}, priority=20, job_id="job_ingest_second"
        )
        student = self.jobs.create(
            "student", "student", {}, priority=10, job_id="job_student"
        )
        self.assertEqual(3, self.jobs.promote_eligible())
        limits = {"ingestion": 1, "student": 1}

        first = self.jobs.claim_next(
            "owner-1", lease_seconds=30, max_total=3, type_limits=limits
        )
        second = self.jobs.claim_next(
            "owner-2", lease_seconds=30, max_total=3, type_limits=limits
        )
        third = self.jobs.claim_next(
            "owner-3", lease_seconds=30, max_total=3, type_limits=limits
        )

        self.assertEqual(first_ingestion, first.job_id if first else None)
        self.assertEqual(student, second.job_id if second else None)
        self.assertIsNone(third)
        self.assertEqual(JobState.READY.value, self.jobs.get(second_ingestion)["state"])


class RecoveryAndValidationGateTests(DatabaseTestCase):
    def test_start_rejects_cancelled_or_expired_claim(self) -> None:
        cancelled = self._new_ready_job()
        cancelled_claim = self.jobs.claim_next(
            "owner-cancelled", 30, max_total=1, type_limits={}
        )
        assert cancelled_claim is not None
        self.jobs.cancel(cancelled)
        with self.assertRaisesRegex(JobError, "cannot start"):
            self.jobs.start(
                cancelled, "owner-cancelled", cancelled_claim.lease_token,
                "worker-cancelled", str(self.root / "cancelled"),
            )

        # Reconcile the cancelled claim so capacity is available for the next one.
        expiry = self.jobs.get(cancelled)["lease_expires_at"]
        self.jobs.recover_expired(expiry + 0.001)
        expired = self._new_ready_job()
        expired_claim = self.jobs.claim_next(
            "owner-expired", 30, max_total=1, type_limits={}
        )
        assert expired_claim is not None
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                "UPDATE jobs SET lease_expires_at=? WHERE job_id=?",
                (time.time() - 1, expired),
            )
        with self.assertRaisesRegex(JobError, "cannot start"):
            self.jobs.start(
                expired, "owner-expired", expired_claim.lease_token,
                "worker-expired", str(self.root / "expired"),
            )

    def test_block_honors_concurrent_cancel_request(self) -> None:
        job_id = self._new_ready_job()
        lease_token, worker_id, _ = self._claim_and_start(job_id, "owner")
        self.jobs.cancel(job_id)
        self.jobs.block(
            job_id,
            "owner",
            lease_token,
            worker_id,
            kind="blocked_authentication",
            error="login needed",
        )
        self.assertEqual(JobState.CANCELLED.value, self.jobs.get(job_id)["state"])
    def test_expired_lease_cannot_be_resurrected_by_late_heartbeat(self) -> None:
        job_id = self._new_ready_job()
        claimed = self.jobs.claim_next(
            "late-owner", lease_seconds=1, max_total=1, type_limits={}
        )
        assert claimed is not None
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                "UPDATE jobs SET lease_expires_at=? WHERE job_id=?",
                (time.time() - 1, job_id),
            )
        self.assertFalse(
            self.jobs.heartbeat(
                job_id, "late-owner", claimed.lease_token, "missing-worker", 30
            )
        )
        self.assertLess(self.jobs.get(job_id)["lease_expires_at"], time.time())

    def test_every_worker_terminal_transition_rejects_an_expired_lease(self) -> None:
        def fail(job_id: str, token: str, worker_id: str) -> None:
            self.jobs.fail(
                job_id, "owner", token, worker_id,
                kind="late-worker", error="late failure", retryable=False,
            )

        def block(job_id: str, token: str, worker_id: str) -> None:
            self.jobs.block(
                job_id, "owner", token, worker_id,
                kind="late-worker", error="late block",
            )

        def interrupt(job_id: str, token: str, worker_id: str) -> None:
            self.jobs.interrupt(
                job_id, "owner", token, worker_id, reason="late interruption"
            )

        def finish_cancelled(job_id: str, token: str, worker_id: str) -> None:
            self.jobs.finish_cancelled(job_id, "owner", token, worker_id)

        cases = {
            "fail": (fail, False),
            "block": (block, False),
            "interrupt": (interrupt, False),
            "finish_cancelled": (finish_cancelled, True),
        }
        for name, (operation, request_cancel) in cases.items():
            with self.subTest(operation=name):
                job_id = self._new_ready_job(
                    job_id=f"job_expired_{name}", max_attempts=1
                )
                token, worker_id, _ = self._claim_and_start(job_id, "owner")
                if request_cancel:
                    self.jobs.cancel(job_id)
                with self.database.transaction(immediate=True) as connection:
                    connection.execute(
                        "UPDATE jobs SET lease_expires_at=? WHERE job_id=?",
                        (time.time() - 1, job_id),
                    )
                with self.assertRaisesRegex(JobError, "expired"):
                    operation(job_id, token, worker_id)
                self.assertEqual(JobState.RUNNING.value, self.jobs.get(job_id)["state"])
                self.assertEqual(1, self.jobs.recover_expired())

    def test_heartbeat_lease_is_measured_after_waiting_for_database_lock(self) -> None:
        job_id = self._new_ready_job()
        claimed = self.jobs.claim_next(
            "delayed-owner", lease_seconds=10, max_total=1, type_limits={}
        )
        assert claimed is not None
        lock_acquired = threading.Event()
        release_lock = threading.Event()

        def hold_write_lock() -> None:
            with self.database.transaction(immediate=True):
                lock_acquired.set()
                release_lock.wait(timeout=5)

        holder = threading.Thread(target=hold_write_lock)
        holder.start()
        self.assertTrue(lock_acquired.wait(timeout=2))
        timer = threading.Timer(0.35, release_lock.set)
        timer.start()
        self.assertTrue(
            self.jobs.heartbeat(
                job_id, "delayed-owner", claimed.lease_token, "missing-worker", 0.5
            )
        )
        completed_at = time.time()
        holder.join(timeout=2)
        timer.cancel()
        self.assertGreater(
            self.jobs.get(job_id)["lease_expires_at"],
            completed_at + 0.35,
        )

    def test_cancel_request_fences_success_and_expired_recovery_cancels(self) -> None:
        job_id = self._new_ready_job()
        lease_token, worker_id, workspace = self._claim_and_start(job_id, "owner")
        Validator(self.database).run(
            job_id,
            workspace,
            [{"type": "handler_evidence", "name": "pass", "passed": True}],
            self.root / "logs" / job_id,
            attempt_number=1,
        )
        self.jobs.cancel(job_id)
        with self.assertRaisesRegex(JobError, "cancelled job"):
            self.jobs.succeed(job_id, "owner", lease_token, worker_id)
        expiry = self.jobs.get(job_id)["lease_expires_at"]
        self.assertEqual(1, self.jobs.recover_expired(expiry + 0.001))
        self.assertEqual(JobState.CANCELLED.value, self.jobs.get(job_id)["state"])

    def test_validation_failure_is_scoped_to_original_attempt(self) -> None:
        job_id = self._new_ready_job(max_attempts=2)
        first_token, first_worker, first_workspace = self._claim_and_start(job_id, "owner-1")
        Validator(self.database).run(
            job_id,
            first_workspace,
            [{"type": "handler_evidence", "name": "first-fail", "passed": False}],
            self.root / "logs" / job_id / "attempt-1",
            attempt_number=1,
        )
        self.assertEqual(
            JobState.RETRY_WAIT,
            self.jobs.fail(
                job_id,
                "owner-1",
                first_token,
                first_worker,
                kind="validation_failure",
                error="first attempt failed",
                retryable=True,
            ),
        )
        retry_at = self.jobs.get(job_id)["retry_at"]
        self.jobs.promote_eligible(retry_at)
        second_token, second_worker, second_workspace = self._claim_and_start(job_id, "owner-2")
        Validator(self.database).run(
            job_id,
            second_workspace,
            [{"type": "handler_evidence", "name": "second-pass", "passed": True}],
            self.root / "logs" / job_id / "attempt-2",
            attempt_number=2,
        )
        self.jobs.succeed(job_id, "owner-2", second_token, second_worker)
        self.assertEqual(JobState.SUCCEEDED.value, self.jobs.get(job_id)["state"])
    def test_lease_recovery_and_attempt_count_survive_repository_restart(self) -> None:
        job_id = self._new_ready_job(max_attempts=2)
        first = self.jobs.claim_next(
            "owner-first",
            lease_seconds=1,
            max_total=1,
            type_limits={},
        )
        self.assertIsNotNone(first)
        first_record = self.jobs.get(job_id)
        self.assertEqual(1, first_record["attempt_count"])
        self.assertEqual(1, self.jobs.recover_expired(first_record["lease_expires_at"] + 0.001))
        retry_record = self.jobs.get(job_id)
        self.assertEqual(JobState.RETRY_WAIT.value, retry_record["state"])
        self.assertEqual("stall", retry_record["failure_kind"])

        restarted_database = Database(self.database_path, self.migrations)
        self.assertEqual([], restarted_database.migrate())
        restarted = JobRepository(restarted_database, retry_base=0.01, retry_max=0.1)
        self.assertEqual(1, restarted.promote_eligible(at=retry_record["retry_at"]))
        second = restarted.claim_next(
            "owner-second",
            lease_seconds=1,
            max_total=1,
            type_limits={},
        )
        self.assertIsNotNone(second)
        self.assertEqual(2, second.attempt_count if second else None)
        second_record = restarted.get(job_id)
        self.assertEqual(
            1,
            restarted.recover_expired(second_record["lease_expires_at"] + 0.001),
        )

        after_second_restart = JobRepository(Database(self.database_path, self.migrations))
        final = after_second_restart.get(job_id)
        self.assertEqual(JobState.FAILED.value, final["state"])
        self.assertEqual(2, final["attempt_count"])
        self.assertEqual("stall", final["failure_kind"])
        with self.database.connect() as connection:
            lease_events = connection.execute(
                "SELECT COUNT(*) AS n FROM events WHERE job_id=? AND type='LEASE_EXPIRED'",
                (job_id,),
            ).fetchone()["n"]
        self.assertEqual(2, lease_events)

    def test_reclaimed_job_rejects_previous_lease_token_even_for_same_owner(self) -> None:
        job_id = self._new_ready_job(max_attempts=2)
        first = self.jobs.claim_next(
            "reused-owner",
            lease_seconds=1,
            max_total=1,
            type_limits={},
        )
        self.assertIsNotNone(first)
        assert first is not None
        first_worker_id = "worker_expired_attempt"
        first_workspace = self.root / "workspaces" / job_id / "attempt-1"
        first_workspace.mkdir(parents=True)
        timestamp = time.time()
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                """
                INSERT INTO workers(
                    worker_id,type,state,started_at,last_activity,current_job,workspace
                ) VALUES (?,?,?,?,?,?,?)
                """,
                (
                    first_worker_id,
                    "test",
                    "STARTING",
                    timestamp,
                    timestamp,
                    job_id,
                    str(first_workspace),
                ),
            )
        self.jobs.start(
            job_id,
            "reused-owner",
            first.lease_token,
            first_worker_id,
            str(first_workspace),
        )
        first_record = self.jobs.get(job_id)
        self.jobs.recover_expired(first_record["lease_expires_at"] + 0.001)
        retry_record = self.jobs.get(job_id)
        self.jobs.promote_eligible(at=retry_record["retry_at"])
        second = self.jobs.claim_next(
            "reused-owner",
            lease_seconds=30,
            max_total=1,
            type_limits={},
        )
        self.assertIsNotNone(second)
        assert second is not None
        self.assertNotEqual(first.lease_token, second.lease_token)

        worker_id = "worker_fenced_attempt"
        workspace = self.root / "workspaces" / job_id / "attempt-2"
        workspace.mkdir(parents=True)
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
        self.jobs.start(
            job_id,
            "reused-owner",
            second.lease_token,
            worker_id,
            str(workspace),
        )
        current_lease_expiry = self.jobs.get(job_id)["lease_expires_at"]

        self.assertFalse(
            self.jobs.heartbeat(
                job_id,
                "reused-owner",
                first.lease_token,
                first_worker_id,
                lease_seconds=300,
            )
        )
        self.assertEqual(current_lease_expiry, self.jobs.get(job_id)["lease_expires_at"])
        with self.database.connect() as connection:
            expired_worker_state = connection.execute(
                "SELECT state FROM workers WHERE worker_id=?",
                (first_worker_id,),
            ).fetchone()["state"]
        self.assertEqual("LOST", expired_worker_state)
        with self.assertRaisesRegex(JobError, "cannot fail unowned active job"):
            self.jobs.fail(
                job_id,
                "reused-owner",
                first.lease_token,
                first_worker_id,
                kind="stale-worker",
                error="must be fenced",
                retryable=False,
            )

        passed = Validator(self.database).run(
            job_id,
            workspace,
            [{"type": "handler_evidence", "name": "pass", "passed": True}],
            self.root / "logs" / job_id,
        )
        self.assertEqual(["PASS"], [result.status for result in passed])
        with self.assertRaisesRegex(JobError, "cannot succeed unowned running job"):
            self.jobs.succeed(
                job_id,
                "reused-owner",
                first.lease_token,
                worker_id,
            )
        self.assertEqual(JobState.RUNNING.value, self.jobs.get(job_id)["state"])

        self.jobs.succeed(
            job_id,
            "reused-owner",
            second.lease_token,
            worker_id,
        )
        final = self.jobs.get(job_id)
        self.assertEqual(JobState.SUCCEEDED.value, final["state"])
        self.assertIsNone(final["lease_token"])

    def test_running_job_cannot_succeed_without_external_validation(self) -> None:
        job_id = self._new_ready_job()
        lease_token, worker_id, workspace = self._claim_and_start(job_id, "owner")

        with self.assertRaisesRegex(JobError, "cannot succeed without all external validations"):
            self.jobs.succeed(job_id, "owner", lease_token, worker_id)
        self.assertEqual(JobState.RUNNING.value, self.jobs.get(job_id)["state"])

        failed = Validator(self.database).run(
            job_id,
            workspace,
            [
                {
                    "type": "handler_evidence",
                    "name": "independent-failure",
                    "passed": False,
                    "evidence": {"failure": "hidden test failed"},
                }
            ],
            self.root / "logs" / job_id,
        )
        self.assertEqual(["FAIL"], [result.status for result in failed])
        with self.assertRaisesRegex(JobError, "cannot succeed without all external validations"):
            self.jobs.succeed(job_id, "owner", lease_token, worker_id)
        self.assertEqual(JobState.RUNNING.value, self.jobs.get(job_id)["state"])


if __name__ == "__main__":
    unittest.main()
