from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import subprocess
import tempfile
import threading
import unittest
from collections import Counter
from pathlib import Path

from learnfactory.catalog_synthesis import build_catalog_documents
from learnfactory.config import FactorySettings
from learnfactory.db import Database
from learnfactory.handlers import HandlerFailure, HandlerResult, JobHandlers
from learnfactory.jobs import ClaimedJob, JobError, JobRepository
from learnfactory.planner import curriculum_plan
from learnfactory.reporting import status_snapshot, write_catalog
from learnfactory.seeding import seed_initial_jobs
from learnfactory.sources.base import (
    SourceFormatError,
    git_blob,
    git_tree_entries,
    stable_id,
)
from learnfactory.sources.build_your_own_x import BuildYourOwnXAdapter
from learnfactory.sources.csdiy import CSDIYAdapter
from learnfactory.validation import Validator
from learnfactory.vertical_slices import _source_context
from learnfactory.workspace import PreparedArtifact, WorkspaceManager


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = REPOSITORY_ROOT / "migrations"
CSDIY_SOURCE = REPOSITORY_ROOT.parent / "cs-self-learning"
BYOX_SOURCE = REPOSITORY_ROOT.parent / "build-your-own-x"

CSDIY_PINNED_COMMIT = "adce8e13789dc16aa6d1fbe163e9541736defae4"
BYOX_PINNED_COMMIT = "aa17439b62f384511a5561ce308e9598b94d8989"


