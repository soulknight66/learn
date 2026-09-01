from __future__ import annotations

import contextlib
import hashlib
import json
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

from learnfactory import jobs as jobs_module
from learnfactory import publication as publication_module
from learnfactory.db import (
    AuthorizerGuardError,
    ClosingConnection,
    Database,
    MigrationError,
)
from learnfactory.jobs import (
    JobError,
    JobRepository,
    JobState,
    PublicationCallbackError,
    UnsatisfiedDependencyError,
    _credential_values_from_environment,
)
from learnfactory.publication import (
    PublicationAccessError,
    PublicationScope,
    restricted_publication_connection,
)
from learnfactory.util import tree_sha256
from learnfactory.validation import Validator
from learnfactory.workspace import PreparedArtifact


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


def _migrate_in_process_after_signal(
    database_path: str,
    migrations_path: str,
    ready_queue: object,
    start_event: object,
    result_queue: object,
) -> None:
    try:
        database = Database(
            Path(database_path),
            Path(migrations_path),
            busy_timeout_seconds=0.1,
        )
        ready_queue.put("ready")  # type: ignore[attr-defined]
        if not start_event.wait(20):  # type: ignore[attr-defined]
            result_queue.put(("error", "start event timed out"))  # type: ignore[attr-defined]
            return
        applied = database.migrate()
        database.verify_migrations()
        with database.connect() as connection:
            mode = str(connection.execute("PRAGMA journal_mode").fetchone()[0])
        result_queue.put(("ok", applied, mode))  # type: ignore[attr-defined]
    except MigrationError as error:
        result_queue.put(("migration_error", str(error)))  # type: ignore[attr-defined]
    except BaseException:
        result_queue.put(("raw_error", traceback.format_exc()))  # type: ignore[attr-defined]


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
        self.jobs.start(
            job_id,
            owner,
            claimed.lease_token,
            worker_id,
            str(workspace),
            lease_seconds=30,
        )
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
            with sqlite3.connect(database.path) as connection:
                mode = connection.execute("PRAGMA journal_mode = WAL").fetchone()[0]
            self.assertEqual("wal", str(mode).lower())
            with self.assertRaisesRegex(MigrationError, "applied migration changed"):
                database.migrate()
            with sqlite3.connect(database.path) as connection:
                unchanged_mode = connection.execute("PRAGMA journal_mode").fetchone()[0]
            self.assertEqual("wal", str(unchanged_mode).lower())

    def test_retry_allowance_migration_backfills_existing_jobs_to_zero(self) -> None:
        with tempfile.TemporaryDirectory(prefix="learnfactory-retry-migration-") as raw:
            root = Path(raw)
            migrations = root / "migrations"
            migrations.mkdir()
            allowance_migration = next(
                item for item in MIGRATION_FILES if item.name.startswith("020_")
            )
            for migration in MIGRATION_FILES:
                if migration != allowance_migration:
                    shutil.copy2(migration, migrations / migration.name)
            database = Database(root / "factory.db", migrations)
            database.migrate()
            jobs = JobRepository(database)
            job_id = jobs.create(
                "pre-allowance", "test", {}, max_attempts=1
            )

            shutil.copy2(allowance_migration, migrations / allowance_migration.name)
            self.assertEqual([allowance_migration.name], database.migrate())
            record = JobRepository(database).get(job_id)
            assert record is not None
            self.assertEqual(1, record["max_attempts"])
            self.assertEqual(0, record["retry_allowance"])

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

    def test_fully_applied_migration_fast_path_never_waits_for_write_lock(self) -> None:
        with tempfile.TemporaryDirectory(prefix="learnfactory-migration-fast-") as raw:
            root = Path(raw)
            migrations = _copy_migrations(root / "migrations")
            database = Database(root / "factory.db", migrations)
            database.migrate()
            completed = threading.Event()
            result: list[list[str]] = []
            failures: list[BaseException] = []

            def migrate_again() -> None:
                try:
                    result.append(database.migrate())
                except BaseException as error:
                    failures.append(error)
                finally:
                    completed.set()

            with database.transaction(immediate=True):
                worker = threading.Thread(target=migrate_again)
                worker.start()
                self.assertTrue(
                    completed.wait(timeout=2),
                    "an up-to-date migration attempted to acquire a write lock",
                )
            worker.join(timeout=2)
            self.assertFalse(worker.is_alive())
            self.assertEqual([], failures)
            self.assertEqual([[]], result)

    def test_ordinary_connections_and_current_migrations_do_not_assign_journal_mode(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(prefix="learnfactory-journal-fast-") as raw:
            root = Path(raw)
            migrations = _copy_migrations(root / "migrations")
            database = Database(root / "factory.db", migrations)
            database.migrate()
            statements: list[str] = []

            class TracedConnection(sqlite3.Connection):
                def __init__(self, *args: object, **kwargs: object):
                    super().__init__(*args, **kwargs)
                    self.set_trace_callback(statements.append)

                def __exit__(
                    self,
                    exc_type: object,
                    exc_value: object,
                    traceback: object,
                ) -> bool:
                    try:
                        return bool(
                            super().__exit__(exc_type, exc_value, traceback)
                        )
                    finally:
                        self.close()

            with mock.patch(
                "learnfactory.db.ClosingConnection", TracedConnection
            ):
                fresh = Database(root / "factory.db", migrations)
                with fresh.connect() as connection:
                    connection.execute("SELECT 1").fetchone()
                fresh.migrate()

            normalized = [statement.upper().replace(" ", "") for statement in statements]
            self.assertFalse(
                any("PRAGMAJOURNAL_MODE=" in statement for statement in normalized)
            )
            self.assertNotIn("BEGINIMMEDIATE", normalized)

    def test_migration_repairs_an_incompatible_persistent_journal_mode(self) -> None:
        with tempfile.TemporaryDirectory(prefix="learnfactory-journal-repair-") as raw:
            root = Path(raw)
            migrations = _copy_migrations(root / "migrations")
            database = Database(root / "factory.db", migrations)
            database.migrate()
            with sqlite3.connect(database.path) as connection:
                mode = connection.execute("PRAGMA journal_mode = WAL").fetchone()[0]
            self.assertEqual("wal", str(mode).lower())

            self.assertEqual([], Database(database.path, migrations).migrate())

            with sqlite3.connect(database.path) as connection:
                repaired = connection.execute("PRAGMA journal_mode").fetchone()[0]
            self.assertEqual("delete", str(repaired).lower())

    def test_six_processes_concurrently_normalize_current_wal_database(self) -> None:
        with tempfile.TemporaryDirectory(prefix="learnfactory-journal-race-") as raw:
            root = Path(raw)
            migrations = _copy_migrations(root / "migrations")
            database_path = root / "factory.db"
            database = Database(database_path, migrations)
            database.migrate()
            with sqlite3.connect(database_path) as connection:
                mode = connection.execute("PRAGMA journal_mode = WAL").fetchone()[0]
            self.assertEqual("wal", str(mode).lower())

            context = multiprocessing.get_context("spawn")
            ready = context.Queue()
            results = context.Queue()
            start = context.Event()
            processes = [
                context.Process(
                    target=_migrate_in_process_after_signal,
                    args=(
                        str(database_path),
                        str(migrations),
                        ready,
                        start,
                        results,
                    ),
                )
                for _ in range(6)
            ]
            for process in processes:
                process.start()
            for _ in processes:
                self.assertEqual("ready", ready.get(timeout=20))
            start.set()
            outcomes = [results.get(timeout=30) for _ in processes]
            for process in processes:
                process.join(timeout=10)

            self.assertEqual([], [item for item in outcomes if item[0] != "ok"])
            self.assertTrue(all(item[2].lower() == "delete" for item in outcomes))
            self.assertTrue(all(process.exitcode == 0 for process in processes))
            with sqlite3.connect(database_path) as connection:
                repaired = connection.execute("PRAGMA journal_mode").fetchone()[0]
                ledger = connection.execute(
                    "SELECT version,checksum FROM schema_migrations ORDER BY version"
                ).fetchall()
            self.assertEqual("delete", str(repaired).lower())
            self.assertEqual([item.name for item in MIGRATION_FILES], [row[0] for row in ledger])
            self.assertEqual(
                [hashlib.sha256(item.read_bytes()).hexdigest() for item in MIGRATION_FILES],
                [row[1] for row in ledger],
            )

    def test_blocked_journal_normalization_has_a_real_wall_time_bound(self) -> None:
        with tempfile.TemporaryDirectory(prefix="learnfactory-journal-bound-") as raw:
            root = Path(raw)
            migrations = _copy_migrations(root / "migrations")
            database_path = root / "factory.db"
            Database(database_path, migrations).migrate()
            with sqlite3.connect(database_path) as connection:
                mode = connection.execute("PRAGMA journal_mode = WAL").fetchone()[0]
            self.assertEqual("wal", str(mode).lower())
            holder = sqlite3.connect(database_path, isolation_level=None)
            try:
                holder.execute("BEGIN")
                holder.execute("SELECT COUNT(*) FROM sqlite_master").fetchone()
                started = time.monotonic()
                with self.assertRaisesRegex(
                    MigrationError,
                    "timed out normalizing SQLite journal mode",
                ):
                    Database(
                        database_path,
                        migrations,
                        busy_timeout_seconds=0.05,
                    ).migrate()
                elapsed = time.monotonic() - started
            finally:
                holder.rollback()
                holder.close()
            self.assertLess(elapsed, 1.5)

    def test_claim_fails_closed_until_cursor_migration_is_applied(self) -> None:
        with tempfile.TemporaryDirectory(prefix="learnfactory-rolling-schema-") as raw:
            root = Path(raw)
            migrations = _copy_migrations(root / "migrations")
            cursor_migration = migrations / "018_scheduler_claim_cursor.sql"
            cursor_bytes = cursor_migration.read_bytes()
            cursor_migration.unlink()
            database = Database(root / "factory.db", migrations)
            database.migrate()
            jobs = JobRepository(database)
            job_id = jobs.create("test_job", "test", {}, job_id="job_rolling_cursor")
            jobs.promote_eligible()

            with self.assertRaisesRegex(JobError, "claim cursor schema is unavailable"):
                jobs.claim_next(
                    "rolling-owner", 30, max_total=1, type_limits={}
                )
            self.assertEqual("READY", jobs.get(job_id)["state"])
            self.assertEqual(0, jobs.get(job_id)["attempt_count"])

            cursor_migration.write_bytes(cursor_bytes)
            self.assertEqual(["018_scheduler_claim_cursor.sql"], database.migrate())
            claimed = jobs.claim_next(
                "rolling-owner", 30, max_total=1, type_limits={}
            )
            self.assertEqual(job_id, claimed.job_id if claimed else None)


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

    def test_dependency_edges_advance_generation_and_freeze_after_discovery(
        self,
    ) -> None:
        first_parent = self.jobs.create(
            "parent", "test", {}, job_id="job_generation_parent_first"
        )
        second_parent = self.jobs.create(
            "parent", "test", {}, job_id="job_generation_parent_second"
        )
        child = self.jobs.create(
            "child", "test", {}, job_id="job_generation_child"
        )

        def generation() -> int:
            with self.database.connect() as connection:
                return int(
                    connection.execute(
                        """
                        SELECT generation FROM scheduler_generations
                        WHERE name='jobs_claim_projection'
                        """
                    ).fetchone()[0]
                )

        before_insert = generation()
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                "INSERT INTO job_dependencies(job_id,depends_on_job_id) VALUES (?,?)",
                (child, first_parent),
            )
        self.assertEqual(before_insert + 1, generation())

        before_update = generation()
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                """
                UPDATE job_dependencies SET depends_on_job_id=?
                WHERE job_id=? AND depends_on_job_id=?
                """,
                (second_parent, child, first_parent),
            )
        self.assertEqual(before_update + 1, generation())

        before_delete = generation()
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                "DELETE FROM job_dependencies WHERE job_id=?",
                (child,),
            )
        self.assertEqual(before_delete + 1, generation())

        self.assertEqual(3, self.jobs.promote_eligible())
        with self.assertRaisesRegex(
            sqlite3.IntegrityError,
            "dependencies may only be added to DISCOVERED jobs",
        ):
            with self.database.transaction(immediate=True) as connection:
                connection.execute(
                    "INSERT INTO job_dependencies(job_id,depends_on_job_id) VALUES (?,?)",
                    (child, first_parent),
                )

        old_child = self.jobs.create(
            "child",
            "test",
            {},
            dependencies=[first_parent],
            job_id="job_generation_old_ready_child",
        )
        new_child = self.jobs.create(
            "child", "test", {}, job_id="job_generation_new_discovered_child"
        )
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                "UPDATE jobs SET state='READY' WHERE job_id=?",
                (old_child,),
            )
        with self.assertRaisesRegex(
            sqlite3.IntegrityError,
            "changed between DISCOVERED jobs",
        ):
            with self.database.transaction(immediate=True) as connection:
                connection.execute(
                    """
                    UPDATE job_dependencies SET job_id=?
                    WHERE job_id=? AND depends_on_job_id=?
                    """,
                    (new_child, old_child, first_parent),
                )
        with self.database.connect() as connection:
            retained = connection.execute(
                """
                SELECT depends_on_job_id FROM job_dependencies
                WHERE job_id=?
                """,
                (old_child,),
            ).fetchone()
        self.assertEqual(first_parent, retained[0] if retained else None)

        # A DISCOVERED child's dependency graph is still mutable. Deleting its
        # prerequisite therefore cascades the edge and invalidates any
        # preselected claim through the generation trigger.
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                """
                INSERT INTO jobs(job_id,type,worker_type,state,payload_json,created_at)
                VALUES ('job_cascade_parent','test','test','DISCOVERED','{}',?)
                """,
                (time.time(),),
            )
            connection.execute(
                """
                INSERT INTO jobs(job_id,type,worker_type,state,payload_json,created_at)
                VALUES ('job_cascade_child','test','test','DISCOVERED','{}',?)
                """,
                (time.time(),),
            )
            connection.execute(
                """
                INSERT INTO job_dependencies(job_id,depends_on_job_id)
                VALUES ('job_cascade_child','job_cascade_parent')
                """
            )
        before_cascade = generation()
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                "DELETE FROM jobs WHERE job_id='job_cascade_parent'"
            )
        self.assertGreater(generation(), before_cascade)
        with self.database.connect() as connection:
            remaining = connection.execute(
                """
                SELECT COUNT(*) FROM job_dependencies
                WHERE job_id='job_cascade_child'
                """
            ).fetchone()[0]
        self.assertEqual(0, remaining)

    def test_dependency_delete_guard_preserves_active_graph_but_allows_child_cleanup(
        self,
    ) -> None:
        for suffix, target_state in (
            ("ready", "READY"),
            ("running", "RUNNING"),
            ("terminal", "CANCELLED"),
        ):
            with self.subTest(state=target_state):
                parent = f"job_delete_guard_parent_{suffix}"
                child = f"job_delete_guard_child_{suffix}"
                timestamp = time.time()
                with self.database.transaction(immediate=True) as connection:
                    connection.executemany(
                        """
                        INSERT INTO jobs(
                            job_id,type,worker_type,state,payload_json,created_at
                        ) VALUES (?,'test','test','DISCOVERED','{}',?)
                        """,
                        [(parent, timestamp), (child, timestamp)],
                    )
                    connection.execute(
                        """
                        INSERT INTO job_dependencies(job_id,depends_on_job_id)
                        VALUES (?,?)
                        """,
                        (child, parent),
                    )
                    if target_state == "READY":
                        connection.execute(
                            "UPDATE jobs SET state='READY' WHERE job_id=?",
                            (child,),
                        )
                    elif target_state == "RUNNING":
                        connection.execute(
                            """
                            UPDATE jobs
                            SET state='READY'
                            WHERE job_id=?
                            """,
                            (child,),
                        )
                        connection.execute(
                            """
                            UPDATE jobs
                            SET state='CLAIMED',owner='delete-guard-owner',
                                lease_expires_at=?,lease_token='delete-guard-lease'
                            WHERE job_id=?
                            """,
                            (timestamp + 60, child),
                        )
                        connection.execute(
                            "UPDATE jobs SET state='RUNNING' WHERE job_id=?",
                            (child,),
                        )
                    else:
                        connection.execute(
                            "UPDATE jobs SET state='CANCELLED' WHERE job_id=?",
                            (child,),
                        )

                with self.assertRaisesRegex(
                    sqlite3.IntegrityError,
                    "dependencies may only be removed from DISCOVERED jobs",
                ):
                    with self.database.transaction(immediate=True) as connection:
                        connection.execute(
                            """
                            DELETE FROM job_dependencies
                            WHERE job_id=? AND depends_on_job_id=?
                            """,
                            (child, parent),
                        )

                with self.assertRaisesRegex(
                    sqlite3.IntegrityError,
                    "dependencies may only be removed from DISCOVERED jobs",
                ):
                    with self.database.transaction(immediate=True) as connection:
                        connection.execute(
                            "DELETE FROM jobs WHERE job_id=?",
                            (parent,),
                        )

                with self.database.connect() as connection:
                    self.assertIsNotNone(
                        connection.execute(
                            "SELECT 1 FROM jobs WHERE job_id=?", (parent,)
                        ).fetchone()
                    )
                    self.assertIsNotNone(
                        connection.execute(
                            """
                            SELECT 1 FROM job_dependencies
                            WHERE job_id=? AND depends_on_job_id=?
                            """,
                            (child, parent),
                        ).fetchone()
                    )

                # SQLite removes the child row before running its outgoing FK
                # cascade. The guard therefore permits whole-child retention
                # cleanup while still fencing direct or parent-side deletion.
                with self.database.transaction(immediate=True) as connection:
                    connection.execute("DELETE FROM jobs WHERE job_id=?", (child,))
                with self.database.connect() as connection:
                    self.assertIsNone(
                        connection.execute(
                            "SELECT 1 FROM jobs WHERE job_id=?", (child,)
                        ).fetchone()
                    )
                    self.assertEqual(
                        0,
                        connection.execute(
                            """
                            SELECT COUNT(*) FROM job_dependencies
                            WHERE job_id=? OR depends_on_job_id=?
                            """,
                            (child, child),
                        ).fetchone()[0],
                    )
                    self.assertIsNotNone(
                        connection.execute(
                            "SELECT 1 FROM jobs WHERE job_id=?", (parent,)
                        ).fetchone()
                    )

    def test_preexisting_ready_job_with_cancelled_dependency_is_not_claimed(
        self,
    ) -> None:
        parent = self.jobs.create(
            "parent", "test", {}, job_id="job_invalid_ready_parent"
        )
        child = self.jobs.create(
            "child",
            "test",
            {},
            dependencies=[parent],
            job_id="job_invalid_ready_child",
            priority=100,
        )
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                "UPDATE jobs SET state='CANCELLED' WHERE job_id=?",
                (parent,),
            )
            # Model a legacy/corrupt writer that ignored dependency promotion.
            connection.execute(
                "UPDATE jobs SET state='READY' WHERE job_id=?",
                (child,),
            )

        claimed = self.jobs.claim_next(
            "invalid-ready-owner",
            lease_seconds=30,
            max_total=1,
            type_limits={},
        )

        self.assertIsNone(claimed)
        record = self.jobs.get(child)
        self.assertEqual(JobState.READY.value, record["state"])
        self.assertEqual(0, record["attempt_count"])

    def test_ready_job_with_missing_dependency_parent_fails_closed(self) -> None:
        child = self.jobs.create(
            "child", "test", {}, job_id="job_orphan_dependency_child"
        )
        connection = self.database.connect()
        try:
            connection.execute("PRAGMA foreign_keys=OFF")
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                INSERT INTO job_dependencies(job_id,depends_on_job_id)
                VALUES (?, 'job_missing_dependency_parent')
                """,
                (child,),
            )
            connection.execute(
                "UPDATE jobs SET state='READY' WHERE job_id=?",
                (child,),
            )
            connection.commit()
        finally:
            connection.close()

        self.assertIsNone(
            self.jobs.claim_next(
                "orphan-owner", 30, max_total=1, type_limits={}
            )
        )
        self.assertEqual(0, self.jobs.get(child)["attempt_count"])

    def test_database_rejects_success_with_unsatisfied_dependency(self) -> None:
        parent = self.jobs.create(
            "parent", "test", {}, job_id="job_success_guard_parent"
        )
        child = self.jobs.create(
            "child",
            "test",
            {},
            dependencies=[parent],
            job_id="job_success_guard_child",
        )
        timestamp = time.time()
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                "UPDATE jobs SET state='CANCELLED' WHERE job_id=?",
                (parent,),
            )
            connection.execute(
                "UPDATE jobs SET state='READY' WHERE job_id=?",
                (child,),
            )
            connection.execute(
                """
                UPDATE jobs SET state='CLAIMED',owner='fixture-owner',
                    lease_token='fixture-lease',lease_expires_at=?,heartbeat_at=?
                WHERE job_id=?
                """,
                (timestamp + 30, timestamp, child),
            )
            connection.execute(
                "UPDATE jobs SET state='RUNNING' WHERE job_id=?",
                (child,),
            )

        with self.assertRaisesRegex(
            sqlite3.IntegrityError,
            "cannot succeed job with unsatisfied dependencies",
        ):
            with self.database.transaction(immediate=True) as connection:
                connection.execute(
                    "UPDATE jobs SET state='SUCCEEDED' WHERE job_id=?",
                    (child,),
                )
        self.assertEqual(JobState.RUNNING.value, self.jobs.get(child)["state"])

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
        self.assertEqual(1, parent_record["max_attempts"])
        self.assertEqual(1, parent_record["retry_allowance"])
        lease_token, worker_id, workspace = self._claim_and_start(parent, "owner-parent-2")
        self._validate_and_succeed(parent, "owner-parent-2", lease_token, worker_id, workspace)

        self.assertEqual(1, self.jobs.promote_eligible())
        self.assertEqual(JobState.READY.value, self.jobs.get(child)["state"])

    def test_success_rejects_an_over_budget_active_attempt(self) -> None:
        job_id = self._new_ready_job(max_attempts=1)
        lease_token, worker_id, workspace = self._claim_and_start(
            job_id, "over-budget-owner"
        )
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                "UPDATE jobs SET attempt_count=2 WHERE job_id=?",
                (job_id,),
            )
        Validator(self.database).run(
            job_id,
            workspace,
            [{"type": "handler_evidence", "name": "pass", "passed": True}],
            self.root / "logs" / job_id / "attempt-2",
            attempt_number=2,
        )

        with self.assertRaisesRegex(JobError, "authorized attempt budget"):
            self.jobs.succeed(
                job_id,
                "over-budget-owner",
                lease_token,
                worker_id,
            )
        self.assertEqual("RUNNING", self.jobs.get(job_id)["state"])
        with self.database.connect() as connection:
            self.assertEqual(
                0,
                connection.execute(
                    "SELECT COUNT(*) AS n FROM artifacts WHERE job_id=?",
                    (job_id,),
                ).fetchone()["n"],
            )

    def test_retry_allowance_trigger_rejects_non_controller_grants(self) -> None:
        job_id = self._new_ready_job(max_attempts=1)
        claimed = self.jobs.claim_next(
            "allowance-owner", 30, max_total=1, type_limits={}
        )
        assert claimed is not None
        self.jobs.fail(
            job_id,
            "allowance-owner",
            claimed.lease_token,
            None,
            kind="deterministic",
            error="exhausted",
            retryable=False,
        )
        self.jobs.retry(job_id)
        self.assertEqual(1, self.jobs.get(job_id)["retry_allowance"])

        for label, value in (("jump", 3), ("decrement", 0), ("wrong-state", 2)):
            with self.subTest(label=label):
                with self.assertRaisesRegex(
                    sqlite3.IntegrityError,
                    "controller-authorized attempt",
                ):
                    with self.database.transaction(immediate=True) as connection:
                        connection.execute(
                            "UPDATE jobs SET retry_allowance=? WHERE job_id=?",
                            (value, job_id),
                        )
                self.assertEqual(1, self.jobs.get(job_id)["retry_allowance"])


class ClaimAndCapacityTests(DatabaseTestCase):
    def test_claim_by_id_unknown_target_never_falls_back_or_opens_writer(
        self,
    ) -> None:
        unrelated = self._new_ready_job(
            job_id="job_exact_unknown_fallback", priority=100
        )

        with mock.patch.object(
            self.database,
            "transaction",
            side_effect=AssertionError("unknown exact target opened a writer"),
        ):
            claimed = self.jobs.claim_by_id(
                "job_exact_missing",
                "unknown-exact-owner",
                30,
                max_total=1,
                type_limits={"test": 1},
            )

        self.assertIsNone(claimed)
        record = self.jobs.get(unrelated)
        self.assertEqual("READY", record["state"])
        self.assertEqual(0, record["attempt_count"])

    def test_claim_by_id_claims_only_requested_job_and_preserves_live_lease(
        self,
    ) -> None:
        target = self.jobs.create(
            "target", "test", {}, job_id="job_exact_target", priority=-10
        )
        unrelated = self.jobs.create(
            "unrelated", "test", {}, job_id="job_exact_higher", priority=100
        )
        self.jobs.promote_eligible()

        claimed = self.jobs.claim_by_id(
            target,
            "exact-owner",
            30,
            max_total=2,
            type_limits={"test": 2},
        )

        self.assertEqual(target, claimed.job_id if claimed else None)
        self.assertEqual("READY", self.jobs.get(unrelated)["state"])
        self.assertEqual(0, self.jobs.get(unrelated)["attempt_count"])
        first_record = self.jobs.get(target)
        self.assertEqual("CLAIMED", first_record["state"])
        self.assertIsNone(
            self.jobs.claim_by_id(
                target,
                "lease-stealing-owner",
                30,
                max_total=2,
                type_limits={"test": 2},
            )
        )
        second_record = self.jobs.get(target)
        self.assertEqual("exact-owner", second_record["owner"])
        self.assertEqual(first_record["lease_token"], second_record["lease_token"])
        self.assertEqual(1, second_record["attempt_count"])

    def test_claim_by_id_fenced_target_never_falls_back(self) -> None:
        target = self.jobs.create(
            "target",
            "test",
            {"validators": [{"type": "command", "argv": ["true"]}]},
            job_id="job_exact_fenced",
            priority=100,
        )
        unrelated = self.jobs.create(
            "unrelated", "test", {}, job_id="job_exact_safe", priority=1
        )
        self.jobs.promote_eligible()

        claimed = self.jobs.claim_by_id(
            target,
            "exact-fenced-owner",
            30,
            max_total=1,
            type_limits={"test": 1},
            blocked_validator_types=frozenset({"command"}),
        )

        self.assertIsNone(claimed)
        for job_id in (target, unrelated):
            record = self.jobs.get(job_id)
            self.assertEqual("READY", record["state"])
            self.assertEqual(0, record["attempt_count"])

    def test_claim_by_id_decodes_invalid_payload_before_writer(self) -> None:
        target = self._new_ready_job(job_id="job_exact_invalid_payload")
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                "UPDATE jobs SET payload_json=? WHERE job_id=?",
                ('{"duplicate":1,"duplicate":2}', target),
            )

        with mock.patch.object(
            self.database,
            "transaction",
            side_effect=AssertionError("invalid payload opened a writer"),
        ), self.assertRaisesRegex(JobError, "invalid or ambiguous payload JSON"):
            self.jobs.claim_by_id(
                target,
                "invalid-payload-owner",
                30,
                max_total=1,
                type_limits={"test": 1},
            )

        with self.database.connect() as connection:
            record = connection.execute(
                "SELECT state,attempt_count,owner FROM jobs WHERE job_id=?", (target,)
            ).fetchone()
        self.assertEqual("READY", record["state"])
        self.assertEqual(0, record["attempt_count"])
        self.assertIsNone(record["owner"])

    def test_claim_by_id_payload_preflight_releases_shared_lock(self) -> None:
        target = self._new_ready_job(job_id="job_exact_slow_payload")
        parsing_started = threading.Event()
        release_parser = threading.Event()
        outcomes: list[object] = []
        failures: list[BaseException] = []
        original_fence = jobs_module._held_by_validator_fence

        def slow_parse(raw: str, blocked: frozenset[str]) -> bool:
            parsing_started.set()
            if not release_parser.wait(timeout=5):
                raise AssertionError("test did not release exact payload parser")
            return original_fence(raw, blocked)

        def claim() -> None:
            try:
                outcomes.append(
                    self.jobs.claim_by_id(
                        target,
                        "slow-exact-owner",
                        30,
                        max_total=1,
                        type_limits={"test": 1},
                        blocked_validator_types=frozenset({"command"}),
                    )
                )
            except BaseException as error:
                failures.append(error)

        with mock.patch(
            "learnfactory.jobs._held_by_validator_fence", side_effect=slow_parse
        ):
            worker = threading.Thread(target=claim)
            worker.start()
            self.assertTrue(parsing_started.wait(timeout=5))
            contender = Database(
                self.database_path,
                self.migrations,
                busy_timeout_seconds=0.02,
            )
            try:
                with contender.transaction(immediate=True) as connection:
                    connection.execute(
                        """
                        INSERT INTO events(timestamp,actor,type,payload_json)
                        VALUES (?,?,?,?)
                        """,
                        (time.time(), "test", "WRITER_DURING_EXACT_PARSE", "{}"),
                    )
            finally:
                release_parser.set()
            worker.join(timeout=10)

        self.assertFalse(worker.is_alive())
        self.assertEqual([], failures)
        self.assertEqual(target, outcomes[0].job_id if outcomes[0] else None)

    def test_claim_by_id_ignores_unrelated_claim_generation_change(self) -> None:
        target = self._new_ready_job(job_id="job_exact_generation_target")
        unrelated = self._new_ready_job(
            job_id="job_exact_generation_unrelated", priority=1
        )
        original_select = self.jobs._select_claimable_by_id

        def select_then_change_unrelated(*args: object, **kwargs: object) -> object:
            selected = original_select(*args, **kwargs)  # type: ignore[arg-type]
            with self.database.transaction(immediate=True) as connection:
                connection.execute(
                    "UPDATE jobs SET priority=priority+1 WHERE job_id=?",
                    (unrelated,),
                )
            return selected

        with mock.patch.object(
            self.jobs,
            "_select_claimable_by_id",
            side_effect=select_then_change_unrelated,
        ):
            claimed = self.jobs.claim_by_id(
                target,
                "exact-generation-owner",
                30,
                max_total=1,
                type_limits={"test": 1},
            )

        self.assertEqual(target, claimed.job_id if claimed else None)
        self.assertEqual("READY", self.jobs.get(unrelated)["state"])

    def test_claim_by_id_rejects_target_payload_change_after_preflight(self) -> None:
        target = self._new_ready_job(job_id="job_exact_changed_payload")
        original_select = self.jobs._select_claimable_by_id
        changed_payload = '{"validators":[{"type":"command","argv":["true"]}]}'

        def select_then_change_target(*args: object, **kwargs: object) -> object:
            selected = original_select(*args, **kwargs)  # type: ignore[arg-type]
            with self.database.transaction(immediate=True) as connection:
                connection.execute(
                    "UPDATE jobs SET payload_json=? WHERE job_id=?",
                    (changed_payload, target),
                )
            return selected

        with mock.patch.object(
            self.jobs,
            "_select_claimable_by_id",
            side_effect=select_then_change_target,
        ):
            claimed = self.jobs.claim_by_id(
                target,
                "changed-payload-owner",
                30,
                max_total=1,
                type_limits={"test": 1},
                blocked_validator_types=frozenset({"command"}),
            )

        self.assertIsNone(claimed)
        record = self.jobs.get(target)
        self.assertEqual("READY", record["state"])
        self.assertEqual(0, record["attempt_count"])
        self.assertIsNone(
            self.jobs.claim_by_id(
                target,
                "changed-payload-retry",
                30,
                max_total=1,
                type_limits={"test": 1},
                blocked_validator_types=frozenset({"command"}),
            )
        )

    def test_claim_by_id_rechecks_pause_and_type_capacity_in_writer(self) -> None:
        target = self._new_ready_job(job_id="job_exact_writer_fences")
        original_select = self.jobs._select_claimable_by_id

        def select_then_pause(*args: object, **kwargs: object) -> object:
            selected = original_select(*args, **kwargs)  # type: ignore[arg-type]
            self.database.set_system_value("paused", True)
            return selected

        with mock.patch.object(
            self.jobs,
            "_select_claimable_by_id",
            side_effect=select_then_pause,
        ):
            self.assertIsNone(
                self.jobs.claim_by_id(
                    target,
                    "paused-exact-owner",
                    30,
                    max_total=1,
                    type_limits={"test": 1},
                )
            )
        self.assertEqual(0, self.jobs.get(target)["attempt_count"])
        self.database.set_system_value("paused", False)

        capacity = self._new_ready_job(job_id="job_exact_capacity_consumer")

        def select_then_fill_type(*args: object, **kwargs: object) -> object:
            selected = original_select(*args, **kwargs)  # type: ignore[arg-type]
            timestamp = time.time()
            with self.database.transaction(immediate=True) as connection:
                connection.execute(
                    """
                    UPDATE jobs SET state='CLAIMED',owner='capacity-owner',
                        lease_token='lease_exact_capacity',lease_expires_at=?,
                        heartbeat_at=?,attempt_count=attempt_count+1
                    WHERE job_id=?
                    """,
                    (timestamp + 30, timestamp, capacity),
                )
            return selected

        with mock.patch.object(
            self.jobs,
            "_select_claimable_by_id",
            side_effect=select_then_fill_type,
        ):
            self.assertIsNone(
                self.jobs.claim_by_id(
                    target,
                    "saturated-exact-owner",
                    30,
                    max_total=2,
                    type_limits={"test": 1},
                )
            )
        self.assertEqual(0, self.jobs.get(target)["attempt_count"])

    def test_claim_by_id_rejects_unsatisfied_dependency_without_fallback(
        self,
    ) -> None:
        parent = self.jobs.create(
            "parent", "test", {}, job_id="job_exact_pending_parent"
        )
        child = self.jobs.create(
            "child",
            "test",
            {},
            dependencies=[parent],
            job_id="job_exact_dependency_child",
            priority=100,
        )
        unrelated = self._new_ready_job(
            job_id="job_exact_dependency_unrelated", priority=1
        )
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                "UPDATE jobs SET state='READY' WHERE job_id=?", (child,)
            )

        claimed = self.jobs.claim_by_id(
            child,
            "dependency-exact-owner",
            30,
            max_total=1,
            type_limits={"test": 1},
        )

        self.assertIsNone(claimed)
        self.assertEqual("READY", self.jobs.get(child)["state"])
        self.assertEqual(0, self.jobs.get(child)["attempt_count"])
        self.assertEqual("READY", self.jobs.get(unrelated)["state"])

    def test_concurrent_claim_by_id_grants_one_lease(self) -> None:
        target = self._new_ready_job(job_id="job_exact_atomic")
        contenders = 4
        barrier = threading.Barrier(contenders)

        def claim(index: int) -> str | None:
            repository = JobRepository(Database(self.database_path, self.migrations))
            barrier.wait(timeout=10)
            result = repository.claim_by_id(
                target,
                f"exact-thread-owner-{index}",
                30,
                max_total=contenders,
                type_limits={"test": contenders},
            )
            return result.job_id if result is not None else None

        with ThreadPoolExecutor(max_workers=contenders) as executor:
            results = list(executor.map(claim, range(contenders)))

        self.assertEqual([target], [result for result in results if result is not None])
        record = self.jobs.get(target)
        self.assertEqual("CLAIMED", record["state"])
        self.assertEqual(1, record["attempt_count"])

    def test_effective_attempt_budget_survives_restart_and_fences_claims(self) -> None:
        job_id = self.jobs.create(
            "retry-budget",
            "test",
            {
                "validators": [
                    {"type": "command", "name": "held", "argv": ["true"]}
                ]
            },
            max_attempts=1,
        )
        self.jobs.promote_eligible()
        first = self.jobs.claim_next(
            "retry-owner-1", 1, max_total=1, type_limits={}
        )
        assert first is not None
        first_row = self.jobs.get(job_id)
        assert first_row is not None
        self.assertEqual(
            1, self.jobs.recover_expired(first_row["lease_expires_at"] + 0.001)
        )
        self.assertEqual("FAILED", self.jobs.get(job_id)["state"])

        self.jobs.retry(job_id)
        ready = self.jobs.get(job_id)
        assert ready is not None
        self.assertEqual(1, ready["max_attempts"])
        self.assertEqual(1, ready["retry_allowance"])
        self.assertEqual(1, self.jobs.count_ready_held_by_validator_fence(frozenset({"command"})))
        self.assertEqual(0, self.jobs.count_ready_claimable(frozenset({"command"})))
        self.assertEqual(1, self.jobs.count_ready_claimable(frozenset()))

        restarted = JobRepository(Database(self.database_path, self.migrations))
        second = restarted.claim_next(
            "retry-owner-2", 1, max_total=1, type_limits={}
        )
        assert second is not None
        self.assertEqual(2, second.attempt_count)
        self.assertIsNone(
            self.jobs.claim_next(
                "stale-contender", 1, max_total=2, type_limits={}
            )
        )
        second_row = restarted.get(job_id)
        assert second_row is not None
        self.assertEqual(
            1,
            restarted.recover_expired(
                second_row["lease_expires_at"] + 0.001
            ),
        )
        self.assertEqual("FAILED", restarted.get(job_id)["state"])

        restarted.retry(job_id)
        third_ready = restarted.get(job_id)
        assert third_ready is not None
        self.assertEqual(1, third_ready["max_attempts"])
        self.assertEqual(2, third_ready["retry_allowance"])
        third = restarted.claim_next(
            "retry-owner-3", 1, max_total=1, type_limits={}
        )
        assert third is not None
        self.assertEqual(3, third.attempt_count)
        with self.database.connect() as connection:
            retry_events = [
                json.loads(row["payload_json"])
                for row in connection.execute(
                    """
                    SELECT payload_json FROM events
                    WHERE job_id=? AND type='JOB_MANUALLY_RETRIED'
                    ORDER BY event_id
                    """,
                    (job_id,),
                )
            ]
        self.assertEqual([2, 3], [item["effective_attempt_limit"] for item in retry_events])

    def test_payload_parsing_between_pages_does_not_hold_a_shared_lock(self) -> None:
        payload = json.dumps(
            {"validators": [{"type": "command", "argv": ["true"]}]},
            separators=(",", ":"),
        )
        with self.database.transaction(immediate=True) as connection:
            connection.executemany(
                """
                INSERT INTO jobs(
                    job_id,type,worker_type,state,priority,payload_json,created_at
                ) VALUES (?,?,?,'READY',?,?,?)
                """,
                [
                    (
                        f"job_slow_fenced_{index:04d}",
                        "fenced",
                        "test",
                        3000 - index,
                        payload,
                        float(index),
                    )
                    for index in range(3000)
                ],
            )
        parsing_started = threading.Event()
        release_parser = threading.Event()
        failures: list[BaseException] = []
        original_fence = jobs_module._held_by_validator_fence

        def slow_first_parse(raw: str, blocked: frozenset[str]) -> bool:
            if not parsing_started.is_set():
                parsing_started.set()
                if not release_parser.wait(timeout=5):
                    raise AssertionError("test did not release payload parser")
            return original_fence(raw, blocked)

        def scan() -> None:
            try:
                self.assertIsNone(
                    self.jobs.claim_next(
                        "slow-parser",
                        30,
                        max_total=2,
                        type_limits={"test": 2},
                        blocked_validator_types=frozenset({"command"}),
                    )
                )
            except BaseException as error:
                failures.append(error)

        with mock.patch(
            "learnfactory.jobs._held_by_validator_fence",
            side_effect=slow_first_parse,
        ):
            worker = threading.Thread(target=scan)
            worker.start()
            self.assertTrue(parsing_started.wait(timeout=5))
            contender = Database(
                self.database_path,
                self.migrations,
                busy_timeout_seconds=0.02,
            )
            try:
                with contender.transaction(immediate=True) as connection:
                    connection.execute(
                        """
                        INSERT INTO events(timestamp,actor,type,payload_json)
                        VALUES (?,?,?,?)
                        """,
                        (time.time(), "test", "WRITER_DURING_PARSE", "{}"),
                    )
            finally:
                release_parser.set()
            worker.join(timeout=10)

        self.assertFalse(worker.is_alive())
        self.assertEqual([], failures)

    def test_projection_generation_rejects_every_interposed_claim_change(self) -> None:
        def insert_higher(
            repository: JobRepository, _database: Database, _selected: str
        ) -> None:
            repository.create(
                "test_job", "test", {}, job_id="job_interposed_high", priority=99
            )
            repository.promote_eligible()

        def update_priority(
            _repository: JobRepository, database: Database, _selected: str
        ) -> None:
            with database.transaction(immediate=True) as connection:
                connection.execute(
                    "UPDATE jobs SET priority=100 WHERE job_id='job_interposed_other'"
                )

        def delete_selected(
            _repository: JobRepository, database: Database, selected: str
        ) -> None:
            with database.transaction(immediate=True) as connection:
                connection.execute("DELETE FROM events WHERE job_id=?", (selected,))
                connection.execute("DELETE FROM jobs WHERE job_id=?", (selected,))

        def change_state(
            _repository: JobRepository, database: Database, _selected: str
        ) -> None:
            with database.transaction(immediate=True) as connection:
                connection.execute(
                    "UPDATE jobs SET state='CANCELLED' "
                    "WHERE job_id='job_interposed_other'"
                )

        def change_payload(
            _repository: JobRepository, database: Database, selected: str
        ) -> None:
            with database.transaction(immediate=True) as connection:
                connection.execute(
                    "UPDATE jobs SET payload_json=? WHERE job_id=?",
                    (
                        '{"validators":[{"type":"command","argv":["true"]}]}',
                        selected,
                    ),
                )

        def consume_capacity(
            _repository: JobRepository, database: Database, _selected: str
        ) -> None:
            with database.transaction(immediate=True) as connection:
                connection.execute(
                    """
                    UPDATE jobs SET state='CLAIMED',owner='other-owner',
                        lease_token='lease_interposed_capacity',
                        lease_expires_at=?,heartbeat_at=?,attempt_count=1
                    WHERE job_id='job_interposed_other'
                    """,
                    (time.time() + 30, time.time()),
                )

        mutations = {
            "insert": insert_higher,
            "priority": update_priority,
            "delete": delete_selected,
            "state": change_state,
            "payload": change_payload,
            "capacity": consume_capacity,
        }
        for name, mutation in mutations.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory(
                prefix=f"learnfactory-generation-{name}-"
            ) as raw:
                database = Database(Path(raw) / "factory.db", self.migrations)
                database.migrate()
                repository = JobRepository(database)
                selected = repository.create(
                    "test_job", "test", {}, job_id="job_interposed_selected", priority=2
                )
                repository.create(
                    "test_job", "test", {}, job_id="job_interposed_other", priority=1
                )
                repository.promote_eligible()
                original_select = repository._select_claimable_candidate
                interposed = False

                def select_then_mutate(**kwargs: object) -> object:
                    nonlocal interposed
                    candidate = original_select(**kwargs)  # type: ignore[arg-type]
                    if candidate is not None and not interposed:
                        interposed = True
                        mutation(repository, database, selected)
                    return candidate

                with mock.patch.object(
                    repository,
                    "_select_claimable_candidate",
                    side_effect=select_then_mutate,
                ):
                    claimed = repository.claim_next(
                        "generation-owner",
                        30,
                        max_total=1,
                        type_limits={"test": 1},
                        blocked_validator_types=frozenset({"command"}),
                    )

                self.assertTrue(interposed)
                self.assertIsNone(claimed)
                record = repository.get(selected)
                if name != "delete":
                    assert record is not None
                    self.assertEqual(0, record["attempt_count"])

    def test_postselection_cancelled_dependency_insertion_is_rejected(
        self,
    ) -> None:
        cancelled_parent = self.jobs.create(
            "parent", "test", {}, job_id="job_interposed_cancelled_parent"
        )
        selected = self.jobs.create(
            "child",
            "test",
            {},
            job_id="job_interposed_dependency_child",
            priority=100,
        )
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                "UPDATE jobs SET state='CANCELLED' WHERE job_id=?",
                (cancelled_parent,),
            )
        self.jobs.promote_eligible()
        original_select = self.jobs._select_claimable_candidate
        attack_attempted = False

        def select_then_attack(**kwargs: object) -> object:
            nonlocal attack_attempted
            candidate = original_select(**kwargs)  # type: ignore[arg-type]
            if candidate is not None and not attack_attempted:
                attack_attempted = True
                with self.assertRaisesRegex(
                    sqlite3.IntegrityError,
                    "dependencies may only be added to DISCOVERED jobs",
                ):
                    with self.database.transaction(immediate=True) as connection:
                        connection.execute(
                            """
                            INSERT INTO job_dependencies(job_id,depends_on_job_id)
                            VALUES (?,?)
                            """,
                            (selected, cancelled_parent),
                        )
            return candidate

        with mock.patch.object(
            self.jobs,
            "_select_claimable_candidate",
            side_effect=select_then_attack,
        ):
            claimed = self.jobs.claim_next(
                "dependency-attack-owner",
                30,
                max_total=1,
                type_limits={},
            )

        self.assertTrue(attack_attempted)
        self.assertEqual(selected, claimed.job_id if claimed else None)
        with self.database.connect() as connection:
            edge_count = connection.execute(
                "SELECT COUNT(*) FROM job_dependencies WHERE job_id=?",
                (selected,),
            ).fetchone()[0]
        self.assertEqual(0, edge_count)

    def test_interposed_prerequisite_state_change_invalidates_selection(self) -> None:
        timestamp = time.time()
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                """
                INSERT INTO jobs(
                    job_id,type,worker_type,state,payload_json,created_at
                ) VALUES ('job_racing_prerequisite','test','test','SUCCEEDED','{}',?)
                """,
                (timestamp,),
            )
        child = self.jobs.create(
            "child",
            "test",
            {},
            dependencies=["job_racing_prerequisite"],
            job_id="job_racing_dependency_child",
        )
        self.jobs.promote_eligible()
        original_select = self.jobs._select_claimable_candidate
        mutation_finished = False

        def select_then_replace_parent(**kwargs: object) -> object:
            nonlocal mutation_finished
            candidate = original_select(**kwargs)  # type: ignore[arg-type]
            if candidate is not None and not mutation_finished:
                # Simulate an independently corrupted/legacy writer. Supported
                # writers cannot leave SUCCEEDED, but the claim fence still
                # rejects the changed prerequisite rather than trusting that.
                connection = sqlite3.connect(
                    self.database_path,
                    isolation_level=None,
                    timeout=5,
                )
                try:
                    connection.execute("PRAGMA foreign_keys=OFF")
                    connection.execute("BEGIN IMMEDIATE")
                    connection.execute(
                        "DELETE FROM jobs WHERE job_id='job_racing_prerequisite'"
                    )
                    connection.execute(
                        """
                        INSERT INTO jobs(
                            job_id,type,worker_type,state,payload_json,created_at
                        ) VALUES (
                            'job_racing_prerequisite','test','test',
                            'CANCELLED','{}',?
                        )
                        """,
                        (time.time(),),
                    )
                    connection.commit()
                finally:
                    connection.close()
                mutation_finished = True
            return candidate

        with mock.patch.object(
            self.jobs,
            "_select_claimable_candidate",
            side_effect=select_then_replace_parent,
        ):
            claimed = self.jobs.claim_next(
                "dependency-race-owner",
                30,
                max_total=1,
                type_limits={},
            )

        self.assertTrue(mutation_finished)
        self.assertIsNone(claimed)
        record = self.jobs.get(child)
        self.assertEqual(JobState.READY.value, record["state"])
        self.assertEqual(0, record["attempt_count"])

    def test_all_validator_fenced_candidates_never_open_a_write_transaction(
        self,
    ) -> None:
        for index in range(130):
            self.jobs.create(
                "fenced",
                "test",
                {"validators": [{"type": "command", "argv": ["true"]}]},
                job_id=f"job_fenced_{index:03d}",
            )
        self.jobs.promote_eligible()

        with mock.patch.object(
            self.database,
            "transaction",
            side_effect=AssertionError("fenced queue acquired writer"),
        ):
            claimed = self.jobs.claim_next(
                "fenced-owner",
                30,
                max_total=2,
                type_limits={"test": 2},
                blocked_validator_types=frozenset({"command"}),
            )

        self.assertIsNone(claimed)
        contender = JobRepository(
            Database(
                self.database_path,
                self.migrations,
                busy_timeout_seconds=0.01,
            )
        )
        with self.database.transaction(immediate=True):
            self.assertIsNone(
                contender.claim_next(
                    "fenced-contender",
                    30,
                    max_total=2,
                    type_limits={"test": 2},
                    blocked_validator_types=frozenset({"command"}),
                )
            )

    def test_equal_priority_cursor_reaches_eligible_job_beyond_two_pages(self) -> None:
        for index in range(130):
            self.jobs.create(
                "fenced",
                "test",
                {"validators": [{"type": "command", "argv": ["true"]}]},
                job_id=f"job_equal_priority_{index:03d}",
                priority=1,
            )
        target = self.jobs.create(
            "eligible",
            "test",
            {},
            job_id="job_equal_priority_zzz",
            priority=1,
        )
        self.jobs.promote_eligible()

        claimed = self.jobs.claim_next(
            "equal-priority-owner",
            30,
            max_total=1,
            type_limits={"test": 1},
            blocked_validator_types=frozenset({"command"}),
        )

        self.assertEqual(target, claimed.job_id if claimed else None)

    def test_all_saturated_candidates_never_open_a_write_transaction(self) -> None:
        active = self._new_ready_job(
            worker_type="ingestion", job_id="job_saturated_active"
        )
        claimed = self.jobs.claim_next(
            "active-owner",
            30,
            max_total=2,
            type_limits={"ingestion": 1},
        )
        self.assertEqual(active, claimed.job_id if claimed else None)
        waiting = self._new_ready_job(
            worker_type="ingestion", job_id="job_saturated_waiting"
        )

        with mock.patch.object(
            self.database,
            "transaction",
            side_effect=AssertionError("saturated queue acquired writer"),
        ):
            next_claim = self.jobs.claim_next(
                "waiting-owner",
                30,
                max_total=2,
                type_limits={"ingestion": 1},
            )

        self.assertIsNone(next_claim)
        self.assertEqual("READY", self.jobs.get(waiting)["state"])
        contender = JobRepository(
            Database(
                self.database_path,
                self.migrations,
                busy_timeout_seconds=0.01,
            )
        )
        with self.database.transaction(immediate=True):
            self.assertIsNone(
                contender.claim_next(
                    "saturated-contender",
                    30,
                    max_total=2,
                    type_limits={"ingestion": 1},
                )
            )

    def test_pause_committed_before_claim_leaves_job_completely_unowned(self) -> None:
        job_id = self._new_ready_job(job_id="job_pause_first")
        self.database.set_system_value("paused", True)

        claimed = self.jobs.claim_next(
            "paused-owner", 30, max_total=1, type_limits={}
        )

        self.assertIsNone(claimed)
        record = self.jobs.get(job_id)
        self.assertEqual("READY", record["state"])
        self.assertEqual(0, record["attempt_count"])
        self.assertIsNone(record["owner"])
        self.assertIsNone(record["lease_token"])
        with self.database.connect() as connection:
            claims = connection.execute(
                "SELECT COUNT(*) FROM events WHERE job_id=? AND type='JOB_CLAIMED'",
                (job_id,),
            ).fetchone()[0]
        self.assertEqual(0, claims)

    def test_pause_transaction_linearizes_before_waiting_claim(self) -> None:
        job_id = self._new_ready_job(job_id="job_pause_race")
        transaction_attempted = threading.Event()

        class SignallingDatabase(Database):
            @contextlib.contextmanager
            def transaction(self, *, immediate: bool = False):  # type: ignore[no-untyped-def]
                transaction_attempted.set()
                with super().transaction(immediate=immediate) as connection:
                    yield connection

        contender = JobRepository(
            SignallingDatabase(self.database_path, self.migrations)
        )
        outcome: list[object] = []

        def claim() -> None:
            outcome.append(
                contender.claim_next(
                    "race-owner", 30, max_total=1, type_limits={}
                )
            )

        with self.database.transaction(immediate=True) as connection:
            self.database.set_system_value(
                "paused", True, connection=connection
            )
            worker = threading.Thread(target=claim)
            worker.start()
            self.assertTrue(transaction_attempted.wait(timeout=2))
        worker.join(timeout=5)
        self.assertFalse(worker.is_alive())
        self.assertEqual([None], outcome)
        self.assertEqual(0, self.jobs.get(job_id)["attempt_count"])

        self.database.set_system_value("paused", False)
        resumed = self.jobs.claim_next(
            "resumed-owner", 30, max_total=1, type_limits={}
        )
        self.assertEqual(job_id, resumed.job_id if resumed else None)

    def test_scheduler_queries_use_covering_and_ordered_indexes(self) -> None:
        with self.database.connect() as connection:
            promotion = " ".join(
                str(row["detail"])
                for row in connection.execute(
                    """
                    EXPLAIN QUERY PLAN
                    SELECT job_id FROM jobs WHERE state='DISCOVERED'
                    """
                )
            )
            claim = " ".join(
                str(row["detail"])
                for row in connection.execute(
                    """
                    EXPLAIN QUERY PLAN
                    SELECT job_id,worker_type,payload_json,
                           claim_priority_key AS priority_key,created_at
                    FROM jobs candidate
                    WHERE candidate.state='READY'
                      AND candidate.cancel_requested=0
                      AND candidate.attempt_count
                          < candidate.max_attempts + candidate.retry_allowance
                      AND NOT EXISTS (
                        SELECT 1
                        FROM job_dependencies dependency
                        LEFT JOIN jobs prerequisite
                          ON prerequisite.job_id=dependency.depends_on_job_id
                        WHERE dependency.job_id=candidate.job_id
                          AND (
                            prerequisite.job_id IS NULL
                            OR prerequisite.state <> 'SUCCEEDED'
                          )
                      )
                      AND (claim_priority_key,created_at,job_id) > (?,?,?)
                    ORDER BY claim_priority_key,created_at,job_id
                    LIMIT ?
                    """,
                    (-1000.0, 0.0, "job_cursor", 64),
                )
            )
        self.assertIn("COVERING INDEX", promotion)
        self.assertTrue(
            "idx_jobs_state_job_id" in promotion
            or "idx_jobs_claim_order" in promotion
            or "idx_jobs_claim_cursor" in promotion
        )
        self.assertIn("INDEX idx_jobs_claim_cursor", claim)
        self.assertNotIn("TEMP B-TREE", claim)

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
    def _prepared_artifact(self, job_id: str, attempt: int) -> PreparedArtifact:
        path = self.root / "prepared" / job_id
        path.mkdir(parents=True)
        (path / "result.txt").write_text("validated\n", encoding="utf-8")
        return PreparedArtifact(
            artifact_id=f"artifact_{job_id}",
            path=path,
            checksum=tree_sha256(path),
            checksum_algorithm="tree-sha256-v2",
            attempt=attempt,
            artifact_type="test",
            metadata={"job_id": job_id},
            validation_status="TESTED",
            validation_labels=("GENERATED",),
            created_at=time.time(),
        )

    def _assert_publication_handles_revoked(
        self,
        publication: object,
        cursor: object,
        iterator: object,
        *,
        marker: str,
    ) -> None:
        operations = (
            ("connection-in-transaction", lambda: publication.in_transaction),  # type: ignore[attr-defined]
            ("connection-cursor", lambda: publication.cursor()),  # type: ignore[attr-defined]
            (
                "connection-execute",
                lambda: publication.execute(  # type: ignore[attr-defined]
                    """
                    INSERT INTO system_state(key,value_json,updated_at)
                    VALUES (?,'true',1)
                    """,
                    (f"{marker}-connection",),
                ),
            ),
            (
                "connection-executemany",
                lambda: publication.executemany(  # type: ignore[attr-defined]
                    """
                    INSERT INTO system_state(key,value_json,updated_at)
                    VALUES (?,'true',1)
                    """,
                    [(f"{marker}-connection-many",)],
                ),
            ),
            ("connection-denied-method", lambda: publication.commit()),  # type: ignore[attr-defined]
            ("cursor-connection", lambda: cursor.connection),  # type: ignore[attr-defined]
            ("cursor-rowcount", lambda: cursor.rowcount),  # type: ignore[attr-defined]
            ("cursor-lastrowid", lambda: cursor.lastrowid),  # type: ignore[attr-defined]
            ("cursor-description", lambda: cursor.description),  # type: ignore[attr-defined]
            (
                "cursor-execute",
                lambda: cursor.execute(  # type: ignore[attr-defined]
                    """
                    INSERT INTO students(
                        student_id,persona,profile_json,created_at
                    ) VALUES (?,'test','{}',1)
                    """,
                    (f"{marker}-cursor",),
                ),
            ),
            (
                "cursor-executemany",
                lambda: cursor.executemany(  # type: ignore[attr-defined]
                    "UPDATE sources SET name=? WHERE source_id=?",
                    [("forged", "missing")],
                ),
            ),
            ("cursor-fetchone", lambda: cursor.fetchone()),  # type: ignore[attr-defined]
            ("cursor-fetchmany", lambda: cursor.fetchmany()),  # type: ignore[attr-defined]
            ("cursor-fetchall", lambda: cursor.fetchall()),  # type: ignore[attr-defined]
            ("cursor-iter", lambda: iter(cursor)),
            ("cursor-denied-method", lambda: cursor.close()),  # type: ignore[attr-defined]
            ("iterator-connection", lambda: iterator.connection),  # type: ignore[attr-defined]
            ("iterator-iter", lambda: iter(iterator)),
            ("iterator-next", lambda: next(iterator)),  # type: ignore[arg-type]
        )
        for operation_name, operation in operations:
            with self.subTest(operation=operation_name), self.assertRaisesRegex(
                PublicationAccessError,
                "publication capability is no longer active",
            ):
                operation()

    def _assert_revocation_markers_absent(self, marker: str) -> None:
        with self.database.connect() as connection:
            self.assertEqual(
                0,
                connection.execute(
                    "SELECT COUNT(*) FROM system_state WHERE key LIKE ?",
                    (f"{marker}%",),
                ).fetchone()[0],
            )
            self.assertEqual(
                0,
                connection.execute(
                    "SELECT COUNT(*) FROM students WHERE student_id LIKE ?",
                    (f"{marker}%",),
                ).fetchone()[0],
            )

    def test_publication_authorizer_enforces_policy_and_reauthorizes_cache(
        self,
    ) -> None:
        with self.database.transaction(immediate=True) as connection:
            # Prewarm this exact SQL before the privilege boundary. Without
            # cached_statements=0, Python can reuse it without authorizing it.
            statement = "SELECT COUNT(*) FROM system_state"
            self.assertGreaterEqual(connection.execute(statement).fetchone()[0], 1)
            with self.assertRaisesRegex(
                PublicationAccessError, "suppressed a denied operation"
            ):
                with restricted_publication_connection(
                    connection, PublicationScope.SOURCE_INGESTION
                ) as publication:
                    publication.execute("SELECT COUNT(*) FROM sources").fetchone()
                    with self.assertRaisesRegex(
                        PublicationAccessError, "system_state"
                    ):
                        publication.execute(statement).fetchone()

            self.assertIsNone(connection.learnfactory_authorizer)
            self.assertGreaterEqual(connection.execute(statement).fetchone()[0], 1)

    def test_source_publication_baseline_fk_access_is_strictly_read_only(
        self,
    ) -> None:
        existing_source = "source_baseline_fk_existing"
        baseline = "a" * 64
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                """
                INSERT INTO sources(
                    source_id,type,name,path,commit_hash,ingested_at
                ) VALUES (?,?,?,?,?,?)
                """,
                (existing_source, "test", "existing", "/existing", "a", 1),
            )
            connection.execute(
                """
                INSERT INTO byox_baseline_snapshots(
                    baseline_sha256,schema_version,project_id,source_id,
                    source_commit_hash,extractor_version,material_json,
                    first_observed_at
                ) VALUES (?,1,?,?,?,?,?,?)
                """,
                (
                    baseline,
                    "project_baseline_fk_existing",
                    existing_source,
                    "commit-a",
                    "test-v1",
                    "{}",
                    1,
                ),
            )

        with self.database.transaction(immediate=True) as connection:
            with restricted_publication_connection(
                connection, PublicationScope.SOURCE_INGESTION
            ) as publication:
                publication.execute(
                    """
                    INSERT INTO sources(
                        source_id,type,name,path,commit_hash,ingested_at
                    ) VALUES (?,?,?,?,?,?)
                    """,
                    (
                        "source_baseline_fk_new",
                        "test",
                        "new",
                        "/new",
                        "b",
                        2,
                    ),
                )

        mutations = (
            (
                "insert",
                """
                INSERT INTO byox_baseline_snapshots(
                    baseline_sha256,schema_version,project_id,source_id,
                    source_commit_hash,extractor_version,material_json,
                    first_observed_at
                ) VALUES (?,1,?,?,?,?,?,?)
                """,
                (
                    "b" * 64,
                    "project_baseline_fk_forged",
                    existing_source,
                    "commit-b",
                    "test-v1",
                    "{}",
                    2,
                ),
            ),
            (
                "update",
                "UPDATE byox_baseline_snapshots SET project_id=? "
                "WHERE baseline_sha256=?",
                ("project_baseline_fk_forged", baseline),
            ),
            (
                "delete",
                "DELETE FROM byox_baseline_snapshots WHERE baseline_sha256=?",
                (baseline,),
            ),
        )
        for label, statement, parameters in mutations:
            with self.subTest(operation=label), self.assertRaisesRegex(
                PublicationAccessError,
                "byox_baseline_snapshots",
            ):
                with self.database.transaction(immediate=True) as connection:
                    with restricted_publication_connection(
                        connection, PublicationScope.SOURCE_INGESTION
                    ) as publication:
                        publication.execute(statement, parameters)

    def test_publication_public_result_graph_has_no_raw_sqlite_handles(
        self,
    ) -> None:
        def assert_public_graph_is_restricted(*roots: object) -> None:
            pending = list(roots)
            visited: set[int] = set()
            while pending:
                value = pending.pop()
                identity = id(value)
                if identity in visited:
                    continue
                visited.add(identity)
                self.assertNotIsInstance(value, sqlite3.Connection)
                self.assertNotIsInstance(value, sqlite3.Cursor)
                if isinstance(value, sqlite3.Row):
                    pending.extend(value)
                elif isinstance(value, dict):
                    pending.extend(value.keys())
                    pending.extend(value.values())
                elif isinstance(value, (list, tuple, set, frozenset)):
                    pending.extend(value)
                for attribute in dir(value):
                    if attribute.startswith("_"):
                        continue
                    try:
                        child = getattr(value, attribute)
                    except (AttributeError, sqlite3.Error):
                        continue
                    if not callable(child):
                        pending.append(child)

        with self.database.transaction(immediate=True) as connection:
            with restricted_publication_connection(
                connection, PublicationScope.SOURCE_INGESTION
            ) as publication:
                inserted = publication.executemany(
                    """
                    INSERT INTO sources(
                        source_id,type,name,path,commit_hash,ingested_at
                    ) VALUES (?,?,?,?,?,?)
                    """,
                    [
                        ("source_public_graph_a", "test", "a", "/a", "a", 1),
                        ("source_public_graph_b", "test", "b", "/b", "b", 2),
                    ],
                )
                selected = publication.cursor()
                self.assertIs(
                    selected.execute(
                        """
                        SELECT source_id,name FROM sources
                        WHERE source_id LIKE 'source_public_graph_%'
                        ORDER BY source_id
                        """
                    ),
                    selected,
                )
                first = selected.fetchone()
                remainder = selected.fetchmany()
                empty = selected.fetchall()
                iterated_cursor = publication.execute(
                    """
                    SELECT source_id FROM sources
                    WHERE source_id LIKE 'source_public_graph_%'
                    ORDER BY source_id
                    """
                )
                iterator = iter(iterated_cursor)
                # This exact expression returned sqlite3.Cursor.connection in
                # the historical escape. It must resolve only to the facade.
                self.assertIs(
                    iter(publication.execute("SELECT source_id FROM sources")).connection,
                    publication,
                )
                self.assertIs(iterator.connection, publication)
                self.assertIs(iter(iterator), iterator)
                iterated_rows = list(iterator)
                self.assertEqual(
                    ["source_public_graph_a", "source_public_graph_b"],
                    [str(row["source_id"]) for row in iterated_rows],
                )
                updated = publication.cursor().executemany(
                    "UPDATE sources SET name=? WHERE source_id=?",
                    [
                        ("a2", "source_public_graph_a"),
                        ("b2", "source_public_graph_b"),
                    ],
                )
                assert_public_graph_is_restricted(
                    publication,
                    inserted,
                    selected,
                    selected.connection,
                    selected.description,
                    selected.rowcount,
                    selected.lastrowid,
                    first,
                    remainder,
                    empty,
                    iterated_cursor,
                    iterator,
                    iterator.connection,
                    iterated_rows,
                    updated,
                )

    def test_publication_handles_are_revoked_after_normal_exit(self) -> None:
        marker = "revoked-normal"
        with self.database.transaction(immediate=True) as connection:
            with restricted_publication_connection(
                connection, PublicationScope.SOURCE_INGESTION
            ) as publication:
                cursor = publication.execute(
                    "SELECT source_id FROM sources ORDER BY source_id"
                )
                iterator = iter(cursor)

            self._assert_publication_handles_revoked(
                publication,
                cursor,
                iterator,
                marker=marker,
            )

        self._assert_revocation_markers_absent(marker)

    def test_publication_handles_are_revoked_after_exceptional_exit(self) -> None:
        marker = "revoked-exception"
        with self.database.transaction(immediate=True) as connection:
            with self.assertRaisesRegex(RuntimeError, "synthetic callback failure"):
                with restricted_publication_connection(
                    connection, PublicationScope.SOURCE_INGESTION
                ) as publication:
                    cursor = publication.execute(
                        "SELECT source_id FROM sources ORDER BY source_id"
                    )
                    iterator = iter(cursor)
                    raise RuntimeError("synthetic callback failure")

            self._assert_publication_handles_revoked(
                publication,
                cursor,
                iterator,
                marker=marker,
            )

        self._assert_revocation_markers_absent(marker)

    def test_threaded_publication_revocation_has_no_check_use_window(
        self,
    ) -> None:
        job_id = self._new_ready_job(job_id="job_publication_revocation_race")
        owner = "publication-revocation-owner"
        lease_token, worker_id, workspace = self._claim_and_start(job_id, owner)
        results = Validator(self.database).run(
            job_id,
            workspace,
            [{"type": "handler_evidence", "name": "pass", "passed": True}],
            self.root / "logs" / job_id,
        )
        self.assertEqual(["PASS"], [result.status for result in results])
        artifact = self._prepared_artifact(job_id, 1)

        operation_entered = threading.Event()
        release_operation = threading.Event()
        revoke_attempted = threading.Event()
        authorizer_restored = threading.Event()
        attack_done = threading.Event()
        thread_errors: list[str] = []
        rejected_operations: list[str] = []
        restoration_before_release: list[bool] = []
        threads: list[threading.Thread] = []

        class BlockingParameters:
            def __init__(self) -> None:
                self.sent = False

            def __iter__(self) -> BlockingParameters:
                return self

            def __next__(self) -> tuple[object, ...]:
                if self.sent:
                    raise StopIteration
                self.sent = True
                operation_entered.set()
                if not release_operation.wait(timeout=5):
                    raise RuntimeError("publication operation release timed out")
                return (
                    "source_inflight_publication_race",
                    "test",
                    "in-flight operation",
                    "/in-flight",
                    "in-flight",
                    time.time(),
                )

        original_revoke = publication_module._PublicationPolicy.revoke_and_restore
        original_end_authorizer_guard = ClosingConnection._end_authorizer_guard
        original_assert_snapshot = (
            JobRepository._assert_dependency_publication_snapshot
        )

        def observed_revoke(
            policy: object,
            connection: ClosingConnection,
        ) -> None:
            revoke_attempted.set()
            original_revoke(policy, connection)  # type: ignore[arg-type]

        def observed_end_authorizer_guard(
            connection: ClosingConnection,
            capability: object,
        ) -> str | None:
            violation = original_end_authorizer_guard(
                connection,
                capability,  # type: ignore[arg-type]
            )
            if revoke_attempted.is_set():
                authorizer_restored.set()
            return violation

        def wait_for_retained_attacks(
            _repository: JobRepository,
            connection: sqlite3.Connection,
            observed_job_id: str,
            expected: object,
        ) -> None:
            if not attack_done.wait(timeout=5):
                raise RuntimeError("retained publication attack timed out")
            original_assert_snapshot(
                connection,
                observed_job_id,
                expected,  # type: ignore[arg-type]
            )

        def release_after_revoke_attempt() -> None:
            if not revoke_attempted.wait(timeout=5):
                thread_errors.append("revocation was never attempted")
                release_operation.set()
                return
            restoration_before_release.append(authorizer_restored.is_set())
            release_operation.set()

        def on_publish(publication: object) -> None:
            cursor = publication.cursor()  # type: ignore[attr-defined]
            iterator = iter(
                publication.execute(  # type: ignore[attr-defined]
                    "SELECT source_id FROM sources ORDER BY source_id"
                )
            )

            def use_and_reuse_retained_handles() -> None:
                try:
                    cursor.executemany(  # type: ignore[attr-defined]
                        """
                        INSERT INTO sources(
                            source_id,type,name,path,commit_hash,ingested_at
                        ) VALUES (?,?,?,?,?,?)
                        """,
                        BlockingParameters(),
                    )
                    if not authorizer_restored.wait(timeout=5):
                        raise RuntimeError("authorizer restoration timed out")
                    attacks = (
                        (
                            "connection",
                            lambda: publication.execute(  # type: ignore[attr-defined]
                                """
                                INSERT INTO system_state(
                                    key,value_json,updated_at
                                ) VALUES ('retained-thread-escape','true',1)
                                """
                            ),
                        ),
                        (
                            "cursor",
                            lambda: cursor.execute(  # type: ignore[attr-defined]
                                """
                                INSERT INTO students(
                                    student_id,persona,profile_json,created_at
                                ) VALUES (
                                    'student-retained-thread-escape',
                                    'test','{}',1
                                )
                                """
                            ),
                        ),
                        (
                            "iterator",
                            lambda: iterator.connection.execute(  # type: ignore[attr-defined]
                                """
                                INSERT INTO artifacts(
                                    artifact_id,job_id,type,path,checksum,
                                    metadata_json,created_at,validation_status,
                                    attempt_number,checksum_algorithm,
                                    integrity_status
                                ) VALUES (
                                    'artifact_forged_retained',?,'forged',
                                    '/not/validated','forged','{}',1,
                                    'GENERATED',1,'tree-sha256-v2','VERIFIED_V2'
                                )
                                """,
                                (job_id,),
                            ),
                        ),
                    )
                    for name, attack in attacks:
                        try:
                            attack()
                        except PublicationAccessError as error:
                            if "no longer active" not in str(error):
                                thread_errors.append(
                                    f"{name} returned unexpected denial: {error}"
                                )
                            rejected_operations.append(name)
                        else:
                            thread_errors.append(
                                f"retained {name} operation was admitted"
                            )
                except BaseException as error:
                    thread_errors.append(f"{type(error).__name__}: {error}")
                finally:
                    attack_done.set()

            worker = threading.Thread(
                target=use_and_reuse_retained_handles,
                name="retained-publication-capability",
            )
            controller = threading.Thread(
                target=release_after_revoke_attempt,
                name="publication-revocation-barrier",
            )
            threads.extend((worker, controller))
            worker.start()
            controller.start()
            if not operation_entered.wait(timeout=5):
                raise RuntimeError("publication operation did not enter")

        try:
            with mock.patch.object(
                publication_module._PublicationPolicy,
                "revoke_and_restore",
                new=observed_revoke,
            ), mock.patch.object(
                ClosingConnection,
                "_end_authorizer_guard",
                new=observed_end_authorizer_guard,
            ), mock.patch.object(
                JobRepository,
                "_assert_dependency_publication_snapshot",
                new=wait_for_retained_attacks,
            ):
                self.jobs.succeed_with_artifact(
                    job_id,
                    owner,
                    lease_token,
                    worker_id,
                    artifact,
                    on_publish=on_publish,
                    publication_scope=PublicationScope.SOURCE_INGESTION,
                )
        finally:
            release_operation.set()
            for thread in threads:
                thread.join(timeout=5)

        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertEqual([], thread_errors)
        self.assertEqual([False], restoration_before_release)
        self.assertEqual(
            ["connection", "cursor", "iterator"],
            rejected_operations,
        )
        self.assertTrue(authorizer_restored.is_set())
        self.assertEqual(JobState.SUCCEEDED.value, self.jobs.get(job_id)["state"])
        with self.database.connect() as connection:
            self.assertEqual(
                1,
                connection.execute(
                    """
                    SELECT COUNT(*) FROM sources
                    WHERE source_id='source_inflight_publication_race'
                    """
                ).fetchone()[0],
            )
            self.assertIsNone(
                connection.execute(
                    """
                    SELECT 1 FROM system_state
                    WHERE key='retained-thread-escape'
                    """
                ).fetchone()
            )
            self.assertEqual(
                0,
                connection.execute(
                    """
                    SELECT COUNT(*) FROM students
                    WHERE student_id='student-retained-thread-escape'
                    """
                ).fetchone()[0],
            )
            self.assertEqual(
                [artifact.artifact_id],
                [
                    str(row["artifact_id"])
                    for row in connection.execute(
                        """
                        SELECT artifact_id FROM artifacts
                        WHERE job_id=? ORDER BY artifact_id
                        """,
                        (job_id,),
                    )
                ],
            )

    def test_preexisting_authorizer_is_refused_untouched_and_not_invoked(
        self,
    ) -> None:
        outcomes = ("ok", "ignore", "deny", "raise")
        for outcome in outcomes:
            with self.subTest(outcome=outcome):
                source_id = f"source_preexisting_authorizer_{outcome}"
                callback_entered = False
                authorizer_calls: list[int] = []

                with self.database.transaction(immediate=True) as connection:
                    assert isinstance(connection, ClosingConnection)

                    def prior_authorizer(
                        action: int,
                        argument1: str | None,
                        _argument2: str | None,
                        _database: str | None,
                        _trigger: str | None,
                    ) -> int:
                        authorizer_calls.append(action)
                        if (
                            action == sqlite3.SQLITE_READ
                            and argument1 == "sources"
                        ):
                            if outcome == "raise":
                                raise RuntimeError(
                                    "private pre-existing callback detail"
                                )
                            if outcome == "ignore":
                                return sqlite3.SQLITE_IGNORE
                            if outcome == "deny":
                                return sqlite3.SQLITE_DENY
                        return sqlite3.SQLITE_OK

                    connection.set_authorizer(prior_authorizer)
                    with self.assertRaisesRegex(
                        PublicationAccessError,
                        "controller-owned connection without a tracked "
                        "pre-existing database authorizer",
                    ):
                        with restricted_publication_connection(
                            connection,
                            PublicationScope.SOURCE_INGESTION,
                        ) as publication:
                            callback_entered = True
                            publication.execute(
                                """
                                INSERT INTO sources(
                                    source_id,type,name,path,commit_hash,
                                    ingested_at
                                ) VALUES (?,?,?,?,?,1)
                                """,
                                (
                                    source_id,
                                    "test",
                                    "must not publish",
                                    f"/{source_id}",
                                    outcome,
                                ),
                            )

                    self.assertFalse(callback_entered)
                    self.assertEqual([], authorizer_calls)
                    self.assertIs(
                        connection.learnfactory_authorizer,
                        prior_authorizer,
                    )
                    connection.set_authorizer(None)

                with self.database.connect() as connection:
                    self.assertEqual(
                        0,
                        connection.execute(
                            "SELECT COUNT(*) FROM sources WHERE source_id=?",
                            (source_id,),
                        ).fetchone()[0],
                    )

    def test_background_authorizer_replacement_is_fenced_between_operations(
        self,
    ) -> None:
        cases = (
            "tracked-clear",
            "tracked-alternate",
            "base-clear",
            "base-alternate",
        )
        for case_name in cases:
            with self.subTest(case=case_name):
                key = f"background-authorizer-{case_name}"
                replacement_errors: list[BaseException] = []

                with self.assertRaisesRegex(
                    PublicationAccessError,
                    "suppressed a denied operation",
                ):
                    with self.database.transaction(immediate=True) as connection:
                        assert isinstance(connection, ClosingConnection)

                        def alternate_authorizer(*_args: object) -> int:
                            return sqlite3.SQLITE_OK

                        replacement = (
                            alternate_authorizer
                            if case_name.endswith("alternate")
                            else None
                        )

                        def replace_authorizer() -> None:
                            try:
                                if case_name.startswith("tracked"):
                                    connection.set_authorizer(replacement)
                                else:
                                    sqlite3.Connection.set_authorizer(
                                        connection,
                                        replacement,
                                    )
                            except BaseException as error:
                                replacement_errors.append(error)

                        with restricted_publication_connection(
                            connection,
                            PublicationScope.SOURCE_INGESTION,
                        ) as publication:
                            thread = threading.Thread(
                                target=replace_authorizer,
                                name=f"authorizer-replacement-{case_name}",
                            )
                            thread.start()
                            thread.join(timeout=5)
                            self.assertFalse(
                                thread.is_alive(),
                                "background authorizer replacement deadlocked",
                            )

                            if case_name.startswith("tracked"):
                                self.assertEqual(1, len(replacement_errors))
                                self.assertIsInstance(
                                    replacement_errors[0],
                                    AuthorizerGuardError,
                                )
                                with self.assertRaises(
                                    PublicationAccessError
                                ):
                                    publication.execute(
                                        "SELECT source_id FROM sources"
                                    ).fetchall()
                            else:
                                self.assertEqual([], replacement_errors)
                                # This operation must first reinstall policy
                                # after an untracked base-descriptor mutation.
                                publication.execute(
                                    "SELECT source_id FROM sources"
                                ).fetchall()

                            with self.assertRaises(PublicationAccessError):
                                publication.execute(
                                    """
                                    INSERT INTO system_state(
                                        key,value_json,updated_at
                                    ) VALUES (?,'true',1)
                                    """,
                                    (key,),
                                )

                with self.database.connect() as connection:
                    self.assertEqual(
                        0,
                        connection.execute(
                            "SELECT COUNT(*) FROM system_state WHERE key=?",
                            (key,),
                        ).fetchone()[0],
                    )

    def test_authorizer_restoration_failure_revokes_and_rolls_back(self) -> None:
        original_end_guard = ClosingConnection._end_authorizer_guard
        for failure_point in ("before", "after"):
            with self.subTest(failure=failure_point):
                retained: list[object] = []
                source_id = f"source_restore_failure_{failure_point}"

                def fail_restoration(
                    connection: ClosingConnection,
                    capability: object,
                ) -> str | None:
                    if failure_point == "before":
                        raise RuntimeError("synthetic restoration failure before")
                    result = original_end_guard(
                        connection,
                        capability,  # type: ignore[arg-type]
                    )
                    raise RuntimeError("synthetic restoration failure after")

                with self.assertRaisesRegex(
                    RuntimeError,
                    f"restoration failure {failure_point}",
                ):
                    with mock.patch.object(
                        ClosingConnection,
                        "_end_authorizer_guard",
                        new=fail_restoration,
                    ):
                        with self.database.transaction(
                            immediate=True
                        ) as connection:
                            with restricted_publication_connection(
                                connection,
                                PublicationScope.SOURCE_INGESTION,
                            ) as publication:
                                retained.append(publication)
                                publication.execute(
                                    """
                                    INSERT INTO sources(
                                        source_id,type,name,path,commit_hash,
                                        ingested_at
                                    ) VALUES (?,?,?,?,?,1)
                                    """,
                                    (
                                        source_id,
                                        "test",
                                        "must roll back",
                                        f"/{source_id}",
                                        source_id,
                                    ),
                                )

                with self.assertRaisesRegex(
                    PublicationAccessError,
                    "no longer active",
                ):
                    retained[0].execute(  # type: ignore[attr-defined]
                        "SELECT source_id FROM sources"
                    )
                with self.database.connect() as connection:
                    self.assertEqual(
                        0,
                        connection.execute(
                            "SELECT COUNT(*) FROM sources WHERE source_id=?",
                            (source_id,),
                        ).fetchone()[0],
                    )

    def test_preexisting_authorizer_cannot_run_nested_raw_write(
        self,
    ) -> None:
        job_id = self._new_ready_job(
            job_id="job_reentrant_authorizer_forgery"
        )
        owner = "reentrant-authorizer-owner"
        lease_token, worker_id, workspace = self._claim_and_start(job_id, owner)
        results = Validator(self.database).run(
            job_id,
            workspace,
            [{"type": "handler_evidence", "name": "pass", "passed": True}],
            self.root / "logs" / job_id,
        )
        self.assertEqual(["PASS"], [result.status for result in results])
        artifact = self._prepared_artifact(job_id, 1)
        connections: list[ClosingConnection] = []
        prior_callbacks: list[object] = []
        nested_write_fired = False
        callback_entered = False

        class ReentrantAuthorizerDatabase(Database):
            def connect(
                self, *, busy_timeout_seconds: float | None = None
            ) -> sqlite3.Connection:
                connection = super().connect(
                    busy_timeout_seconds=busy_timeout_seconds
                )
                assert isinstance(connection, ClosingConnection)

                def prior_authorizer(
                    action: int,
                    argument1: str | None,
                    _argument2: str | None,
                    _database: str | None,
                    _trigger: str | None,
                ) -> int:
                    nonlocal nested_write_fired
                    if (
                        not nested_write_fired
                        and action == sqlite3.SQLITE_READ
                        and argument1 == "sources"
                    ):
                        nested_write_fired = True
                        # This is the exact composition exploit: clearing policy
                        # and writing through the raw connection before the
                        # outer authorizer invocation returns.
                        sqlite3.Connection.set_authorizer(connection, None)
                        sqlite3.Connection.execute(
                            connection,
                            """
                            INSERT INTO system_state(
                                key,value_json,updated_at
                            ) VALUES (
                                'reentrant-authorizer-control','true',1
                            )
                            """,
                        )
                    return sqlite3.SQLITE_OK

                connection.set_authorizer(prior_authorizer)
                connections.append(connection)
                prior_callbacks.append(prior_authorizer)
                return connection

        authorizing_jobs = JobRepository(
            ReentrantAuthorizerDatabase(self.database_path, self.migrations),
            retry_base=0.01,
            retry_max=0.1,
        )

        def trigger_prior(publication: object) -> None:
            nonlocal callback_entered
            callback_entered = True
            publication.execute(  # type: ignore[attr-defined]
                "SELECT source_id FROM sources"
            ).fetchall()

        with self.assertRaisesRegex(
            PublicationCallbackError,
            "controller-owned connection without a tracked "
            "pre-existing database authorizer",
        ) as captured:
            authorizing_jobs.succeed_with_artifact(
                job_id,
                owner,
                lease_token,
                worker_id,
                artifact,
                on_publish=trigger_prior,  # type: ignore[arg-type]
                publication_scope=PublicationScope.SOURCE_INGESTION,
            )

        self.assertNotIn("private", str(captured.exception).lower())
        self.assertFalse(callback_entered)
        self.assertFalse(nested_write_fired)
        self.assertEqual(1, len(connections))
        self.assertIs(
            connections[0].learnfactory_authorizer,
            prior_callbacks[0],
        )
        record = self.jobs.get(job_id)
        assert record is not None
        self.assertEqual(JobState.RUNNING.value, record["state"])
        with self.database.connect() as connection:
            self.assertEqual(
                0,
                connection.execute(
                    "SELECT COUNT(*) FROM artifacts WHERE job_id=?",
                    (job_id,),
                ).fetchone()[0],
            )
            self.assertIsNone(
                connection.execute(
                    """
                    SELECT 1 FROM system_state
                    WHERE key='reentrant-authorizer-control'
                    """
                ).fetchone()
            )

    def test_publication_facade_and_authorizer_block_escape_atomically(
        self,
    ) -> None:
        job_id = self._new_ready_job(job_id="job_publication_authority_attacks")
        owner = "publication-authority-owner"
        lease_token, worker_id, workspace = self._claim_and_start(job_id, owner)
        results = Validator(self.database).run(
            job_id,
            workspace,
            [{"type": "handler_evidence", "name": "pass", "passed": True}],
            self.root / "logs" / job_id,
        )
        self.assertEqual(["PASS"], [result.status for result in results])
        artifact = self._prepared_artifact(job_id, 1)

        parent = "job_publication_other_parent"
        child = "job_publication_other_child"
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                """
                INSERT INTO jobs(job_id,type,worker_type,state,payload_json,created_at)
                VALUES (?,'test','test','SUCCEEDED','{}',?)
                """,
                (parent, time.time()),
            )
            connection.execute(
                """
                INSERT INTO jobs(job_id,type,worker_type,state,payload_json,created_at)
                VALUES (?,'test','test','DISCOVERED','{}',?)
                """,
                (child, time.time()),
            )
            connection.execute(
                """
                INSERT INTO job_dependencies(job_id,depends_on_job_id)
                VALUES (?,?)
                """,
                (child, parent),
            )
            schema_before = list(
                connection.execute(
                    """
                    SELECT type,name,tbl_name,sql FROM sqlite_master
                    WHERE type IN ('table','index','trigger','view')
                    ORDER BY type,name
                    """
                )
            )

        external_path = self.root / "publication-external.db"
        with sqlite3.connect(external_path) as external:
            external.execute("CREATE TABLE marker(value TEXT NOT NULL)")
            external.execute("INSERT INTO marker(value) VALUES ('untouched')")

        def cursor_connection_escape(connection: object) -> None:
            cursor = connection.execute(  # type: ignore[attr-defined]
                "SELECT source_id FROM sources LIMIT 1"
            )
            self.assertIs(cursor.connection, connection)
            self.assertNotIsInstance(cursor.connection, sqlite3.Connection)
            cursor.connection.commit()

        def historical_iterator_escape_matrix(connection: object) -> None:
            # sqlite3.Cursor is its own iterator, so the historical wrapper
            # returned a raw cursor here and exposed its owning connection.
            # Keep the complete exploit sequence in the regression: the first
            # set_authorizer call must now hit the restricted facade, making
            # every following mutation unreachable and the marker atomic.
            escaped = iter(
                connection.execute(  # type: ignore[attr-defined]
                    "SELECT source_id FROM sources ORDER BY source_id"
                )
            ).connection
            self.assertIs(escaped, connection)
            self.assertNotIsInstance(escaped, sqlite3.Connection)
            escaped.set_authorizer(None)
            escaped.execute(
                """
                INSERT INTO system_state(key,value_json,updated_at)
                VALUES ('publication-escaped','true',?)
                """,
                (time.time(),),
            )
            escaped.execute(
                """
                INSERT INTO artifacts(
                    artifact_id,job_id,type,path,checksum,metadata_json,created_at,
                    validation_status,attempt_number,checksum_algorithm,integrity_status
                ) VALUES (
                    'artifact_iterator_escape',?,'test','/tmp/escaped','x','{}',?,
                    'GENERATED',1,'tree-sha256-v2','VERIFIED_V2'
                )
                """,
                (job_id, time.time()),
            )
            escaped.execute("DROP TRIGGER job_dependencies_delete_guard")
            escaped.execute("DROP TRIGGER job_dependencies_insert_guard")
            escaped.execute(
                "DELETE FROM job_dependencies WHERE job_id=?", (child,)
            )
            escaped.execute("CREATE TABLE escaped_iterator_schema(value TEXT)")
            escaped.execute("PRAGMA writable_schema=ON")
            escaped.execute(
                "ATTACH DATABASE ? AS iterator_external", (str(external_path),)
            )
            escaped.execute("UPDATE iterator_external.marker SET value='mutated'")
            escaped.execute(
                """
                INSERT INTO students(student_id,persona,profile_json,created_at)
                VALUES ('student_iterator_escape','test','{}',?)
                """,
                (time.time(),),
            )

        def cursor_close(connection: object) -> None:
            connection.cursor().close()  # type: ignore[attr-defined]

        def replace_authorizer(connection: object) -> None:
            connection.set_authorizer(None)  # type: ignore[attr-defined]

        def attach_external(connection: object) -> None:
            connection.execute(  # type: ignore[attr-defined]
                "ATTACH DATABASE ? AS escaped", (str(external_path),)
            )

        def graph_rewrite_script(connection: object) -> None:
            connection.executescript(  # type: ignore[attr-defined]
                f"""
                DROP TRIGGER job_dependencies_delete_guard;
                DROP TRIGGER job_dependencies_insert_guard;
                DELETE FROM job_dependencies WHERE job_id='{child}';
                INSERT INTO job_dependencies(job_id,depends_on_job_id)
                VALUES ('{child}','{job_id}');
                """
            )

        def suppress_denied_commit(connection: object) -> None:
            try:
                connection.commit()  # type: ignore[attr-defined]
            except PublicationAccessError:
                pass

        def suppress_denied_control_write(connection: object) -> None:
            try:
                connection.execute(  # type: ignore[attr-defined]
                    "UPDATE jobs SET state='SUCCEEDED' WHERE job_id=?", (job_id,)
                )
            except PublicationAccessError:
                pass

        attacks: list[tuple[str, PublicationScope, object]] = [
            ("commit-method", PublicationScope.SOURCE_INGESTION, lambda c: c.commit()),
            ("rollback-method", PublicationScope.SOURCE_INGESTION, lambda c: c.rollback()),
            ("close-method", PublicationScope.SOURCE_INGESTION, lambda c: c.close()),
            (
                "executescript-method",
                PublicationScope.SOURCE_INGESTION,
                lambda c: c.executescript("COMMIT; CREATE TABLE escaped(value);"),
            ),
            ("authorizer-replacement", PublicationScope.SOURCE_INGESTION, replace_authorizer),
            (
                "historical-iterator-escape-matrix",
                PublicationScope.SOURCE_INGESTION,
                historical_iterator_escape_matrix,
            ),
            (
                "extension-enable",
                PublicationScope.SOURCE_INGESTION,
                lambda c: c.enable_load_extension(True),
            ),
            (
                "extension-load",
                PublicationScope.SOURCE_INGESTION,
                lambda c: c.load_extension("/tmp/not-a-real-extension"),
            ),
            ("cursor-connection", PublicationScope.SOURCE_INGESTION, cursor_connection_escape),
            ("cursor-close", PublicationScope.SOURCE_INGESTION, cursor_close),
            (
                "suppressed-method-denial",
                PublicationScope.SOURCE_INGESTION,
                suppress_denied_commit,
            ),
            (
                "suppressed-authorizer-denial",
                PublicationScope.SOURCE_INGESTION,
                suppress_denied_control_write,
            ),
            ("sql-begin", PublicationScope.SOURCE_INGESTION, lambda c: c.execute("BEGIN")),
            ("sql-commit", PublicationScope.SOURCE_INGESTION, lambda c: c.execute("COMMIT")),
            ("sql-end", PublicationScope.SOURCE_INGESTION, lambda c: c.execute("END")),
            ("sql-rollback", PublicationScope.SOURCE_INGESTION, lambda c: c.execute("ROLLBACK")),
            (
                "sql-savepoint",
                PublicationScope.SOURCE_INGESTION,
                lambda c: c.execute("SAVEPOINT escaped"),
            ),
            (
                "sql-release",
                PublicationScope.SOURCE_INGESTION,
                lambda c: c.execute("RELEASE escaped"),
            ),
            (
                "pragma-foreign-keys",
                PublicationScope.SOURCE_INGESTION,
                lambda c: c.execute("PRAGMA foreign_keys=OFF"),
            ),
            (
                "pragma-writable-schema",
                PublicationScope.SOURCE_INGESTION,
                lambda c: c.execute("PRAGMA writable_schema=ON"),
            ),
            ("attach", PublicationScope.SOURCE_INGESTION, attach_external),
            ("detach", PublicationScope.SOURCE_INGESTION, lambda c: c.execute("DETACH escaped")),
            (
                "create-ddl",
                PublicationScope.SOURCE_INGESTION,
                lambda c: c.execute("CREATE TABLE escaped(value TEXT)"),
            ),
            (
                "alter-ddl",
                PublicationScope.SOURCE_INGESTION,
                lambda c: c.execute("ALTER TABLE sources ADD COLUMN escaped TEXT"),
            ),
            (
                "drop-guard-ddl",
                PublicationScope.SOURCE_INGESTION,
                lambda c: c.execute("DROP TRIGGER job_dependencies_delete_guard"),
            ),
            (
                "cte-job-update",
                PublicationScope.SOURCE_INGESTION,
                lambda c: c.execute(
                    "WITH target AS (SELECT ?) UPDATE jobs SET state='SUCCEEDED' WHERE job_id IN target",
                    (job_id,),
                ),
            ),
            (
                "control-marker",
                PublicationScope.SOURCE_INGESTION,
                lambda c: c.execute(
                    "INSERT INTO system_state(key,value_json,updated_at) VALUES ('publication-escaped','true',?)",
                    (time.time(),),
                ),
            ),
            (
                "artifact-injection",
                PublicationScope.SOURCE_INGESTION,
                lambda c: c.execute(
                    """
                    INSERT INTO artifacts(
                        artifact_id,job_id,type,path,checksum,metadata_json,created_at,
                        validation_status,attempt_number,checksum_algorithm,integrity_status
                    ) VALUES ('artifact_escaped',?,'test','/tmp/escaped','x','{}',?,'GENERATED',1,'tree-sha256-v2','VERIFIED_V2')
                    """,
                    (job_id, time.time()),
                ),
            ),
            (
                "other-job-graph-delete",
                PublicationScope.SOURCE_INGESTION,
                lambda c: c.execute(
                    "DELETE FROM job_dependencies WHERE job_id=?", (child,)
                ),
            ),
            ("guard-recreate-and-graph-rewrite", PublicationScope.SOURCE_INGESTION, graph_rewrite_script),
            (
                "schema-read",
                PublicationScope.SOURCE_INGESTION,
                lambda c: c.execute("SELECT sql FROM sqlite_master").fetchall(),
            ),
            (
                "sql-load-extension",
                PublicationScope.SOURCE_INGESTION,
                lambda c: c.execute("SELECT load_extension('/tmp/escaped')"),
            ),
            (
                "source-to-learner-write",
                PublicationScope.SOURCE_INGESTION,
                lambda c: c.execute(
                    "UPDATE students SET current_state_json='{}'"
                ),
            ),
            (
                "source-to-learner-read",
                PublicationScope.SOURCE_INGESTION,
                lambda c: c.execute("SELECT COUNT(*) FROM attempts").fetchone(),
            ),
            (
                "learner-to-source-write",
                PublicationScope.LEARNER_EVIDENCE,
                lambda c: c.execute("DELETE FROM courses"),
            ),
            (
                "learner-to-source-read",
                PublicationScope.LEARNER_EVIDENCE,
                lambda c: c.execute("SELECT COUNT(*) FROM courses").fetchone(),
            ),
            (
                "learner-attempt-invalidation-read",
                PublicationScope.LEARNER_EVIDENCE,
                lambda c: c.execute(
                    "SELECT COUNT(*) FROM learner_attempt_invalidations"
                ).fetchone(),
            ),
            (
                "learner-evidence-invalidation-insert",
                PublicationScope.LEARNER_EVIDENCE,
                lambda c: c.execute(
                    """
                    INSERT INTO learner_evidence_invalidations(
                        invalidation_id,evidence_id,attempt_id,source_job_id,
                        reason,invalidated_at
                    ) VALUES ('escaped','evidence','attempt',?,'escaped',?)
                    """,
                    (job_id, time.time()),
                ),
            ),
            (
                "learner-evidence-invalidation-delete",
                PublicationScope.LEARNER_EVIDENCE,
                lambda c: c.execute("DELETE FROM learner_evidence_invalidations"),
            ),
            (
                "learner-attempt-invalidation-insert",
                PublicationScope.LEARNER_EVIDENCE,
                lambda c: c.execute(
                    """
                    INSERT INTO learner_attempt_invalidations(
                        invalidation_id,attempt_id,source_job_id,reason,
                        replacement_policy,invalidated_at
                    ) VALUES ('escaped','attempt',?,'escaped','escaped',?)
                    """,
                    (job_id, time.time()),
                ),
            ),
            (
                "learner-attempt-invalidation-delete",
                PublicationScope.LEARNER_EVIDENCE,
                lambda c: c.execute("DELETE FROM learner_attempt_invalidations"),
            ),
        ]

        for attack_name, scope, raw_attack in attacks:
            def attack_after_marker(connection: object) -> None:
                connection.execute(  # type: ignore[attr-defined]
                    """
                    INSERT INTO events(timestamp,actor,type,payload_json)
                    VALUES (?,'publication-attack','PUBLICATION_ATTACK',?)
                    """,
                    (time.time(), json.dumps({"attack": attack_name})),
                )
                raw_attack(connection)  # type: ignore[operator]

            with self.subTest(attack=attack_name), self.assertRaisesRegex(
                PublicationCallbackError, "exceeded authority"
            ):
                self.jobs.succeed_with_artifact(
                    job_id,
                    owner,
                    lease_token,
                    worker_id,
                    artifact,
                    on_publish=attack_after_marker,  # type: ignore[arg-type]
                    publication_scope=scope,
                )

            with self.database.connect() as connection:
                self.assertEqual("RUNNING", self.jobs.get(job_id)["state"])
                self.assertEqual(
                    0,
                    connection.execute(
                        "SELECT COUNT(*) FROM artifacts WHERE job_id=?", (job_id,)
                    ).fetchone()[0],
                )
                self.assertEqual(
                    0,
                    connection.execute(
                        "SELECT COUNT(*) FROM events WHERE actor='publication-attack'"
                    ).fetchone()[0],
                )
                self.assertIsNone(
                    connection.execute(
                        "SELECT 1 FROM system_state WHERE key='publication-escaped'"
                    ).fetchone()
                )
                self.assertEqual(
                    0,
                    connection.execute(
                        """
                        SELECT COUNT(*) FROM students
                        WHERE student_id='student_iterator_escape'
                        """
                    ).fetchone()[0],
                )
                self.assertEqual(
                    [(child, parent)],
                    [
                        tuple(row)
                        for row in connection.execute(
                            """
                            SELECT job_id,depends_on_job_id FROM job_dependencies
                            WHERE job_id=? ORDER BY depends_on_job_id
                            """,
                            (child,),
                        )
                    ],
                )
                self.assertEqual(
                    [tuple(row) for row in schema_before],
                    [
                        tuple(row)
                        for row in connection.execute(
                            """
                            SELECT type,name,tbl_name,sql FROM sqlite_master
                            WHERE type IN ('table','index','trigger','view')
                            ORDER BY type,name
                            """
                        )
                    ],
                )
            with sqlite3.connect(external_path) as external:
                self.assertEqual(
                    [("untouched",)], external.execute("SELECT value FROM marker").fetchall()
                )

    def test_success_publication_rejects_changed_prerequisite_atomically(
        self,
    ) -> None:
        parent = "job_publication_prerequisite"
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                """
                INSERT INTO jobs(job_id,type,worker_type,state,payload_json,created_at)
                VALUES (?,'test','test','SUCCEEDED','{}',?)
                """,
                (parent, time.time()),
            )
        child = self.jobs.create(
            "child",
            "test",
            {},
            dependencies=[parent],
            job_id="job_publication_dependency_child",
        )
        self.jobs.promote_eligible()
        lease_token, worker_id, workspace = self._claim_and_start(
            child, "publication-owner"
        )
        results = Validator(self.database).run(
            child,
            workspace,
            [{"type": "handler_evidence", "name": "pass", "passed": True}],
            self.root / "logs" / child,
        )
        self.assertEqual(["PASS"], [result.status for result in results])

        # Supported state transitions make SUCCEEDED terminal. Model an
        # independently corrupted legacy writer to prove publication still
        # fails closed if that invariant is violated outside this API.
        connection = sqlite3.connect(
            self.database_path,
            isolation_level=None,
            timeout=5,
        )
        try:
            connection.execute("PRAGMA foreign_keys=OFF")
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("DELETE FROM jobs WHERE job_id=?", (parent,))
            connection.execute(
                """
                INSERT INTO jobs(job_id,type,worker_type,state,payload_json,created_at)
                VALUES (?,'test','test','CANCELLED','{}',?)
                """,
                (parent, time.time()),
            )
            connection.commit()
        finally:
            connection.close()

        artifact = self._prepared_artifact(child, 1)
        callback_called = False

        def on_publish(_connection: sqlite3.Connection) -> None:
            nonlocal callback_called
            callback_called = True

        with self.assertRaisesRegex(
            UnsatisfiedDependencyError,
            "unsatisfied dependencies",
        ):
            self.jobs.succeed_with_artifact(
                child,
                "publication-owner",
                lease_token,
                worker_id,
                artifact,
                on_publish=on_publish,
                publication_scope=PublicationScope.SOURCE_INGESTION,
            )

        self.assertFalse(callback_called)
        self.assertEqual(JobState.RUNNING.value, self.jobs.get(child)["state"])
        with self.database.connect() as connection:
            artifact_count = connection.execute(
                "SELECT COUNT(*) FROM artifacts WHERE job_id=?",
                (child,),
            ).fetchone()[0]
        self.assertEqual(0, artifact_count)

    def test_final_success_update_rechecks_dependency_after_publish_hook(
        self,
    ) -> None:
        satisfied_parent = "job_hook_satisfied_parent"
        cancelled_parent = "job_hook_cancelled_parent"
        with self.database.transaction(immediate=True) as connection:
            connection.executemany(
                """
                INSERT INTO jobs(job_id,type,worker_type,state,payload_json,created_at)
                VALUES (?,'test','test',?,'{}',?)
                """,
                [
                    (satisfied_parent, "SUCCEEDED", time.time()),
                    (cancelled_parent, "CANCELLED", time.time()),
                ],
            )
        child = self.jobs.create(
            "child",
            "test",
            {},
            dependencies=[satisfied_parent],
            job_id="job_publish_hook_dependency_child",
        )
        self.jobs.promote_eligible()
        lease_token, worker_id, workspace = self._claim_and_start(
            child, "publish-hook-owner"
        )
        results = Validator(self.database).run(
            child,
            workspace,
            [{"type": "handler_evidence", "name": "pass", "passed": True}],
            self.root / "logs" / child,
        )
        self.assertEqual(["PASS"], [result.status for result in results])
        artifact = self._prepared_artifact(child, 1)

        def adversarial_publish(connection: sqlite3.Connection) -> None:
            # Model a future publication hook with excessive database
            # authority. The final UPDATE predicate must still catch its edge.
            connection.execute("DROP TRIGGER job_dependencies_insert_guard")
            connection.execute(
                """
                INSERT INTO job_dependencies(job_id,depends_on_job_id)
                VALUES (?,?)
                """,
                (child, cancelled_parent),
            )
            connection.execute(
                """
                INSERT INTO system_state(key,value_json,updated_at)
                VALUES ('adversarial_publish_marker','true',?)
                """,
                (time.time(),),
            )

        with self.assertRaisesRegex(
            PublicationCallbackError,
            "publication hook exceeded authority",
        ):
            self.jobs.succeed_with_artifact(
                child,
                "publish-hook-owner",
                lease_token,
                worker_id,
                artifact,
                on_publish=adversarial_publish,
                publication_scope=PublicationScope.SOURCE_INGESTION,
            )

        self.assertEqual(JobState.RUNNING.value, self.jobs.get(child)["state"])
        with self.database.connect() as connection:
            self.assertEqual(
                1,
                connection.execute(
                    """
                    SELECT COUNT(*) FROM sqlite_master
                    WHERE type='trigger' AND name='job_dependencies_insert_guard'
                    """
                ).fetchone()[0],
            )
            self.assertEqual(
                [satisfied_parent],
                [
                    str(row[0])
                    for row in connection.execute(
                        """
                        SELECT depends_on_job_id FROM job_dependencies
                        WHERE job_id=? ORDER BY depends_on_job_id
                        """,
                        (child,),
                    )
                ],
            )
            self.assertEqual(
                0,
                connection.execute(
                    "SELECT COUNT(*) FROM artifacts WHERE job_id=?",
                    (child,),
                ).fetchone()[0],
            )
            self.assertIsNone(
                connection.execute(
                    """
                    SELECT 1 FROM system_state
                    WHERE key='adversarial_publish_marker'
                    """
                ).fetchone()
            )

    def test_publish_hook_cannot_delete_edges_or_dependency_guards(
        self,
    ) -> None:
        first_parent = "job_hook_snapshot_parent_first"
        second_parent = "job_hook_snapshot_parent_second"
        timestamp = time.time()
        with self.database.transaction(immediate=True) as connection:
            connection.executemany(
                """
                INSERT INTO jobs(job_id,type,worker_type,state,payload_json,created_at)
                VALUES (?,'test','test','SUCCEEDED','{}',?)
                """,
                [(first_parent, timestamp), (second_parent, timestamp)],
            )
        child = self.jobs.create(
            "child",
            "test",
            {},
            dependencies=[first_parent],
            job_id="job_publish_hook_snapshot_child",
        )
        self.jobs.promote_eligible()
        lease_token, worker_id, workspace = self._claim_and_start(
            child, "publish-snapshot-owner"
        )
        results = Validator(self.database).run(
            child,
            workspace,
            [{"type": "handler_evidence", "name": "pass", "passed": True}],
            self.root / "logs" / child,
        )
        self.assertEqual(["PASS"], [result.status for result in results])
        artifact = self._prepared_artifact(child, 1)

        def direct_delete(connection: sqlite3.Connection) -> None:
            connection.execute(
                """
                DELETE FROM job_dependencies
                WHERE job_id=? AND depends_on_job_id=?
                """,
                (child, first_parent),
            )

        def replace_edge_after_dropping_guards(
            connection: sqlite3.Connection,
        ) -> None:
            connection.execute("DROP TRIGGER job_dependencies_delete_guard")
            connection.execute("DROP TRIGGER job_dependencies_insert_guard")
            connection.execute(
                """
                DELETE FROM job_dependencies
                WHERE job_id=? AND depends_on_job_id=?
                """,
                (child, first_parent),
            )
            connection.execute(
                """
                INSERT INTO job_dependencies(job_id,depends_on_job_id)
                VALUES (?,?)
                """,
                (child, second_parent),
            )

        def drop_guard_only(connection: sqlite3.Connection) -> None:
            connection.execute("DROP TRIGGER job_dependencies_delete_guard")

        for name, callback in (
            ("direct-delete", direct_delete),
            ("drop-and-replace", replace_edge_after_dropping_guards),
            ("drop-trigger-only", drop_guard_only),
        ):
            with self.subTest(attack=name), self.assertRaisesRegex(
                PublicationCallbackError,
                "publication hook exceeded authority",
            ):
                self.jobs.succeed_with_artifact(
                    child,
                    "publish-snapshot-owner",
                    lease_token,
                    worker_id,
                    artifact,
                    on_publish=callback,
                    publication_scope=PublicationScope.SOURCE_INGESTION,
                )

            self.assertEqual(JobState.RUNNING.value, self.jobs.get(child)["state"])
            with self.database.connect() as connection:
                self.assertEqual(
                    [first_parent],
                    [
                        str(row[0])
                        for row in connection.execute(
                            """
                            SELECT depends_on_job_id FROM job_dependencies
                            WHERE job_id=? ORDER BY depends_on_job_id
                            """,
                            (child,),
                        )
                    ],
                )
                self.assertEqual(
                    1,
                    connection.execute(
                        """
                        SELECT COUNT(*) FROM sqlite_master
                        WHERE type='trigger'
                          AND name='job_dependencies_delete_guard'
                        """
                    ).fetchone()[0],
                )
                self.assertEqual(
                    0,
                    connection.execute(
                        "SELECT COUNT(*) FROM artifacts WHERE job_id=?",
                        (child,),
                    ).fetchone()[0],
                )

    def test_start_atomically_renews_claim_lease_from_start_timestamp(self) -> None:
        job_id = self._new_ready_job(job_id="job_start_renews_lease")
        claimed = self.jobs.claim_next(
            "renew-owner", 30, max_total=1, type_limits={}
        )
        assert claimed is not None
        workspace = self.root / "renewed-workspace"
        workspace.mkdir()
        worker_id = "worker_start_renews_lease"
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                """
                INSERT INTO workers(
                    worker_id,type,state,started_at,last_activity,current_job,workspace
                ) VALUES (?,?,?,?,?,?,?)
                """,
                (worker_id, "test", "STARTING", 99, 99, job_id, str(workspace)),
            )
            connection.execute(
                "UPDATE jobs SET lease_expires_at=101 WHERE job_id=?",
                (job_id,),
            )

        with mock.patch("learnfactory.jobs.now", return_value=100):
            renewed_until = self.jobs.start(
                job_id,
                "renew-owner",
                claimed.lease_token,
                worker_id,
                str(workspace),
                lease_seconds=30,
            )

        self.assertEqual(130, renewed_until)
        self.assertEqual(130, self.jobs.get(job_id)["lease_expires_at"])

    def test_claim_heartbeat_does_not_advance_registered_worker_before_start(
        self,
    ) -> None:
        job_id = self._new_ready_job(job_id="job_claim_heartbeat_phase")
        claimed = self.jobs.claim_next(
            "phase-owner", 30, max_total=1, type_limits={}
        )
        assert claimed is not None
        worker_id = "worker_claim_heartbeat_phase"
        workspace = self.root / "phase-workspace"
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

        renewed = self.jobs.heartbeat(
            job_id,
            "phase-owner",
            claimed.lease_token,
            worker_id,
            30,
        )
        self.assertIsNotNone(renewed)
        with self.database.connect() as connection:
            worker_state = connection.execute(
                "SELECT state FROM workers WHERE worker_id=?", (worker_id,)
            ).fetchone()["state"]
        self.assertEqual("CLAIMED", self.jobs.get(job_id)["state"])
        self.assertEqual("STARTING", worker_state)

        self.jobs.start(
            job_id,
            "phase-owner",
            claimed.lease_token,
            worker_id,
            str(workspace),
            lease_seconds=30,
        )
        with self.database.connect() as connection:
            worker_state = connection.execute(
                "SELECT state FROM workers WHERE worker_id=?", (worker_id,)
            ).fetchone()["state"]
        self.assertEqual("RUNNING", self.jobs.get(job_id)["state"])
        self.assertEqual("RUNNING", worker_state)

    def test_start_transaction_rolls_back_worker_binding_with_claim(self) -> None:
        job_id = self._new_ready_job(job_id="job_atomic_worker_start")
        claimed = self.jobs.claim_next(
            "atomic-owner", 30, max_total=1, type_limits={}
        )
        assert claimed is not None
        worker_id = "worker_atomic_start_rollback"

        with self.assertRaisesRegex(JobError, "cannot start unowned claim"):
            with self.database.transaction(immediate=True) as connection:
                connection.execute(
                    """
                    INSERT INTO workers(
                        worker_id,type,state,started_at,last_activity,current_job,workspace
                    ) VALUES (?,?,?,?,?,?,?)
                    """,
                    (worker_id, "test", "STARTING", 1, 1, job_id, "workspace"),
                )
                self.jobs.start_in_transaction(
                    connection,
                    job_id,
                    "atomic-owner",
                    "wrong-lease",
                    worker_id,
                    "workspace",
                    lease_seconds=30,
                )

        self.assertEqual("CLAIMED", self.jobs.get(job_id)["state"])
        with self.database.connect() as connection:
            self.assertIsNone(
                connection.execute(
                    "SELECT 1 FROM workers WHERE worker_id=?", (worker_id,)
                ).fetchone()
            )

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
                lease_seconds=30,
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
                lease_seconds=30,
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
            lease_seconds=30,
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
            lease_seconds=30,
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

    def test_validator_fence_skips_command_job_without_mutating_it(self) -> None:
        command_job = self.jobs.create(
            "test_job",
            "test",
            {"validators": [{"type": "command", "argv": ["/bin/true"]}]},
            priority=100,
        )
        structural_job = self.jobs.create(
            "test_job",
            "test",
            {"validators": [{"type": "required_paths", "paths": ["result"]}]},
            priority=1,
        )
        self.jobs.promote_eligible()

        claimed = self.jobs.claim_next(
            "fenced-owner",
            30,
            max_total=1,
            type_limits={},
            blocked_validator_types=frozenset({"command"}),
        )
        self.assertIsNotNone(claimed)
        assert claimed is not None
        self.assertEqual(structural_job, claimed.job_id)
        self.assertEqual("READY", self.jobs.get(command_job)["state"])
        self.assertEqual(
            1,
            self.jobs.count_ready_held_by_validator_fence(
                frozenset({"command"})
            ),
        )

    def test_active_validator_fence_holds_malformed_envelope(self) -> None:
        malformed = [
            self.jobs.create(
                "test_job",
                "test",
                payload,
                priority=100,
            )
            for payload in (
                {"validators": "command"},
                {"validators": {"type": "command"}},
                {"validator": [{"type": "command"}]},
                {
                    "validators": [
                        {"type": "review_acceptance", "mode": 1}
                    ]
                },
            )
        ]
        safe = self.jobs.create("test_job", "test", {}, priority=1)
        self.jobs.promote_eligible()
        claimed = self.jobs.claim_next(
            "fenced-owner",
            30,
            max_total=1,
            type_limits={},
            blocked_validator_types=frozenset({"command"}),
        )
        self.assertIsNotNone(claimed)
        assert claimed is not None
        self.assertEqual(safe, claimed.job_id)
        self.assertTrue(
            all(self.jobs.get(identifier)["state"] == "READY" for identifier in malformed)
        )

    def test_command_fence_includes_review_acceptance_command_mode(self) -> None:
        acceptance = self.jobs.create(
            "test_job",
            "test",
            {
                "validators": [
                    {"type": "review_acceptance", "mode": "command"}
                ]
            },
            priority=100,
        )
        safe = self.jobs.create("test_job", "test", {}, priority=1)
        self.jobs.promote_eligible()
        claimed = self.jobs.claim_next(
            "fenced-owner",
            30,
            max_total=1,
            type_limits={},
            blocked_validator_types=frozenset({"command"}),
        )
        self.assertIsNotNone(claimed)
        assert claimed is not None
        self.assertEqual(safe, claimed.job_id)
        self.assertEqual("READY", self.jobs.get(acceptance)["state"])


if __name__ == "__main__":
    unittest.main()
