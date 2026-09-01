from __future__ import annotations

import json
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from learnfactory.backends import BackendResult
from learnfactory.config import FactorySettings
from learnfactory.db import Database
from learnfactory.handlers import HandlerResult, JobHandlers
from learnfactory.jobs import ClaimedJob, JobRepository
from learnfactory.learners import (
    activate_validated_attempt,
    add_knowledge_evidence,
    effective_learner_concepts,
    parse_examiner_evaluation,
    record_validated_attempt,
    seed_students,
)
from learnfactory.publication import PublicationScope
from learnfactory.seeding import seed_initial_jobs
from learnfactory.util import canonical_json, now
from learnfactory.validation import Validator
from learnfactory.worker import run_worker
from learnfactory.workspace import WorkspaceManager


ROOT = Path(__file__).resolve().parents[1]


class LearnerMemoryTests(unittest.TestCase):
    def test_direct_evidence_stores_bounded_weight_used_by_effective_view(self) -> None:
        with tempfile.TemporaryDirectory(prefix="learnfactory-evidence-weight-") as raw:
            warehouse = Path(raw) / "warehouse"
            database = Database(warehouse / "factory.db", ROOT / "migrations")
            database.migrate()
            seed_students(database, warehouse)

            confidence = add_knowledge_evidence(
                database,
                "student-target",
                "bounded-weight",
                "independent observation",
                kind="test",
                source_reference=None,
                weight=7.0,
            )
            with database.connect() as connection:
                stored_weight = connection.execute(
                    """
                    SELECT weight FROM knowledge_evidence
                    WHERE student_id='student-target' AND concept='bounded-weight'
                    """
                ).fetchone()["weight"]
                effective = effective_learner_concepts(
                    connection, "student-target"
                )
            self.assertEqual(1.0, stored_weight)
            self.assertEqual(confidence, effective[0]["confidence"])
            with self.assertRaisesRegex(ValueError, "finite"):
                add_knowledge_evidence(
                    database,
                    "student-target",
                    "invalid-weight",
                    "invalid",
                    kind="test",
                    source_reference=None,
                    weight=float("nan"),
                )

    def test_validated_attempt_is_idempotent_evidence_and_renders_memory(self) -> None:
        with tempfile.TemporaryDirectory(prefix="learnfactory-learner-") as raw:
            warehouse = Path(raw) / "warehouse"
            database = Database(warehouse / "factory.db", ROOT / "migrations")
            database.migrate()
            seed_students(database, warehouse)
            arguments = {
                "student_id": "student-target",
                "task_id": "course-cow-transfer-v2",
                "task_type": "transfer-exercise",
                "attempt_number": 1,
                "start_time": 100.0,
                "end_time": 120.0,
                "result": "PASS",
                "workspace": "/archive/course-cow-transfer-v2",
                "evaluator": "independent deterministic examiner",
                "rubric": {"required_tests": 8},
                "score": 100.0,
                "evaluation_evidence": {"passed": 8, "failed": 0},
                "concepts": [
                    {
                        "concept": "copy-on-write",
                        "description": "Passed an unseen lifecycle transfer suite.",
                        "kind": "transfer-test",
                        "source_reference": "job_course_mit6s081_vertical_v2",
                        "weight": 0.7,
                    },
                    {
                        "concept": "concurrency",
                        "description": "Passed bounded shared-write stress under a global lock.",
                        "kind": "stress-test",
                        "source_reference": "job_course_mit6s081_vertical_v2",
                        "weight": 0.35,
                        "misconceptions": [
                            "A single global lock passing a smoke test does not establish scalable synchronization."
                        ],
                    },
                ],
            }

            first = record_validated_attempt(database, warehouse, **arguments)
            with database.connect() as connection:
                confidence = connection.execute(
                    "SELECT confidence FROM learner_knowledge WHERE student_id='student-target' AND concept='copy-on-write'"
                ).fetchone()["confidence"]
            second = record_validated_attempt(database, warehouse, **arguments)

            self.assertEqual(first, second)
            with database.connect() as connection:
                self.assertEqual(
                    1,
                    connection.execute("SELECT COUNT(*) AS n FROM attempts").fetchone()["n"],
                )
                self.assertEqual(
                    1,
                    connection.execute("SELECT COUNT(*) AS n FROM evaluations").fetchone()["n"],
                )
                self.assertEqual(
                    2,
                    connection.execute("SELECT COUNT(*) AS n FROM knowledge_evidence").fetchone()["n"],
                )
                self.assertEqual(
                    confidence,
                    connection.execute(
                        "SELECT confidence FROM learner_knowledge WHERE student_id='student-target' AND concept='copy-on-write'"
                    ).fetchone()["confidence"],
                )
            memory = warehouse / "learners" / "student-target"
            knowledge = json.loads((memory / "KNOWLEDGE.json").read_text(encoding="utf-8"))
            self.assertEqual(
                ["concurrency", "copy-on-write"],
                [item["concept"] for item in knowledge["concepts"]],
            )
            self.assertIn("global lock", (memory / "MISTAKES.md").read_text(encoding="utf-8"))
            self.assertIn("course-cow-transfer-v2", (memory / "EXPERIENCE.md").read_text(encoding="utf-8"))

    def test_repeated_concept_publication_ignores_invalidated_evidence(self) -> None:
        with tempfile.TemporaryDirectory(prefix="learnfactory-repeated-concept-") as raw:
            root = Path(raw)
            warehouse = root / "warehouse"
            database = Database(warehouse / "factory.db", ROOT / "migrations")
            database.migrate()
            seed_students(database, warehouse)
            manager = WorkspaceManager(warehouse, database)
            manager.initialize()
            jobs = JobRepository(database)
            publication_job = jobs.create(
                "fake",
                "examiner",
                {},
                job_id="job_repeated_concept_publication",
                max_attempts=1,
            )
            first_attempt = record_validated_attempt(
                database,
                warehouse,
                student_id="student-target",
                task_id="repeated-concept-first",
                task_type="test",
                attempt_number=1,
                start_time=10.0,
                end_time=11.0,
                result="PASS",
                workspace="/archive/repeated-concept-first",
                evaluator="first independent evaluator",
                rubric={"version": 1},
                score=90.0,
                evaluation_evidence={"observations": ["superseded evidence"]},
                concepts=[
                    {
                        "concept": "repeated-concept",
                        "description": "superseded evidence",
                        "kind": "test",
                        "source_reference": "first",
                        "weight": 0.8,
                    }
                ],
            )
            with database.transaction(immediate=True) as connection:
                first_evidence = connection.execute(
                    """
                    SELECT evidence_id FROM knowledge_evidence
                    WHERE student_id='student-target'
                      AND concept='repeated-concept'
                    """
                ).fetchone()["evidence_id"]
                connection.execute(
                    """
                    INSERT INTO learner_evidence_invalidations(
                        invalidation_id,evidence_id,attempt_id,source_job_id,
                        reason,invalidated_at
                    ) VALUES (?,?,?,?,?,?)
                    """,
                    (
                        "invalidate_repeated_concept_first",
                        first_evidence,
                        first_attempt,
                        publication_job,
                        "superseded test evidence",
                        12.0,
                    ),
                )

            claim, worker_id, workspace = self._start_job(
                database,
                jobs,
                manager,
                publication_job,
                "repeated-concept-owner",
            )
            (workspace / "result.txt").write_text("validated\n", encoding="utf-8")
            validations = Validator(database).run(
                publication_job,
                workspace,
                [
                    {
                        "type": "handler_evidence",
                        "name": "repeated-concept-validator",
                        "passed": True,
                        "evidence": {"source": "test"},
                    }
                ],
                root / "logs" / publication_job,
                attempt_number=claim.attempt_count,
            )
            self.assertTrue(all(result.passed for result in validations))
            artifact = manager.prepare_archive(
                publication_job,
                claim.attempt_count,
                workspace,
                artifact_type="test",
                semantic_path="tests/repeated-concept",
                metadata={},
            )

            def publish(connection: object) -> None:
                activate_validated_attempt(
                    database,
                    connection,  # type: ignore[arg-type]
                    student_id="student-target",
                    task_id="repeated-concept-second",
                    task_type="test",
                    attempt_number=1,
                    start_time=20.0,
                    end_time=21.0,
                    result="PASS",
                    workspace="/archive/repeated-concept-second",
                    evaluator="second independent evaluator",
                    rubric={"version": 1},
                    score=95.0,
                    evaluation_evidence={"observations": ["current evidence"]},
                    concepts=[
                        {
                            "concept": "repeated-concept",
                            "description": "current evidence",
                            "kind": "test",
                            "source_reference": "second",
                            "weight": 0.4,
                        }
                    ],
                )

            jobs.succeed_with_artifact(
                publication_job,
                "repeated-concept-owner",
                claim.lease_token,
                worker_id,
                artifact,
                on_publish=publish,  # type: ignore[arg-type]
                publication_scope=PublicationScope.LEARNER_EVIDENCE,
            )
            with database.connect() as connection:
                concepts = effective_learner_concepts(
                    connection, "student-target"
                )
                self.assertEqual(
                    1,
                    connection.execute(
                        "SELECT COUNT(*) FROM learner_evidence_invalidations"
                    ).fetchone()[0],
                )
            self.assertEqual("SUCCEEDED", jobs.get(publication_job)["state"])
            self.assertEqual(1, len(concepts))
            self.assertEqual(1, concepts[0]["invalidated_evidence_count"])
            self.assertEqual(["current evidence"], [item["description"] for item in concepts[0]["evidence"]])
            self.assertAlmostEqual(0.55, concepts[0]["confidence"])

    def test_examiner_activation_is_fenced_and_files_render_only_after_commit(self) -> None:
        with tempfile.TemporaryDirectory(prefix="learnfactory-examiner-") as raw:
            root = Path(raw)
            warehouse = root / "warehouse"
            database = Database(warehouse / "factory.db", ROOT / "migrations")
            database.migrate()
            seed_students(database, warehouse)
            manager = WorkspaceManager(warehouse, database)
            manager.initialize()
            jobs = JobRepository(database)

            student_job = jobs.create(
                "fake",
                "student",
                {},
                job_id="job_test_student_attempt",
                max_attempts=1,
            )
            student_claim, student_worker, student_workspace = self._start_job(
                database, jobs, manager, student_job, "student-owner"
            )
            (student_workspace / "submission.md").write_text(
                "lifecycle invariants\n", encoding="utf-8"
            )
            Validator(database).run(
                student_job,
                student_workspace,
                [
                    {
                        "type": "required_paths",
                        "name": "student-output",
                        "paths": ["submission.md"],
                    }
                ],
                root / "logs" / student_job,
                attempt_number=student_claim.attempt_count,
            )
            student_artifact = manager.prepare_archive(
                student_job,
                student_claim.attempt_count,
                student_workspace,
                artifact_type="student-attempt",
                semantic_path="tests/student-attempt",
                metadata={},
            )
            jobs.succeed_with_artifact(
                student_job,
                "student-owner",
                student_claim.lease_token,
                student_worker,
                student_artifact,
            )

            schema = {
                "type": "object",
                "properties": {
                    "result": {"type": "string", "enum": ["PASS", "REVISE", "FAIL"]},
                    "score": {"type": "number", "minimum": 0, "maximum": 100},
                    "evidence": {"type": "array", "items": {"type": "string"}},
                    "transfer_gaps": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["result", "score", "evidence", "transfer_gaps"],
                "additionalProperties": False,
            }
            policy = {
                "schema_version": 1,
                "student_id": "student-target",
                "student_job_id": student_job,
                "student_artifact_type": "student-attempt",
                "task_id": "test-transfer-design",
                "task_type": "transfer-design",
                "attempt_number": 1,
                "evaluator": "independent test examiner",
                "evaluation_path": "evaluation.json",
                "schema_validator": "examiner-structured-evidence",
                "rubric": {"dimensions": ["lifecycle", "concurrency"]},
                "concepts": [
                    {
                        "concept": "resource-lifecycle",
                        "description": "Independent evidence for exact resource lifetime.",
                        "kind": "independent-examiner",
                        "source_reference": "test-rubric-v1",
                        "result_weights": {"PASS": 0.4, "REVISE": 0.1, "FAIL": -0.3},
                    }
                ],
            }
            examiner_payload = {
                "prompt": "Evaluate the prepared submission.",
                "output_schema": schema,
                "validators": [
                    {
                        "type": "required_paths",
                        "name": "examiner-output-files",
                        "paths": ["evaluation.json", "evaluation.md"],
                    },
                    {
                        "type": "json_schema",
                        "name": "examiner-structured-evidence",
                        "path": "evaluation.json",
                        "schema": schema,
                    },
                ],
                "artifact_type": "independent-evaluation",
                "artifact_path": "tests/examiner-evaluation",
                "learner_evidence": policy,
            }
            examiner_job = jobs.create(
                "codex_task",
                "examiner",
                examiner_payload,
                job_id="job_test_independent_examiner",
                dependencies=[student_job],
                max_attempts=1,
            )
            examiner_claim, examiner_worker, examiner_workspace = self._start_job(
                database, jobs, manager, examiner_job, "examiner-owner"
            )
            evaluation = {
                "result": "PASS",
                "score": 88,
                "evidence": [
                    "Submission states an exact final-unmap frame-release invariant."
                ],
                "transfer_gaps": ["No measured contention evidence was provided."],
            }
            (examiner_workspace / "evaluation.json").write_text(
                canonical_json(evaluation) + "\n", encoding="utf-8"
            )
            (examiner_workspace / "evaluation.md").write_text(
                "Evidence-backed review.\n", encoding="utf-8"
            )
            settings = FactorySettings(
                root=ROOT,
                database=database.path,
                warehouse=warehouse,
            )
            with patch(
                "learnfactory.handlers.ExecBackend.start_job",
                return_value=BackendResult(0, "", session_id="examiner-session"),
            ):
                handled = JobHandlers(settings, database, manager).execute(
                    examiner_claim,
                    examiner_workspace,
                    root / "logs" / examiner_job,
                    threading.Event(),
                )
            self.assertIsNotNone(handled.on_publish)
            self.assertIsNotNone(handled.on_commit)
            validations = Validator(database).run(
                examiner_job,
                examiner_workspace,
                handled.validators,
                root / "logs" / examiner_job,
                attempt_number=examiner_claim.attempt_count,
            )
            self.assertTrue(all(result.passed for result in validations))
            examiner_artifact = manager.prepare_archive(
                examiner_job,
                examiner_claim.attempt_count,
                examiner_workspace,
                artifact_type=handled.artifact_type,
                semantic_path=handled.semantic_path,
                metadata=handled.metadata,
            )
            publish = handled.on_publish
            assert publish is not None

            def fail_after_activation(connection: sqlite3.Connection) -> None:
                publish(connection)
                self.assertEqual(
                    1,
                    connection.execute("SELECT COUNT(*) FROM attempts").fetchone()[0],
                )
                raise RuntimeError("injected publication failure")

            with self.assertRaisesRegex(RuntimeError, "injected publication failure"):
                jobs.succeed_with_artifact(
                    examiner_job,
                    "examiner-owner",
                    examiner_claim.lease_token,
                    examiner_worker,
                    examiner_artifact,
                    on_publish=fail_after_activation,
                    publication_scope=handled.publication_scope,
                )
            with database.connect() as connection:
                self.assertEqual(
                    (0, 0, 0, 0, "RUNNING"),
                    (
                        connection.execute("SELECT COUNT(*) FROM attempts").fetchone()[0],
                        connection.execute("SELECT COUNT(*) FROM evaluations").fetchone()[0],
                        connection.execute("SELECT COUNT(*) FROM learner_knowledge").fetchone()[0],
                        connection.execute(
                            "SELECT COUNT(*) FROM artifacts WHERE job_id=?", (examiner_job,)
                        ).fetchone()[0],
                        connection.execute(
                            "SELECT state FROM jobs WHERE job_id=?", (examiner_job,)
                        ).fetchone()[0],
                    ),
                )
            memory_path = warehouse / "learners" / "student-target" / "KNOWLEDGE.json"
            self.assertEqual([], json.loads(memory_path.read_text())["concepts"])

            jobs.succeed_with_artifact(
                examiner_job,
                "examiner-owner",
                examiner_claim.lease_token,
                examiner_worker,
                examiner_artifact,
                on_publish=publish,
                publication_scope=handled.publication_scope,
            )
            with database.connect() as connection:
                self.assertEqual(
                    (1, 1, 1, 1, "SUCCEEDED"),
                    (
                        connection.execute("SELECT COUNT(*) FROM attempts").fetchone()[0],
                        connection.execute("SELECT COUNT(*) FROM evaluations").fetchone()[0],
                        connection.execute("SELECT COUNT(*) FROM learner_knowledge").fetchone()[0],
                        connection.execute(
                            "SELECT COUNT(*) FROM artifacts WHERE job_id=?", (examiner_job,)
                        ).fetchone()[0],
                        connection.execute(
                            "SELECT state FROM jobs WHERE job_id=?", (examiner_job,)
                        ).fetchone()[0],
                    ),
                )
            self.assertEqual(
                [],
                json.loads(memory_path.read_text(encoding="utf-8"))["concepts"],
                "derived files must not be rendered by the in-transaction callback",
            )
            assert handled.on_commit is not None
            handled.on_commit()
            rendered = json.loads(memory_path.read_text(encoding="utf-8"))
            self.assertEqual("resource-lifecycle", rendered["concepts"][0]["concept"])
            self.assertIn(
                "final-unmap",
                rendered["concepts"][0]["evidence"][0]["description"],
            )

    def test_examiner_evaluation_rejects_self_assertion_shapes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="learnfactory-evaluation-") as raw:
            path = Path(raw) / "evaluation.json"
            for invalid in (
                {"result": "PASS", "score": True, "evidence": ["claim"], "transfer_gaps": []},
                {"result": "PASS", "score": 100, "evidence": [], "transfer_gaps": []},
                {
                    "result": "PASS",
                    "score": 100,
                    "evidence": ["claim"],
                    "transfer_gaps": [],
                    "concept": "worker-selected-concept",
                },
            ):
                path.write_text(canonical_json(invalid) + "\n", encoding="utf-8")
                with self.assertRaises(ValueError):
                    parse_examiner_evaluation(path)

    def test_worker_runs_derived_sync_only_after_publication_commits(self) -> None:
        with tempfile.TemporaryDirectory(prefix="learnfactory-post-commit-") as raw:
            root = Path(raw)
            database_path = root / "factory.db"
            warehouse = root / "warehouse"
            config_path = root / "factory.toml"
            config_path.write_text(
                "\n".join(
                    [
                        "[factory]",
                        f'database = "{database_path}"',
                        f'warehouse = "{warehouse}"',
                        "lease_seconds = 30",
                        "heartbeat_seconds = 0.05",
                        "[backend]",
                        'command = "codex"',
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            database = Database(database_path, ROOT / "migrations")
            database.migrate()
            jobs = JobRepository(database)
            job_id = jobs.create(
                "fake", "test", {}, job_id="job_test_post_commit_order", max_attempts=1
            )
            jobs.promote_eligible()
            claim = jobs.claim_next("post-commit-owner", 30, max_total=1, type_limits={})
            assert claim is not None
            observations: list[tuple[str, int, str]] = []

            def publish(connection: sqlite3.Connection) -> None:
                connection.execute(
                    """
                    INSERT INTO events(timestamp,actor,type,payload_json)
                    VALUES (?,'test-post-commit','TEST_POST_COMMIT','true')
                    """,
                    (now(),),
                )

            def after_commit() -> None:
                with database.connect() as connection:
                    state = connection.execute(
                        "SELECT state FROM jobs WHERE job_id=?", (job_id,)
                    ).fetchone()[0]
                    artifact_count = connection.execute(
                        "SELECT COUNT(*) FROM artifacts WHERE job_id=?", (job_id,)
                    ).fetchone()[0]
                    marker = connection.execute(
                        "SELECT payload_json FROM events WHERE actor='test-post-commit'"
                    ).fetchone()[0]
                observations.append((state, artifact_count, marker))

            handled = HandlerResult(
                evidence={},
                validators=[
                    {
                        "type": "handler_evidence",
                        "name": "deterministic-output",
                        "passed": True,
                        "evidence": {"source": "test harness"},
                    }
                ],
                artifact_type="test-output",
                semantic_path="tests/post-commit-order",
                on_publish=publish,
                publication_scope=PublicationScope.SOURCE_INGESTION,
                on_commit=after_commit,
            )
            with patch("learnfactory.worker.JobHandlers.execute", return_value=handled):
                exit_code = run_worker(
                    job_id, "post-commit-owner", claim.lease_token, config_path
                )

            self.assertEqual(0, exit_code)
            self.assertEqual([("SUCCEEDED", 1, "true")], observations)

    def test_v2_seed_contains_explicit_examiner_learner_policy(self) -> None:
        with tempfile.TemporaryDirectory(prefix="learnfactory-seed-policy-") as raw:
            database = Database(Path(raw) / "factory.db", ROOT / "migrations")
            database.migrate()
            warehouse = Path(raw) / "warehouse"
            seed_students(database, warehouse)
            with database.transaction(immediate=True) as connection:
                connection.execute(
                    """
                    INSERT INTO sources(source_id,type,name,path,upstream_url,commit_hash,license,ingested_at)
                    VALUES ('source_course','csdiy','CSDIY','/public/csdiy','https://example.test/csdiy','abc','MIT',?)
                    """,
                    (now(),),
                )
                connection.execute(
                    """
                    INSERT INTO courses(
                        course_id,source_id,slug,institution,title,topic,prerequisites_json,source_metadata_json
                    ) VALUES ('course_mit','source_course','mit-6-s081','MIT','MIT 6.S081','Operating Systems','[]','{}')
                    """
                )
                connection.execute(
                    """
                    INSERT INTO sources(source_id,type,name,path,upstream_url,commit_hash,license,ingested_at)
                    VALUES ('source_byox','build-your-own-x','Build Your Own X','/public/byox','https://example.test/byox','def','CC0-1.0',?)
                    """,
                    (now(),),
                )
                connection.execute(
                    """
                    INSERT INTO build_projects(
                        project_id,source_id,slug,title,category,implementation_language,
                        upstream_reference,concepts_json,priority_tier
                    ) VALUES ('project_db','source_byox','dbdb','DBDB','Database','Python',
                              'https://example.test/dbdb','[]',1)
                    """
                )
            jobs = JobRepository(database)
            seeded = seed_initial_jobs(database, jobs)
            examiner = jobs.get(seeded["examiner_revision"])
            assert examiner is not None
            policy = examiner["payload"]["learner_evidence"]
            self.assertEqual("student-target", policy["student_id"])
            self.assertEqual(seeded["student_revision"], policy["student_job_id"])
            self.assertEqual(
                "examiner-structured-evidence", policy["schema_validator"]
            )
            self.assertEqual(
                [
                    "concurrency-reasoning",
                    "copy-on-write",
                    "failure-oriented-testing",
                    "resource-lifecycle",
                ],
                sorted(item["concept"] for item in policy["concepts"]),
            )
            with database.transaction(immediate=True) as connection:
                stale_payload = json.loads(
                    connection.execute(
                        "SELECT payload_json FROM jobs WHERE job_id=?",
                        (seeded["examiner_revision"],),
                    ).fetchone()[0]
                )
                stale_payload.pop("learner_evidence")
                connection.execute(
                    "UPDATE jobs SET payload_json=? WHERE job_id=?",
                    (
                        canonical_json(stale_payload),
                        seeded["examiner_revision"],
                    ),
                )
            seed_initial_jobs(database, jobs)
            refreshed = jobs.get(seeded["examiner_revision"])
            assert refreshed is not None
            self.assertEqual(
                "student-target",
                refreshed["payload"]["learner_evidence"]["student_id"],
            )
            with database.connect() as connection:
                self.assertEqual(
                    1,
                    connection.execute(
                        """
                        SELECT COUNT(*) FROM events
                        WHERE job_id=? AND type='SEEDED_JOB_PAYLOAD_UPGRADED'
                        """,
                        (seeded["examiner_revision"],),
                    ).fetchone()[0],
                )
            attempted_payload = dict(refreshed["payload"])
            attempted_payload.pop("learner_evidence")
            with database.transaction(immediate=True) as connection:
                connection.execute(
                    """
                    UPDATE jobs SET state='BLOCKED',attempt_count=1,payload_json=?
                    WHERE job_id=?
                    """,
                    (
                        canonical_json(attempted_payload),
                        seeded["examiner_revision"],
                    ),
                )
            seed_initial_jobs(database, jobs)
            immutable = jobs.get(seeded["examiner_revision"])
            assert immutable is not None
            self.assertNotIn("learner_evidence", immutable["payload"])
            with database.connect() as connection:
                self.assertEqual(
                    1,
                    connection.execute(
                        """
                        SELECT COUNT(*) FROM events
                        WHERE job_id=? AND type='SEEDED_JOB_PAYLOAD_UPGRADED'
                        """,
                        (seeded["examiner_revision"],),
                    ).fetchone()[0],
                )

    @staticmethod
    def _start_job(
        database: Database,
        jobs: JobRepository,
        manager: WorkspaceManager,
        job_id: str,
        owner: str,
    ) -> tuple[ClaimedJob, str, Path]:
        jobs.promote_eligible()
        claim = jobs.claim_next(owner, 60, max_total=1, type_limits={})
        assert claim is not None and claim.job_id == job_id
        workspace = manager.allocate(job_id, claim.attempt_count)
        worker_id = f"worker_{job_id}"
        timestamp = now()
        with database.transaction(immediate=True) as connection:
            connection.execute(
                """
                INSERT INTO workers(
                    worker_id,type,process_id,workspace,state,started_at,last_activity,current_job
                ) VALUES (?,?,?,?,?,?,?,?)
                """,
                (
                    worker_id,
                    claim.worker_type,
                    1,
                    str(workspace),
                    "STARTING",
                    timestamp,
                    timestamp,
                    job_id,
                ),
            )
        jobs.start(
            job_id,
            owner,
            claim.lease_token,
            worker_id,
            str(workspace),
            lease_seconds=30,
        )
        return claim, worker_id, workspace


if __name__ == "__main__":
    unittest.main()