def _fixture_git(repository: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=repository,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=10,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(
            f"fixture command failed ({completed.returncode}): {arguments!r}\n"
            f"{completed.stderr}"
        )
    return completed.stdout.strip()


def _commit_fixture(repository: Path) -> str:
    """Make a fixture a real repository so describe/ingest exercise Git provenance."""

    _fixture_git(repository, "init", "--quiet")
    _fixture_git(repository, "config", "user.name", "Learning Factory Tests")
    _fixture_git(repository, "config", "user.email", "tests@example.invalid")
    _fixture_git(repository, "add", ".")
    _fixture_git(repository, "commit", "--quiet", "-m", "fixture")
    return _fixture_git(repository, "rev-parse", "HEAD")


class SourceTestCase(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="learnfactory-sources-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.database = Database(self.root / "factory.db", MIGRATIONS)
        self.database.migrate()

    def _csdiy_fixture(self) -> tuple[Path, str, bytes]:
        repository = self.root / "cs-self-learning"
        topic = repository / "docs" / "操作系统"
        topic.mkdir(parents=True)
        (repository / "mkdocs.yml").write_text("site_name: fixture\n", encoding="utf-8")
        (repository / "template.en.md").write_text("# Course template\n", encoding="utf-8")
        (repository / "LICENSE").write_text(
            "Permission is hereby granted, free of charge, to any person obtaining a copy.\n",
            encoding="utf-8",
        )
        # The Chinese and English files intentionally share a stem.  Only the English
        # catalog record is normalized; the translated sibling must not create a duplicate.
        (topic / "CS900.md").write_text(
            "# CS 900：系统工程\n\n"
            "## 课程介绍\n\n"
            "- Offered by: 不应被解析的中文记录\n"
            "- Difficulty: ⭐\n",
            encoding="utf-8",
        )
        english = (
            "# CS 900: Systems Engineering\n\n"
            "## Descriptions\n\n"
            "- **Offered by**: **Example University**\n"
            "- Prerequisites: Algorithms + C Programming\n"
            "- Programming Languages: C++, Rust\n"
            "- Difficulty: 🌟🌟🌟🌟\n"
            "- Class Hour: 42.5 hours\n\n"
            "A systems course with bilingual catalog material.\n\n"
            "## Course Resources\n\n"
            "- Course Website: <https://courses.example.invalid/cs900>\n"
            "- Recordings: released during the term\n"
            "- Assignments: not available\n"
        ).encode("utf-8")
        (topic / "CS900.en.md").write_bytes(english)
        commit = _commit_fixture(repository)
        return repository, commit, english

    def _byox_fixture(self) -> tuple[Path, str]:
        repository = self.root / "build-your-own-x"
        repository.mkdir()
        (repository / "README.md").write_text(
            "# Build your own <insert-technology-here>\n\n"
            "#### Build your own `Database`\n\n"
            "* [**Python**: _Tiny Database_](https://github.com/example/tiny-db)\n"
            "* [**Rust**: _Tiny Database_](https://example.invalid/tiny-db.pdf)\n\n"
            "#### Build your own `Web Server`\n\n"
            "* [**Go**: _Evented HTTP Server_](https://www.youtube.com/watch?v=fixture) [video]\n\n"
            "#### Uncategorized\n\n"
            "* [**C**: _Small Allocator_](https://example.invalid/allocator)\n\n"
            "## Origins & License\n\n"
            "The catalog author has waived all copyright and related or neighboring rights.\n\n"
            "https://creativecommons.org/publicdomain/zero/1.0/\n",
            encoding="utf-8",
        )
        return repository, _commit_fixture(repository)


class CSDIYSourceTests(SourceTestCase):
    def _prepared_scheduled_ingestion(
        self, repository: Path, suffix: str
    ) -> tuple[
        JobRepository,
        ClaimedJob,
        str,
        WorkspaceManager,
        PreparedArtifact,
        HandlerResult,
    ]:
        settings = FactorySettings(
            root=self.root / "learning-factory",
            database=self.database.path,
            warehouse=self.root / "warehouse",
        )
        manager = WorkspaceManager(settings.warehouse, self.database)
        manager.initialize()
        jobs = JobRepository(self.database)
        job_id = f"job_source_{suffix}"
        jobs.create(
            "source_ingest",
            "ingestion",
            {"source_path": str(repository)},
            job_id=job_id,
            max_attempts=1,
        )
        jobs.promote_eligible()
        claim = jobs.claim_next(
            f"owner-{suffix}", 60, max_total=1, type_limits={"ingestion": 1}
        )
        assert claim is not None
        workspace = manager.allocate(job_id, claim.attempt_count)
        worker_id = f"worker_{suffix}"
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                """
                INSERT INTO workers(
                    worker_id,type,workspace,state,started_at,last_activity,current_job
                ) VALUES (?,?,?,?,?,?,?)
                """,
                (
                    worker_id,
                    "ingestion",
                    str(workspace),
                    "STARTING",
                    1.0,
                    1.0,
                    job_id,
                ),
            )
        jobs.start(
            job_id,
            f"owner-{suffix}",
            claim.lease_token,
            worker_id,
            str(workspace),
            lease_seconds=30,
        )
        result = JobHandlers(settings, self.database, manager).execute(
            claim, workspace, self.root / "logs" / suffix, threading.Event()
        )
        self.assertIsNotNone(result.on_publish)
        with self.database.connect() as connection:
            self.assertEqual(0, connection.execute("SELECT COUNT(*) FROM sources").fetchone()[0])
        validations = Validator(self.database).run(
            job_id,
            workspace,
            result.validators,
            self.root / "logs" / suffix,
            attempt_number=claim.attempt_count,
        )
        self.assertTrue(validations and all(item.passed for item in validations))
        artifact = manager.prepare_archive(
            job_id,
            claim.attempt_count,
            workspace,
            artifact_type=result.artifact_type,
            semantic_path=f"sources/{suffix}",
            metadata=result.metadata,
            validation_status="GENERATED",
            validation_labels=["GENERATED"],
        )
        return jobs, claim, worker_id, manager, artifact, result

    def test_lifecycle_migration_backfills_one_active_snapshot_without_deletion(self) -> None:
        migration_root = self.root / "legacy-migrations"
        migration_root.mkdir()
        migration_files = sorted(MIGRATIONS.glob("[0-9][0-9][0-9]_*.sql"))
        for migration in migration_files:
            if migration.name < "008_":
                shutil.copy2(migration, migration_root / migration.name)
        legacy = Database(self.root / "legacy.db", migration_root)
        legacy.migrate()
        canonical_path = "/snapshots/example"
        with legacy.transaction(immediate=True) as connection:
            connection.executemany(
                """
                INSERT INTO sources(
                    source_id,type,name,path,commit_hash,ingested_at,metadata_json
                ) VALUES (?,?,?,?,?,?,?)
                """,
                [
                    ("source_old", "csdiy", "old", canonical_path, "1" * 40, 10.0, "{}"),
                    ("source_new", "csdiy", "new", canonical_path, "2" * 40, 20.0, "{}"),
                ],
            )
            connection.executemany(
                """
                INSERT INTO courses(course_id,source_id,slug,title)
                VALUES (?,?,?,?)
                """,
                [
                    ("course_old", "source_old", "old", "Historical course"),
                    ("course_new", "source_new", "new", "Current course"),
                ],
            )
        shutil.copy2(
            MIGRATIONS / "008_source_snapshot_lifecycle.sql",
            migration_root / "008_source_snapshot_lifecycle.sql",
        )
        self.assertEqual(["008_source_snapshot_lifecycle.sql"], legacy.migrate())

        with legacy.connect() as connection:
            snapshots = {
                row["source_id"]: dict(row)
                for row in connection.execute(
                    """
                    SELECT source_id,is_active,superseded_by_source_id,superseded_at
                    FROM sources ORDER BY source_id
                    """
                )
            }
            self.assertEqual(2, connection.execute("SELECT COUNT(*) FROM courses").fetchone()[0])
        self.assertEqual(0, snapshots["source_old"]["is_active"])
        self.assertEqual(
            "source_new", snapshots["source_old"]["superseded_by_source_id"]
        )
        self.assertEqual(20.0, snapshots["source_old"]["superseded_at"])
        self.assertEqual(1, snapshots["source_new"]["is_active"])

        with self.assertRaises(sqlite3.IntegrityError):
            with legacy.transaction(immediate=True) as connection:
                connection.execute(
                    """
                    INSERT INTO sources(
                        source_id,type,name,path,commit_hash,ingested_at,metadata_json
                    ) VALUES (?,?,?,?,?,?,?)
                    """,
                    (
                        "source_conflict",
                        "csdiy",
                        "conflict",
                        canonical_path,
                        "3" * 40,
                        30.0,
                        "{}",
                    ),
                )

    def test_bilingual_fixture_parses_english_metadata_resources_and_provenance(self) -> None:
        repository, commit, english = self._csdiy_fixture()
        adapter = CSDIYAdapter()

        descriptor = adapter.describe(repository)
        batch = adapter.extract(descriptor)

        self.assertEqual("MIT", descriptor.license)
        self.assertEqual(commit, descriptor.commit_hash)
        self.assertEqual(1, len(batch.courses))
        course = batch.courses[0]
        self.assertEqual("cs900", course.slug)
        self.assertEqual("CS 900: Systems Engineering", course.title)
        self.assertEqual("Example University", course.institution)
        self.assertEqual("操作系统", course.topic)
        self.assertEqual(("Algorithms", "C Programming"), course.prerequisites)
        self.assertEqual(42.5, course.estimated_human_hours)
        self.assertEqual(4.0, course.difficulty)
        self.assertEqual(
            "A systems course with bilingual catalog material.", course.description
        )
        self.assertEqual("C++, Rust", course.metadata["programming_languages_raw"])
        self.assertEqual("en", course.metadata["language"])
        self.assertNotIn("不应被解析", json.dumps(course.metadata, ensure_ascii=False))

        provenance = course.metadata["provenance"]
        self.assertEqual("source-derived", provenance["classification"])
        self.assertEqual(commit, provenance["source_commit"])
        self.assertEqual("docs/操作系统/CS900.en.md", provenance["source_file"])
        self.assertEqual(hashlib.sha256(english).hexdigest(), provenance["content_sha256"])
        self.assertEqual("csdiy", provenance["adapter"])

        units = {unit.title: unit for unit in batch.units}
        self.assertEqual(
            {
                "Catalog overview and resource guide",
                "Course Website",
                "Recordings",
                "Assignments",
            },
            set(units),
        )
        self.assertEqual("reading", units["Course Website"].unit_type)
        self.assertEqual("LINKED", units["Course Website"].metadata["availability"])
        self.assertEqual(
            ["https://courses.example.invalid/cs900"],
            units["Course Website"].metadata["urls"],
        )
        self.assertEqual("lecture", units["Recordings"].unit_type)
        self.assertEqual("DESCRIBED", units["Recordings"].metadata["availability"])
        self.assertEqual("assignment", units["Assignments"].unit_type)
        self.assertEqual("UNAVAILABLE", units["Assignments"].metadata["availability"])

    def test_dirty_and_untracked_worktree_content_cannot_change_recorded_snapshot(self) -> None:
        repository, commit, english = self._csdiy_fixture()
        course_path = repository / "docs" / "操作系统" / "CS900.en.md"
        course_path.write_text(
            "# Poisoned live course\n\n"
            "## Descriptions\n\n"
            "- Offered by: Worktree Attacker\n"
            "- Difficulty: ⭐\n"
            "- Class Hour: 999 hours\n",
            encoding="utf-8",
        )
        (repository / "LICENSE").write_text(
            "GNU General Public License version 3\n", encoding="utf-8"
        )
        (repository / "template.en.md").unlink()
        (repository / "docs" / "操作系统" / "Untracked.en.md").write_text(
            "# Untracked secret\n\n"
            "- Offered by: Must Not Be Read\n"
            "- Difficulty: ⭐\n"
            "- Class Hour: 1 hour\n",
            encoding="utf-8",
        )
        adapter = CSDIYAdapter()

        self.assertTrue(adapter.detect(repository))
        descriptor = adapter.describe(repository)
        batch = adapter.extract(descriptor)

        self.assertEqual(commit, descriptor.commit_hash)
        self.assertTrue(descriptor.metadata["working_tree_dirty"])
        self.assertEqual("git-object-database", descriptor.metadata["snapshot_reader"])
        self.assertEqual("MIT", descriptor.license)
        committed_license = git_blob(repository, commit, "LICENSE")
        self.assertEqual(
            hashlib.sha256(committed_license).hexdigest(),
            descriptor.metadata["license_sha256"],
        )
        self.assertEqual(commit, descriptor.metadata["license_source_commit"])
        self.assertEqual(english, git_blob(repository, commit, "docs/操作系统/CS900.en.md"))
        self.assertEqual(1, len(batch.courses))
        course = batch.courses[0]
        self.assertEqual("CS 900: Systems Engineering", course.title)
        self.assertEqual("Example University", course.institution)
        self.assertEqual(42.5, course.estimated_human_hours)
        self.assertEqual(
            hashlib.sha256(english).hexdigest(),
            course.metadata["provenance"]["content_sha256"],
        )
        serialized = json.dumps(course.metadata, ensure_ascii=False)
        self.assertNotIn("Worktree Attacker", serialized)
        self.assertNotIn("Must Not Be Read", serialized)

    def test_committed_course_symlink_is_rejected_without_reading_its_target(self) -> None:
        repository, _, _ = self._csdiy_fixture()
        outside = self.root / "outside-course.en.md"
        outside.write_text(
            "# Exfiltrated course\n\n"
            "- Offered by: Outside Repository\n"
            "- Difficulty: ⭐\n"
            "- Class Hour: 1 hour\n",
            encoding="utf-8",
        )
        link = repository / "docs" / "操作系统" / "Escape.en.md"
        link.symlink_to(outside)
        _fixture_git(repository, "add", "docs/操作系统/Escape.en.md")
        _fixture_git(repository, "commit", "--quiet", "-m", "add unsafe symlink")
        commit = _fixture_git(repository, "rev-parse", "HEAD")
        adapter = CSDIYAdapter()
        descriptor = adapter.describe(repository)

        entry = next(
            item
            for item in git_tree_entries(repository, commit)
            if item.path == "docs/操作系统/Escape.en.md"
        )
        self.assertEqual("120000", entry.mode)
        self.assertTrue(entry.is_symlink)
        with self.assertRaisesRegex(SourceFormatError, "symlink"):
            git_blob(repository, commit, entry.path)
        with self.assertRaisesRegex(SourceFormatError, "tracked symlink"):
            adapter.extract(descriptor)

    def test_ingestion_is_idempotent_and_preserves_stable_ids_and_provenance(self) -> None:
        repository, commit, _ = self._csdiy_fixture()
        adapter = CSDIYAdapter()

        first = adapter.ingest(self.database, repository)
        with self.database.connect() as connection:
            first_ingested_at = connection.execute(
                "SELECT ingested_at FROM sources WHERE source_id=?",
                (first.source_id,),
            ).fetchone()[0]
            first_course = connection.execute(
                "SELECT course_id,source_metadata_json FROM courses"
            ).fetchone()
            first_units = {
                row["source_reference"]: row["unit_id"]
                for row in connection.execute(
                    "SELECT unit_id,source_reference FROM course_units"
                )
            }
        second = adapter.ingest(self.database, repository)

        self.assertEqual(first.source_id, second.source_id)
        self.assertEqual(
            (1, 4, 0, 0),
            (
                second.courses,
                second.course_units,
                second.curriculum_edges,
                second.projects,
            ),
        )
        with self.database.connect() as connection:
            counts = connection.execute(
                """
                SELECT
                  (SELECT COUNT(*) FROM sources) AS sources,
                  (SELECT COUNT(*) FROM courses) AS courses,
                  (SELECT COUNT(*) FROM course_units) AS units,
                  (SELECT COUNT(*) FROM events WHERE type='SOURCE_INGESTED') AS ingestions
                """
            ).fetchone()
            second_course = connection.execute(
                "SELECT course_id,source_metadata_json FROM courses"
            ).fetchone()
            second_units = {
                row["source_reference"]: row["unit_id"]
                for row in connection.execute(
                    "SELECT unit_id,source_reference FROM course_units"
                )
            }
            second_ingested_at = connection.execute(
                "SELECT ingested_at FROM sources WHERE source_id=?",
                (second.source_id,),
            ).fetchone()[0]
        self.assertEqual((1, 1, 4, 2), tuple(counts))
        self.assertEqual(first_ingested_at, second_ingested_at)
        self.assertEqual(first_course["course_id"], second_course["course_id"])
        self.assertEqual(first_units, second_units)
        metadata = json.loads(second_course["source_metadata_json"])
        self.assertEqual(commit, metadata["provenance"]["source_commit"])
        self.assertEqual("source-derived", metadata["provenance"]["classification"])

    def test_scheduled_ingestion_cancellation_cannot_publish_prepared_rows(self) -> None:
        repository, _, _ = self._csdiy_fixture()
        jobs, claim, worker_id, manager, artifact, result = (
            self._prepared_scheduled_ingestion(repository, "cancelled")
        )
        jobs.cancel(claim.job_id)

        with self.assertRaisesRegex(JobError, "cancelled"):
            jobs.succeed_with_artifact(
                claim.job_id,
                "owner-cancelled",
                claim.lease_token,
                worker_id,
                artifact,
                on_publish=result.on_publish,
                publication_scope=result.publication_scope,
            )

        with self.database.connect() as connection:
            self.assertEqual(0, connection.execute("SELECT COUNT(*) FROM sources").fetchone()[0])
            self.assertEqual(0, connection.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0])
        jobs.finish_cancelled(
            claim.job_id, "owner-cancelled", claim.lease_token, worker_id
        )
        manager.discard_prepared(artifact)

    def test_scheduled_ingestion_rejects_changed_head_before_publication(self) -> None:
        repository, expected_commit, _ = self._csdiy_fixture()
        course_path = repository / "docs" / "操作系统" / "CS900.en.md"
        course_path.write_text(
            course_path.read_text(encoding="utf-8") + "\nChanged after enqueue.\n",
            encoding="utf-8",
        )
        _fixture_git(repository, "add", "docs/操作系统/CS900.en.md")
        _fixture_git(repository, "commit", "--quiet", "-m", "advance head")
        settings = FactorySettings(
            root=self.root / "learning-factory",
            database=self.database.path,
            warehouse=self.root / "warehouse",
        )
        manager = WorkspaceManager(settings.warehouse, self.database)
        manager.initialize()
        workspace = manager.allocate("job_source_changed_head", 1)
        job = ClaimedJob(
            job_id="job_source_changed_head",
            type="source_ingest",
            worker_type="ingestion",
            payload={
                "source_path": str(repository),
                "expected_commit": expected_commit,
            },
            attempt_count=1,
            workspace=str(workspace),
            model=None,
            reasoning_effort=None,
            lease_token="lease-test",
        )

        with self.assertRaisesRegex(
            HandlerFailure, "source HEAD changed before preparation"
        ) as raised:
            JobHandlers(settings, self.database, manager).execute(
                job, workspace, self.root / "logs" / "changed-head", threading.Event()
            )
        self.assertEqual("source_snapshot_changed", raised.exception.kind)
        self.assertFalse(raised.exception.retryable)
        with self.database.connect() as connection:
            self.assertEqual(0, connection.execute("SELECT COUNT(*) FROM sources").fetchone()[0])

    def test_scheduled_ingestion_activation_rolls_back_with_failed_publication(self) -> None:
        repository, _, _ = self._csdiy_fixture()
        jobs, claim, worker_id, _, artifact, result = self._prepared_scheduled_ingestion(
            repository, "rollback"
        )
        publish = result.on_publish
        assert publish is not None

        def fail_after_activation(connection: sqlite3.Connection) -> None:
            publish(connection)
            raise RuntimeError("injected publication failure")

        with self.assertRaisesRegex(RuntimeError, "injected publication failure"):
            jobs.succeed_with_artifact(
                claim.job_id,
                "owner-rollback",
                claim.lease_token,
                worker_id,
                artifact,
                on_publish=fail_after_activation,
                publication_scope=result.publication_scope,
            )

        with self.database.connect() as connection:
            self.assertEqual(0, connection.execute("SELECT COUNT(*) FROM sources").fetchone()[0])
            self.assertEqual(0, connection.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0])
            self.assertEqual(
                "RUNNING",
                connection.execute(
                    "SELECT state FROM jobs WHERE job_id=?", (claim.job_id,)
                ).fetchone()[0],
            )

        jobs.succeed_with_artifact(
            claim.job_id,
            "owner-rollback",
            claim.lease_token,
            worker_id,
            artifact,
            on_publish=publish,
            publication_scope=result.publication_scope,
        )
        with self.database.connect() as connection:
            self.assertEqual(
                (1, 1, 1),
                tuple(
                    connection.execute(
                        """
                        SELECT
                          (SELECT COUNT(*) FROM sources),
                          (SELECT COUNT(*) FROM sources WHERE is_active=1),
                          (SELECT COUNT(*) FROM artifacts)
                        """
                    ).fetchone()
                ),
            )

    def test_second_commit_supersedes_catalog_snapshot_without_erasing_provenance(self) -> None:
        repository, _, _ = self._csdiy_fixture()
        course_path = repository / "docs" / "操作系统" / "CS900.en.md"
        course_path.write_text(
            "# MIT 6.S081 Legacy Snapshot\n\n"
            "## Descriptions\n\n"
            "- **Offered by**: **MIT**\n"
            "- Prerequisites: C Programming\n"
            "- Programming Languages: C\n"
            "- Difficulty: 🌟🌟🌟🌟🌟\n"
            "- Class Hour: 150 hours\n\n"
            "Legacy catalog description.\n\n"
            "## Course Resources\n\n"
            "- Course Website: <https://example.invalid/legacy>\n",
            encoding="utf-8",
        )
        _fixture_git(repository, "add", "docs/操作系统/CS900.en.md")
        _fixture_git(repository, "commit", "--quiet", "--amend", "--no-edit")
        old_commit = _fixture_git(repository, "rev-parse", "HEAD")
        adapter = CSDIYAdapter()
        first = adapter.ingest(self.database, repository)

        course_path.write_text(
            "# MIT 6.1810 Current Snapshot\n\n"
            "## Descriptions\n\n"
            "- **Offered by**: **MIT**\n"
            "- Prerequisites: C Programming + Computer Architecture\n"
            "- Programming Languages: C\n"
            "- Difficulty: 🌟🌟🌟🌟🌟\n"
            "- Class Hour: 160 hours\n\n"
            "Current catalog description.\n\n"
            "## Course Resources\n\n"
            "- Course Website: <https://example.invalid/current>\n",
            encoding="utf-8",
        )
        _fixture_git(repository, "add", "docs/操作系统/CS900.en.md")
        _fixture_git(repository, "commit", "--quiet", "-m", "current snapshot")
        current_commit = _fixture_git(repository, "rev-parse", "HEAD")
        second = adapter.ingest(self.database, repository)
        byox_repository, byox_commit = self._byox_fixture()
        byox = BuildYourOwnXAdapter().ingest(self.database, byox_repository)

        self.assertNotEqual(first.source_id, second.source_id)
        with self.database.connect() as connection:
            old_source = connection.execute(
                """
                SELECT is_active,superseded_by_source_id,superseded_at
                FROM sources WHERE source_id=?
                """,
                (first.source_id,),
            ).fetchone()
            current_source = connection.execute(
                """
                SELECT is_active,superseded_by_source_id,superseded_at
                FROM sources WHERE source_id=?
                """,
                (second.source_id,),
            ).fetchone()
            old_course = connection.execute(
                """
                SELECT title,source_metadata_json FROM courses WHERE source_id=?
                """,
                (first.source_id,),
            ).fetchone()
            raw_counts = connection.execute(
                """
                SELECT
                  (SELECT COUNT(*) FROM sources),
                  (SELECT COUNT(*) FROM courses),
                  (SELECT COUNT(*) FROM course_units),
                  (SELECT COUNT(*) FROM build_projects)
                """
            ).fetchone()
        assert old_source is not None and current_source is not None and old_course is not None
        self.assertEqual(0, old_source["is_active"])
        self.assertEqual(second.source_id, old_source["superseded_by_source_id"])
        self.assertIsNotNone(old_source["superseded_at"])
        self.assertEqual((1, None, None), tuple(current_source))
        self.assertEqual("MIT 6.S081 Legacy Snapshot", old_course["title"])
        self.assertEqual(
            old_commit,
            json.loads(old_course["source_metadata_json"])["provenance"]["source_commit"],
        )
        self.assertEqual(
            (3, 2, first.course_units + second.course_units, byox.projects),
            tuple(raw_counts),
        )

        documents = build_catalog_documents(self.database)
        course_items = [
            item for item in documents.backlog["items"] if item["kind"] == "course"
        ]
        self.assertEqual(
            {"sources": 2, "courses": 1, "projects": byox.projects},
            {
                key: documents.backlog["summary"][key]
                for key in ("sources", "courses", "projects")
            },
        )
        self.assertEqual(["MIT 6.1810 Current Snapshot"], [item["title"] for item in course_items])
        self.assertEqual(current_commit, course_items[0]["provenance"]["source_commit"])

        jobs = JobRepository(self.database)
        seeded = seed_initial_jobs(self.database, jobs)
        seeded_course = jobs.get(seeded["course"])
        assert seeded_course is not None
        self.assertEqual("MIT 6.1810 Current Snapshot", seeded_course["payload"]["title"])
        self.assertEqual(current_commit, seeded_course["payload"]["provenance"]["commit"])

        plan = curriculum_plan(self.database, topic="Current Snapshot")
        self.assertEqual(
            ["MIT 6.1810 Current Snapshot"],
            [item["title"] for item in plan["items"] if item["kind"] == "course"],
        )
        snapshot = status_snapshot(self.database)
        self.assertEqual(
            {
                "sources": 2,
                "courses": 1,
                "course_units": second.course_units,
                "projects": byox.projects,
            },
            {
                key: snapshot["counts"][key]
                for key in ("sources", "courses", "course_units", "projects")
            },
        )

        catalog_dir = self.root / "catalog"
        _, catalog_path = write_catalog(self.database, catalog_dir)
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        self.assertEqual(
            {current_commit, byox_commit},
            {source["commit_hash"] for source in catalog["sources"]},
        )
        self.assertNotIn(old_commit, {source["commit_hash"] for source in catalog["sources"]})
        self.assertEqual(
            ["MIT 6.1810 Current Snapshot"],
            [course["title"] for course in catalog["courses"]],
        )

        defaults = {"source_name": "default", "commit_hash": "default"}
        historical_context = _source_context(
            self.database,
            {"course_id": stable_id("course", first.source_id, "cs900")},
            defaults,
            record_table="courses",
        )
        self.assertEqual("defaults", historical_context["lookup_status"])
        active_context = _source_context(
            self.database,
            {"course_id": stable_id("course", second.source_id, "cs900")},
            defaults,
            record_table="courses",
        )
        self.assertEqual("database", active_context["lookup_status"])
        self.assertEqual(current_commit, active_context["commit_hash"])

    @unittest.skipUnless(CSDIY_SOURCE.is_dir(), "local CSDIY source is unavailable")
    def test_pinned_local_catalog_counts_and_known_metadata_are_stable(self) -> None:
        adapter = CSDIYAdapter()
        descriptor = adapter.describe(CSDIY_SOURCE)
        batch = adapter.extract(descriptor)

        self.assertEqual(CSDIY_PINNED_COMMIT, descriptor.commit_hash)
        self.assertEqual("MIT", descriptor.license)
        self.assertEqual(
            (82, 394, 28, 5),
            (
                len(batch.courses),
                len(batch.units),
                len(batch.curriculum_edges),
                len(batch.warnings),
            ),
        )
        self.assertEqual(len(batch.courses), len({course.slug for course in batch.courses}))
        self.assertTrue(
            all(
                course.metadata["provenance"]["source_file"].endswith(".en.md")
                and course.metadata["language"] == "en"
                for course in batch.courses
            )
        )
        mit = next(course for course in batch.courses if course.slug == "mit6-s081")
        self.assertEqual("MIT", mit.institution)
        self.assertEqual(150.0, mit.estimated_human_hours)
        self.assertEqual(5.0, mit.difficulty)
        self.assertEqual(
            ("Computer Architecture", "Solid C Programming Skills", "RISC-V Assembly"),
            mit.prerequisites,
        )
        self.assertEqual(
            "docs/操作系统/MIT6.S081.en.md",
            mit.metadata["provenance"]["source_file"],
        )
        mit_units = [unit for unit in batch.units if unit.course_slug == mit.slug]
        self.assertFalse(
            any("](https" in unit.title for unit in mit_units),
            "ordinary Markdown links must not be parsed as resource metadata fields",
        )


class BuildYourOwnXSourceTests(SourceTestCase):
    def test_fixture_categories_license_boundary_and_idempotent_stable_ids(self) -> None:
        repository, commit = self._byox_fixture()
        adapter = BuildYourOwnXAdapter()

        descriptor = adapter.describe(repository)
        first_batch = adapter.extract(descriptor)
        second_batch = adapter.extract(descriptor)

        self.assertEqual("CC0-1.0", descriptor.license)
        self.assertEqual("NOASSERTION", descriptor.metadata["linked_resource_license"])
        self.assertEqual(commit, descriptor.commit_hash)
        self.assertEqual(
            [project.slug for project in first_batch.projects],
            [project.slug for project in second_batch.projects],
        )
        self.assertEqual(
            {"Database", "Web Server", "Uncategorized"},
            {project.category for project in first_batch.projects},
        )
        self.assertEqual(4, len(first_batch.projects))
        self.assertEqual(4, len({project.slug for project in first_batch.projects}))
        self.assertEqual(
            {"article", "pdf", "repository", "video"},
            {project.source_format for project in first_batch.projects},
        )
        self.assertTrue(
            all(
                project.metadata["linked_resource_license"] == "NOASSERTION"
                and project.metadata["provenance"]["classification"] == "source-derived"
                and project.metadata["provenance"]["source_commit"] == commit
                and project.metadata["provenance"]["source_file"] == "README.md"
                for project in first_batch.projects
            )
        )

        first = adapter.ingest(self.database, repository)
        with self.database.connect() as connection:
            before = {
                row["upstream_reference"]: row["project_id"]
                for row in connection.execute(
                    "SELECT project_id,upstream_reference FROM build_projects"
                )
            }
        second = adapter.ingest(self.database, repository)
        with self.database.connect() as connection:
            after = {
                row["upstream_reference"]: row["project_id"]
                for row in connection.execute(
                    "SELECT project_id,upstream_reference FROM build_projects"
                )
            }
            counts = connection.execute(
                """
                SELECT
                  (SELECT COUNT(*) FROM sources) AS sources,
                  (SELECT COUNT(*) FROM build_projects) AS projects,
                  (SELECT COUNT(*) FROM events WHERE type='SOURCE_INGESTED') AS ingestions
                """
            ).fetchone()
            source = connection.execute(
                "SELECT license,metadata_json FROM sources"
            ).fetchone()

        self.assertEqual(first.source_id, second.source_id)
        self.assertEqual((1, 4, 2), tuple(counts))
        self.assertEqual(before, after)
        self.assertEqual(
            {
                url: stable_id("project", first.source_id, url)
                for url in before
            },
            after,
        )
        self.assertEqual("CC0-1.0", source["license"])
        source_metadata = json.loads(source["metadata_json"])
        self.assertEqual("NOASSERTION", source_metadata["linked_resource_license"])
        self.assertEqual("explicit CC0 waiver declaration", source_metadata["license_evidence"])

    def test_dirty_readme_cannot_change_catalog_or_cc0_license_evidence(self) -> None:
        repository, commit = self._byox_fixture()
        committed_readme = git_blob(repository, commit, "README.md")
        (repository / "README.md").write_text(
            "Poisoned Worktree Entry with no recognizable catalog markers.\n",
            encoding="utf-8",
        )
        adapter = BuildYourOwnXAdapter()

        self.assertTrue(adapter.detect(repository))
        descriptor = adapter.describe(repository)
        batch = adapter.extract(descriptor)

        self.assertEqual(commit, descriptor.commit_hash)
        self.assertTrue(descriptor.metadata["working_tree_dirty"])
        self.assertEqual("CC0-1.0", descriptor.license)
        self.assertEqual(
            hashlib.sha256(committed_readme).hexdigest(),
            descriptor.metadata["license_sha256"],
        )
        self.assertEqual(commit, descriptor.metadata["license_source_commit"])
        self.assertEqual("README.md#origins--license", descriptor.metadata["license_file"])
        self.assertEqual(4, len(batch.projects))
        self.assertNotIn(
            "Poisoned Worktree Entry", {project.title for project in batch.projects}
        )
        self.assertEqual(
            hashlib.sha256(committed_readme).hexdigest(),
            batch.projects[0].metadata["provenance"]["content_sha256"],
        )

    def test_vendored_subtree_uses_committed_source_pin_and_fails_on_drift(
        self,
    ) -> None:
        standalone, pinned_commit = self._byox_fixture()
        monorepo = self.root / "monorepo"
        source = monorepo / "build-your-own-x"
        shutil.copytree(
            standalone,
            source,
            ignore=shutil.ignore_patterns(".git"),
        )
        _fixture_git(monorepo, "init", "--quiet")
        _fixture_git(monorepo, "config", "user.name", "Learning Factory Tests")
        _fixture_git(
            monorepo,
            "config",
            "user.email",
            "tests@example.invalid",
        )
        _fixture_git(monorepo, "add", ".")
        _fixture_git(monorepo, "commit", "--quiet", "-m", "vendor source")
        vendored_tree = _fixture_git(
            monorepo, "rev-parse", "HEAD:build-your-own-x"
        )
        self.assertEqual(
            _fixture_git(standalone, "rev-parse", f"{pinned_commit}^{{tree}}"),
            vendored_tree,
        )
        manifest_path = monorepo / "SOURCE_PINS.json"

        def write_manifest(
            *,
            schema_version: object = 1,
            upstream_url: str = "git@github.com:example/build-your-own-x.git",
        ) -> None:
            manifest_path.write_text(
                json.dumps(
                    {
                        "schema_version": schema_version,
                        "sources": {
                            "build-your-own-x": {
                                "commit_hash": pinned_commit,
                                "head_ref": "master",
                                "tree_hash": vendored_tree,
                                "upstream_url": upstream_url,
                            }
                        },
                    },
                    sort_keys=True,
                ),
                encoding="utf-8",
            )

        write_manifest()
        _fixture_git(monorepo, "add", "SOURCE_PINS.json")
        _fixture_git(monorepo, "commit", "--quiet", "-m", "lock source")

        adapter = BuildYourOwnXAdapter()
        descriptor = adapter.describe(source)
        batch = adapter.extract(descriptor)

        self.assertEqual([monorepo / ".git"], list(monorepo.rglob(".git")))
        self.assertEqual(pinned_commit, descriptor.commit_hash)
        self.assertEqual(vendored_tree, descriptor.metadata["tree_hash"])
        self.assertEqual(
            "vendored-subtree", descriptor.metadata["repository_layout"]
        )
        self.assertEqual(
            "git@github.com:example/build-your-own-x.git",
            descriptor.upstream_url,
        )
        self.assertEqual("master", descriptor.metadata["head_ref"])
        self.assertEqual(4, len(batch.projects))

        (monorepo / "UNRELATED.txt").write_text(
            "outer repository change\n",
            encoding="utf-8",
        )
        _fixture_git(monorepo, "add", "UNRELATED.txt")
        _fixture_git(monorepo, "commit", "--quiet", "-m", "change outer tree")
        after_outer_change = adapter.describe(source)
        self.assertEqual(descriptor.source_id, after_outer_change.source_id)
        self.assertEqual(descriptor.commit_hash, after_outer_change.commit_hash)
        self.assertEqual(descriptor.upstream_url, after_outer_change.upstream_url)
        self.assertEqual(
            descriptor.metadata["head_ref"],
            after_outer_change.metadata["head_ref"],
        )
        self.assertEqual(
            descriptor.metadata["tree_hash"],
            after_outer_change.metadata["tree_hash"],
        )
        self.assertEqual(batch, adapter.extract(after_outer_change))

        write_manifest(schema_version=True)
        _fixture_git(monorepo, "add", "SOURCE_PINS.json")
        _fixture_git(monorepo, "commit", "--quiet", "-m", "break pin schema")
        with self.assertRaisesRegex(SourceFormatError, "invalid SOURCE_PINS"):
            adapter.describe(source)

        manifest_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "sources": {"build-your-own-x": None},
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        _fixture_git(monorepo, "add", "SOURCE_PINS.json")
        _fixture_git(monorepo, "commit", "--quiet", "-m", "null source pin")
        with self.assertRaisesRegex(SourceFormatError, "invalid source pin"):
            adapter.describe(source)

        malformed_manifests = (
            b"",
            b"\xff",
            b'{"schema_version":1,"schema_version":1,"sources":{}}',
        )
        for index, malformed_manifest in enumerate(malformed_manifests, 1):
            with self.subTest(malformed_manifest=index):
                manifest_path.write_bytes(malformed_manifest)
                _fixture_git(monorepo, "add", "SOURCE_PINS.json")
                _fixture_git(
                    monorepo,
                    "commit",
                    "--quiet",
                    "-m",
                    f"malformed pin {index}",
                )
                with self.assertRaisesRegex(
                    SourceFormatError, "malformed SOURCE_PINS"
                ):
                    adapter.describe(source)

        write_manifest(upstream_url="https://[broken")
        _fixture_git(monorepo, "add", "SOURCE_PINS.json")
        _fixture_git(monorepo, "commit", "--quiet", "-m", "break pin URL")
        with self.assertRaisesRegex(SourceFormatError, "invalid source-pin upstream URL"):
            adapter.describe(source)

        write_manifest()
        _fixture_git(monorepo, "add", "SOURCE_PINS.json")
        _fixture_git(monorepo, "commit", "--quiet", "-m", "restore pin")

        (source / "README.md").write_text(
            "Poisoned uncommitted worktree content.\n",
            encoding="utf-8",
        )
        dirty_descriptor = adapter.describe(source)
        self.assertTrue(dirty_descriptor.metadata["working_tree_dirty"])
        self.assertEqual(batch, adapter.extract(dirty_descriptor))

        _fixture_git(monorepo, "add", "build-your-own-x/README.md")
        _fixture_git(monorepo, "commit", "--quiet", "-m", "drift source")
        self.assertFalse(adapter.detect(source))
        with self.assertRaisesRegex(SourceFormatError, "does not match pinned tree"):
            adapter.describe(source)

    @unittest.skipUnless(BYOX_SOURCE.is_dir(), "local Build-Your-Own-X source is unavailable")
    def test_pinned_local_catalog_has_359_entries_and_stable_categories(self) -> None:
        adapter = BuildYourOwnXAdapter()
        descriptor = adapter.describe(BYOX_SOURCE)
        first = adapter.extract(descriptor)
        second = adapter.extract(descriptor)

        expected_categories = {
            "3D Renderer",
            "AI Model",
            "Augmented Reality",
            "BitTorrent Client",
            "Blockchain / Cryptocurrency",
            "Bot",
            "Command-Line Tool",
            "Database",
            "Distributed Systems",
            "Docker",
            "Emulator / Virtual Machine",
            "Front-end Framework / Library",
            "Game",
            "Git",
            "Memory Allocator",
            "Network Stack",
            "Neural Network",
            "Operating System",
            "Physics Engine",
            "Processor",
            "Programming Language",
            "Regex Engine",
            "Search Engine",
            "Shell",
            "Template Engine",
            "Text Editor",
            "Uncategorized",
            "Visual Recognition System",
            "Voxel Engine",
            "Web Browser",
            "Web Server",
        }
        counts = Counter(project.category for project in first.projects)

        self.assertEqual(BYOX_PINNED_COMMIT, descriptor.commit_hash)
        self.assertEqual("CC0-1.0", descriptor.license)
        self.assertEqual("NOASSERTION", descriptor.metadata["linked_resource_license"])
        self.assertEqual(359, len(first.projects))
        self.assertEqual(expected_categories, set(counts))
        self.assertEqual(31, len(counts))
        self.assertEqual(13, counts["Database"])
        self.assertEqual(19, counts["Operating System"])
        self.assertEqual(62, counts["Uncategorized"])
        self.assertEqual(359, len({project.key for project in first.projects}))
        self.assertEqual(359, len({project.slug for project in first.projects}))
        self.assertEqual(
            [(project.key, project.slug) for project in first.projects],
            [(project.key, project.slug) for project in second.projects],
        )
        self.assertTrue(
            all(
                project.metadata["linked_resource_license"] == "NOASSERTION"
                and project.metadata["provenance"]["source_commit"] == BYOX_PINNED_COMMIT
                for project in first.projects
            )
        )


if __name__ == "__main__":
    unittest.main()
