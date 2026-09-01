from __future__ import annotations

import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

from learnfactory.config import FactorySettings
from learnfactory.course_kickoff_revisions import KICKOFF_REVISION_POLICY_KIND
from learnfactory.course_progression import seed_next_csdiy_course_batches
from learnfactory.db import Database
from learnfactory.handlers import (
    HandlerFailure,
    JobHandlers,
    _enforce_kickoff_revision_backend,
)
from learnfactory.jobs import ClaimedJob, JobRepository
from learnfactory.learners import seed_students
from learnfactory.reporting import status_snapshot
from learnfactory.seeding import (
    CODEX_BACKEND_GATE_JOB_ID,
    seed_all_csdiy_course_cohorts,
    seed_codex_backend_gate,
)
from learnfactory.util import canonical_json, file_sha256, tree_sha256
from learnfactory.workspace import WorkspaceError, WorkspaceManager
from tests.submission_support import insert_submission_binding_validations


ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "migrations"


class KickoffRevisionTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="learnfactory-kickoff-revision-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.warehouse = self.root / "warehouse"
        self.database = Database(self.root / "factory.db", MIGRATIONS)
        self.database.migrate()
        self.jobs = JobRepository(self.database)
        seed_students(self.database, self.warehouse)
        self.course_id = "course_kickoff_revision_test"
        self._insert_course()
        seed_codex_backend_gate(self.jobs)
        cohort = seed_all_csdiy_course_cohorts(self.database, self.jobs)["cohorts"][
            self.course_id
        ]
        self.kickoff = {
            role: cohort[role] for role in ("preparation", "student", "examiner")
        }

    def _insert_course(self) -> None:
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                """
                INSERT INTO sources(
                    source_id,type,name,path,upstream_url,commit_hash,license,
                    ingested_at,metadata_json,is_active
                ) VALUES (?,?,?,?,?,?,?,?,?,1)
                """,
                (
                    "source_csdiy",
                    "course_catalog",
                    "CSDIY",
                    "/public/csdiy",
                    "https://example.test/csdiy",
                    "kickoff-course-commit-1",
                    "CC-BY-SA-4.0",
                    1.0,
                    canonical_json({"adapter": "csdiy"}),
                ),
            )
            connection.execute(
                """
                INSERT INTO courses(
                    course_id,source_id,slug,institution,title,topic,description,
                    prerequisites_json,estimated_human_hours,difficulty,
                    source_metadata_json,status
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    self.course_id,
                    "source_csdiy",
                    "kickoff-revision-test",
                    "Example University",
                    "Kickoff Revision Systems",
                    "systems",
                    "A course used to test bounded kickoff revisions.",
                    "[]",
                    80.0,
                    7.0,
                    canonical_json({"resource_urls": ["https://example.test/course"]}),
                    "DISCOVERED",
                ),
            )
            connection.execute(
                """
                INSERT INTO course_units(
                    unit_id,course_id,type,unit_order,title,dependencies_json,
                    source_reference,metadata_json
                ) VALUES (?,?,?,?,?,?,?,?)
                """,
                (
                    "unit_kickoff_followup",
                    self.course_id,
                    "lab",
                    10,
                    "Lifecycle lab",
                    "[]",
                    "courses/systems.md#lab",
                    canonical_json(
                        {"official_course_unit": True, "availability": "public-link-recorded"}
                    ),
                ),
            )

    def _complete(
        self,
        job_id: str,
        artifact_type: str,
        files: dict[str, str],
        *,
        evaluation_result: str = "PASS",
    ) -> None:
        self.jobs.promote_eligible()
        job = self.jobs.get(job_id)
        assert job is not None
        self.assertEqual("READY", job["state"], job_id)
        artifact_path = self.warehouse / "artifacts" / "fixtures" / job_id
        artifact_path.mkdir(parents=True)
        for relative, content in files.items():
            target = artifact_path / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        with self.database.transaction(immediate=True) as connection:
            changed = connection.execute(
                """
                UPDATE jobs
                SET state='CLAIMED',owner='test-owner',lease_token='test-lease',
                    lease_expires_at=10000,heartbeat_at=100,attempt_count=1,started_at=100
                WHERE job_id=? AND state='READY'
                """,
                (job_id,),
            )
            self.assertEqual(1, changed.rowcount)
            connection.execute(
                "UPDATE jobs SET state='RUNNING' WHERE job_id=? AND state='CLAIMED'",
                (job_id,),
            )
            connection.execute(
                """
                UPDATE jobs
                SET state='SUCCEEDED',owner=NULL,lease_token=NULL,lease_expires_at=NULL,
                    heartbeat_at=101,finished_at=101
                WHERE job_id=? AND state='RUNNING'
                """,
                (job_id,),
            )
            connection.execute(
                """
                INSERT INTO artifacts(
                    artifact_id,job_id,type,path,checksum,metadata_json,created_at,
                    validation_status,attempt_number,checksum_algorithm,integrity_status
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    f"artifact_{job_id}",
                    job_id,
                    artifact_type,
                    str(artifact_path),
                    tree_sha256(artifact_path),
                    "{}",
                    101.0,
                    "GENERATED",
                    1,
                    "tree-sha256-v2",
                    "VERIFIED_V2",
                ),
            )
            if artifact_type == "independent-course-evaluation":
                policy = job["payload"]["learner_evidence"]
                submission_binding = insert_submission_binding_validations(
                    connection,
                    examiner_job_id=job_id,
                    examiner_attempt=1,
                    payload=job["payload"],
                )
                attempt_id = f"attempt_{job_id}"
                student_attempt = connection.execute(
                    "SELECT attempt_count FROM jobs WHERE job_id=?",
                    (policy["student_job_id"],),
                ).fetchone()["attempt_count"]
                evaluation_path = artifact_path / "evaluation.json"
                connection.execute(
                    """
                    INSERT INTO attempts(
                        attempt_id,student_id,task_id,task_type,attempt_number,
                        start_time,end_time,result,workspace
                    ) VALUES (?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        attempt_id,
                        policy["student_id"],
                        policy["task_id"],
                        policy["task_type"],
                        policy["attempt_number"],
                        100.0,
                        101.0,
                        evaluation_result,
                        str(artifact_path),
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO evaluations(
                        evaluation_id,attempt_id,evaluator,rubric_json,result,score,
                        evidence_json,created_at
                    ) VALUES (?,?,?,?,?,?,?,?)
                    """,
                    (
                        f"evaluation_{job_id}",
                        attempt_id,
                        policy["evaluator"],
                        canonical_json(policy["rubric"]),
                        evaluation_result,
                        90.0 if evaluation_result == "PASS" else 45.0,
                        canonical_json(
                            {
                                "observations": ["test-controlled evidence"],
                                "transfer_gaps": [],
                                "evaluation_sha256": (
                                    file_sha256(evaluation_path)
                                    if evaluation_path.is_file()
                                    else "0" * 64
                                ),
                                "examiner_job_id": job_id,
                                "examiner_attempt": 1,
                                "student_job_id": policy["student_job_id"],
                                "student_attempt": student_attempt,
                                "schema_validator": policy["schema_validator"],
                                "schema_validation_evidence": {"status": "PASS"},
                                **(
                                    {
                                        "student_submission_binding":
                                            submission_binding
                                    }
                                    if submission_binding is not None
                                    else {}
                                ),
                            }
                        ),
                        101.0,
                    ),
                )

    def _complete_initial(self, evaluation_result: str = "REVISE") -> None:
        self._complete(
            CODEX_BACKEND_GATE_JOB_ID,
            "backend-capability-gate",
            {"BACKEND_READY.txt": "CODEX_BACKEND_READY_V1\n"},
        )
        self._complete(
            self.kickoff["preparation"],
            "course-preparation",
            {
                "COURSE_MANIFEST.json": "{}\n",
                "UNIT_GRAPH.json": "{}\n",
                "MATERIAL_AVAILABILITY.json": "{}\n",
                "student_safe/COURSE_BRIEF.md": "learner brief\n",
                "student_safe/STUDY_TASK.md": "learner task\n",
                "student_safe/COMPREHENSION.md": "learner questions\n",
                "examiner_only/RUBRIC.md": "withheld rubric\n",
            },
        )
        self._complete(
            self.kickoff["student"],
            "student-course-attempt",
            {
                "student_work/notes.md": "first notes\n",
                "student_work/submission.md": "first submission\n",
                "student_work/debugging-log.md": "first debugging\n",
            },
        )
        self._complete(
            self.kickoff["examiner"],
            "independent-course-evaluation",
            {
                "evaluation.json": canonical_json(
                    {
                        "result": evaluation_result,
                        "score": 45,
                        "evidence": ["bounded kickoff gap"],
                        "transfer_gaps": [],
                    }
                ),
                "feedback.md": "Address the bounded kickoff gap.\n",
            },
            evaluation_result=evaluation_result,
        )

    def _seed_first_revision(self, *, max_revisions: int = 2) -> dict[str, object]:
        self._complete_initial()
        result = seed_next_csdiy_course_batches(
            self.database, self.jobs, max_revisions=max_revisions
        )
        return result["courses"][self.course_id]

    def _complete_revision(
        self, revision: dict[str, object], *, evaluation_result: str
    ) -> None:
        jobs = revision["jobs"]
        assert isinstance(jobs, dict)
        self._complete(
            str(jobs["student_revision"]),
            "student-course-attempt",
            {
                "student_work/notes.md": "revised notes\n",
                "student_work/submission.md": "revised submission\n",
                "student_work/debugging-log.md": "revised debugging\n",
            },
        )
        self._complete(
            str(jobs["examiner_revision"]),
            "independent-course-evaluation",
            {
                "evaluation.json": canonical_json(
                    {
                        "result": evaluation_result,
                        "score": 88 if evaluation_result == "PASS" else 35,
                        "evidence": ["revision externally evaluated"],
                        "transfer_gaps": [],
                    }
                ),
                "feedback.md": "Independent revision feedback.\n",
            },
            evaluation_result=evaluation_result,
        )

    def _dependencies(self, job_id: str) -> set[str]:
        with self.database.connect() as connection:
            return {
                str(row["depends_on_job_id"])
                for row in connection.execute(
                    "SELECT depends_on_job_id FROM job_dependencies WHERE job_id=?",
                    (job_id,),
                )
            }

    def test_nonpassing_kickoff_seeds_exact_isolated_revision_graph(self) -> None:
        course = self._seed_first_revision()
        self.assertEqual("KICKOFF_REVISION_GRAPH_SEEDED", course["status"])
        self.assertEqual(2, course["attempt_number"])
        self.assertEqual("NOT_CLAIMED", course["course_completion"])
        graph = course["jobs"]
        assert isinstance(graph, dict)
        student = self.jobs.get(str(graph["student_revision"]))
        examiner = self.jobs.get(str(graph["examiner_revision"]))
        assert student is not None and examiner is not None
        for job in (student, examiner):
            self.assertEqual("gpt-5.6-sol", job["model"])
            self.assertEqual("ultra", job["reasoning_effort"])
            self.assertEqual(
                {"name": "exec", "permission_profile": "factory-isolated"},
                job["payload"]["required_backend"],
            )
            self.assertEqual(
                KICKOFF_REVISION_POLICY_KIND,
                job["payload"]["seed_policy"]["kind"],
            )
            self.assertEqual(2, job["payload"]["seed_policy"]["attempt_number"])
        examiner_inputs = [
            item
            for item in student["payload"]["inputs_from_dependencies"]
            if item["job_id"] == self.kickoff["examiner"]
        ]
        self.assertEqual(["feedback.md"], [item["subpath"] for item in examiner_inputs])
        for item in student["payload"]["inputs_from_dependencies"]:
            self.assertIn("artifact_id", item)
            self.assertIn("artifact_checksum", item)
            self.assertIn("artifact_attempt", item)
            self.assertEqual("tree-sha256-v2", item["checksum_algorithm"])
            self.assertNotIn("RUBRIC", item["subpath"].upper())
            self.assertNotIn("NOVEL", item["subpath"].upper())
            self.assertNotIn("REFERENCE", item["subpath"].upper())
        self.assertEqual(
            {
                CODEX_BACKEND_GATE_JOB_ID,
                self.kickoff["preparation"],
                self.kickoff["student"],
                self.kickoff["examiner"],
            },
            self._dependencies(str(graph["student_revision"])),
        )
        repeated = seed_next_csdiy_course_batches(self.database, self.jobs)["courses"][
            self.course_id
        ]
        self.assertEqual("WAITING_FOR_KICKOFF_REVISION_PIPELINE", repeated["status"])

    def test_revision_runtime_fails_closed_without_hardened_backend(self) -> None:
        course = self._seed_first_revision()
        graph = course["jobs"]
        assert isinstance(graph, dict)
        student = self.jobs.get(str(graph["student_revision"]))
        assert student is not None
        claimed = ClaimedJob(
            job_id=str(student["job_id"]),
            type=str(student["type"]),
            worker_type=str(student["worker_type"]),
            payload=student["payload"],
            attempt_count=1,
            workspace=None,
            model=student["model"],
            reasoning_effort=student["reasoning_effort"],
            lease_token="test-lease",
        )
        settings = FactorySettings(
            root=ROOT,
            database=self.database.path,
            warehouse=self.warehouse,
        )
        _enforce_kickoff_revision_backend(claimed, settings)
        unsafe = replace(
            settings,
            backend=replace(
                settings.backend,
                permission_profile="danger-full-access",
            ),
        )
        with self.assertRaisesRegex(HandlerFailure, "factory-isolated"):
            _enforce_kickoff_revision_backend(claimed, unsafe)

    def test_revision_staging_rejects_hidden_material_and_binding_tamper(self) -> None:
        course = self._seed_first_revision()
        graph = course["jobs"]
        assert isinstance(graph, dict)
        student_id = str(graph["student_revision"])
        self.jobs.promote_eligible()
        claim = self.jobs.claim_next(
            "kickoff-staging-test",
            30,
            max_total=1,
            type_limits={"student": 1},
        )
        assert claim is not None
        self.assertEqual(student_id, claim.job_id)
        manager = WorkspaceManager(self.warehouse, self.database)
        manager.initialize()
        settings = FactorySettings(
            root=ROOT,
            database=self.database.path,
            warehouse=self.warehouse,
        )
        handlers = JobHandlers(settings, self.database, manager)
        workspace = manager.allocate(student_id, claim.attempt_count)
        integrity, _ = handlers._stage_declared_inputs(claim, workspace)
        self.assertEqual(
            "first submission\n",
            (workspace / "PRIOR_ATTEMPT/submission.md").read_text(encoding="utf-8"),
        )
        self.assertEqual(
            "Address the bounded kickoff gap.\n",
            (workspace / "EXAMINER_FEEDBACK/feedback.md").read_text(encoding="utf-8"),
        )
        self.assertFalse((workspace / "RUBRIC.md").exists())
        self.assertFalse((workspace / "evaluation.json").exists())
        self.assertNotIn(
            "withheld rubric",
            "\n".join(
                path.read_text(encoding="utf-8")
                for path in workspace.rglob("*")
                if path.is_file()
            ),
        )
        self.assertEqual(
            {"LEARNER_MATERIAL", "PRIOR_ATTEMPT", "EXAMINER_FEEDBACK"},
            {record["path"].split("/", 1)[0] for record in integrity},
        )

        preparation = self.jobs.get(self.kickoff["preparation"])
        assert preparation is not None
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM artifacts WHERE job_id=?",
                (self.kickoff["preparation"],),
            ).fetchone()
        assert row is not None
        malicious_payload = dict(claim.payload)
        malicious_payload["inputs_from_dependencies"] = [
            {
                "job_id": self.kickoff["preparation"],
                "subpath": "examiner_only/RUBRIC.md",
                "destination": "RUBRIC.md",
                "artifact_type": "course-preparation",
                "artifact_id": row["artifact_id"],
                "artifact_checksum": row["checksum"],
                "artifact_attempt": row["attempt_number"],
                "checksum_algorithm": row["checksum_algorithm"],
            },
            *claim.payload["inputs_from_dependencies"],
        ]
        malicious = replace(claim, payload=malicious_payload)
        with self.assertRaisesRegex(WorkspaceError, "under student_safe"):
            handlers._stage_declared_inputs(
                malicious, manager.allocate(student_id, claim.attempt_count + 1)
            )

        tampered_payload = dict(claim.payload)
        tampered_inputs = [dict(item) for item in claim.payload["inputs_from_dependencies"]]
        tampered_inputs[-1]["artifact_checksum"] = "0" * 64
        tampered_payload["inputs_from_dependencies"] = tampered_inputs
        tampered = replace(claim, payload=tampered_payload)
        with self.assertRaisesRegex(HandlerFailure, "artifact_checksum mismatch"):
            handlers._stage_declared_inputs(
                tampered, manager.allocate(student_id, claim.attempt_count + 2)
            )

    def test_passing_revision_unlocks_progression_with_exact_predecessor(self) -> None:
        revision = self._seed_first_revision()
        self._complete_revision(revision, evaluation_result="PASS")
        result = seed_next_csdiy_course_batches(self.database, self.jobs)
        course = result["courses"][self.course_id]
        self.assertEqual("BOUNDED_BATCH_GRAPH_SEEDED", course["status"])
        revision_jobs = revision["jobs"]
        assert isinstance(revision_jobs, dict)
        materializer_id = str(course["jobs"]["materializer"])
        self.assertIn(
            str(revision_jobs["examiner_revision"]),
            self._dependencies(materializer_id),
        )
        materializer = self.jobs.get(materializer_id)
        assert materializer is not None
        predecessor = materializer["payload"]["batch_snapshot"]["predecessor_examiner"]
        self.assertEqual(str(revision_jobs["examiner_revision"]), predecessor["job_id"])
        with self.database.connect() as connection:
            artifact = connection.execute(
                "SELECT * FROM artifacts WHERE job_id=?",
                (str(revision_jobs["examiner_revision"]),),
            ).fetchone()
        assert artifact is not None
        self.assertEqual(artifact["artifact_id"], predecessor["artifact_id"])
        self.assertEqual(artifact["checksum"], predecessor["artifact_checksum"])
        self.assertEqual(artifact["attempt_number"], predecessor["artifact_attempt"])

    def test_revision_limit_is_durable_idempotent_and_raiseable(self) -> None:
        revision = self._seed_first_revision(max_revisions=1)
        self._complete_revision(revision, evaluation_result="FAIL")
        blocked = seed_next_csdiy_course_batches(
            self.database, self.jobs, max_revisions=1
        )["courses"][self.course_id]
        self.assertEqual("BLOCKED_KICKOFF_REVISION_LIMIT_EXHAUSTED", blocked["status"])
        self.assertEqual("BLOCKED", blocked["progression_state"])
        self.assertEqual("NOT_CLAIMED", blocked["course_completion"])
        self.assertTrue(blocked["block_recorded"])
        repeated = seed_next_csdiy_course_batches(
            self.database, self.jobs, max_revisions=1
        )["courses"][self.course_id]
        self.assertFalse(repeated["block_recorded"])
        with self.database.connect() as connection:
            blocks = connection.execute(
                """
                SELECT COUNT(*) AS n FROM course_progression_revision_blocks
                WHERE batch_id LIKE 'csdiy-kickoff-v2-%'
                """
            ).fetchone()["n"]
            events = connection.execute(
                "SELECT COUNT(*) AS n FROM events WHERE type='COURSE_KICKOFF_REVISION_BLOCKED'"
            ).fetchone()["n"]
        self.assertEqual(1, blocks)
        self.assertEqual(1, events)
        coverage = status_snapshot(self.database)["metrics"]["scaleout_coverage"][
            "csdiy"
        ]
        self.assertEqual(0, coverage["succeeded_cohorts"])
        self.assertEqual(1, coverage["examiner_outcomes"]["FAIL"])
        self.assertEqual(0, coverage["invalid_kickoff_revision_chains"])
        raised = seed_next_csdiy_course_batches(
            self.database, self.jobs, max_revisions=2
        )["courses"][self.course_id]
        self.assertEqual("KICKOFF_REVISION_GRAPH_SEEDED", raised["status"])
        self.assertEqual(3, raised["attempt_number"])

    def test_partial_graph_is_repaired_without_rewriting_student_job(self) -> None:
        revision = self._seed_first_revision()
        graph = revision["jobs"]
        assert isinstance(graph, dict)
        examiner_id = str(graph["examiner_revision"])
        student_before = self.jobs.get(str(graph["student_revision"]))
        with self.database.transaction(immediate=True) as connection:
            connection.execute("DELETE FROM events WHERE job_id=?", (examiner_id,))
            connection.execute("DELETE FROM jobs WHERE job_id=?", (examiner_id,))
        repaired = seed_next_csdiy_course_batches(self.database, self.jobs)["courses"][
            self.course_id
        ]
        self.assertEqual("KICKOFF_PARTIAL_REVISION_GRAPH_REPAIRED", repaired["status"])
        self.assertEqual(1, repaired["created_jobs"])
        self.assertEqual(examiner_id, repaired["jobs"]["examiner_revision"])
        self.assertEqual(student_before, self.jobs.get(str(graph["student_revision"])))

    def test_concurrent_refillers_create_one_revision_pair(self) -> None:
        self._complete_initial()

        def seed() -> dict[str, object]:
            return seed_next_csdiy_course_batches(
                self.database, self.jobs, max_revisions=2
            )["courses"][self.course_id]

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = [future.result(timeout=20) for future in [pool.submit(seed), pool.submit(seed)]]
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT job_id,payload_json FROM jobs ORDER BY job_id"
            ).fetchall()
        revision_rows = [
            row
            for row in rows
            if json.loads(row["payload_json"]).get("seed_policy", {}).get("kind")
            == KICKOFF_REVISION_POLICY_KIND
        ]
        self.assertEqual(2, len(revision_rows))
        self.assertEqual(
            {"student_revision", "examiner_revision"},
            {
                json.loads(row["payload_json"])["seed_policy"]["role"]
                for row in revision_rows
            },
        )
        self.assertEqual(2, sum(int(result["created_jobs"]) for result in results))

    def test_tampered_revision_snapshot_fails_closed(self) -> None:
        revision = self._seed_first_revision()
        graph = revision["jobs"]
        assert isinstance(graph, dict)
        student_id = str(graph["student_revision"])
        student = self.jobs.get(student_id)
        assert student is not None
        payload = student["payload"]
        payload["revision_snapshot"]["revision_snapshot_sha256"] = "0" * 64
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                "UPDATE jobs SET payload_json=? WHERE job_id=?",
                (canonical_json(payload), student_id),
            )
        with self.assertRaisesRegex(RuntimeError, "conflicting CSDIY kickoff revision snapshots"):
            seed_next_csdiy_course_batches(self.database, self.jobs)

    def test_examiner_result_must_match_exact_attempt(self) -> None:
        revision = self._seed_first_revision()
        self._complete_revision(revision, evaluation_result="PASS")
        graph = revision["jobs"]
        assert isinstance(graph, dict)
        examiner_id = str(graph["examiner_revision"])
        with self.database.transaction(immediate=True) as connection:
            row = connection.execute(
                """
                SELECT e.evaluation_id,e.evidence_json
                FROM evaluations e JOIN attempts a ON a.attempt_id=e.attempt_id
                WHERE a.task_id=? AND a.attempt_number=2
                """,
                (f"{self.course_id}-kickoff-examiner-v2",),
            ).fetchone()
            evidence = json.loads(row["evidence_json"])
            evidence["examiner_attempt"] = 999
            connection.execute(
                "UPDATE evaluations SET evidence_json=? WHERE evaluation_id=?",
                (canonical_json(evidence), row["evaluation_id"]),
            )
        course = seed_next_csdiy_course_batches(self.database, self.jobs)["courses"][
            self.course_id
        ]
        self.assertEqual("KICKOFF_REVISION_EVIDENCE_INVALID", course["status"])
        self.assertIn("attempt-bound", course["reason"])
        coverage = status_snapshot(self.database)["metrics"]["scaleout_coverage"][
            "csdiy"
        ]
        self.assertEqual(0, coverage["succeeded_cohorts"])
        self.assertEqual(1, coverage["invalid_kickoff_revision_chains"])

    def test_conflicting_same_attempt_evidence_cannot_unlock_progression(self) -> None:
        revision = self._seed_first_revision()
        self._complete_revision(revision, evaluation_result="FAIL")
        graph = revision["jobs"]
        assert isinstance(graph, dict)
        examiner_id = str(graph["examiner_revision"])
        with self.database.transaction(immediate=True) as connection:
            original = connection.execute(
                """
                SELECT e.attempt_id,e.evaluator,e.rubric_json,e.evidence_json
                FROM evaluations e JOIN attempts a ON a.attempt_id=e.attempt_id
                WHERE a.task_id=? AND a.attempt_number=2
                """,
                (f"{self.course_id}-kickoff-examiner-v2",),
            ).fetchone()
            connection.execute(
                """
                INSERT INTO evaluations(
                    evaluation_id,attempt_id,evaluator,rubric_json,result,score,
                    evidence_json,created_at
                ) VALUES (?,?,?,?,?,?,?,?)
                """,
                (
                    f"conflicting_{examiner_id}",
                    original["attempt_id"],
                    original["evaluator"],
                    original["rubric_json"],
                    "PASS",
                    99.0,
                    original["evidence_json"],
                    102.0,
                ),
            )

        result = seed_next_csdiy_course_batches(self.database, self.jobs)
        course = result["courses"][self.course_id]
        self.assertEqual("KICKOFF_REVISION_EVIDENCE_INVALID", course["status"])
        self.assertIn("attempt-bound", course["reason"])
        self.assertEqual(0, result["created_jobs"])
        with self.database.connect() as connection:
            progression_jobs = connection.execute(
                """
                SELECT COUNT(*) AS n FROM jobs
                WHERE json_extract(payload_json,'$.seed_policy.kind')=
                      'csdiy_course_progression'
                """
            ).fetchone()["n"]
        self.assertEqual(0, progression_jobs)

    def test_examiner_identity_must_match_declared_evaluator(self) -> None:
        revision = self._seed_first_revision()
        self._complete_revision(revision, evaluation_result="PASS")
        with self.database.transaction(immediate=True) as connection:
            changed = connection.execute(
                """
                UPDATE evaluations SET evaluator='undeclared evaluator'
                WHERE attempt_id IN (
                    SELECT attempt_id FROM attempts
                    WHERE task_id=? AND attempt_number=2
                )
                """,
                (f"{self.course_id}-kickoff-examiner-v2",),
            )
        self.assertEqual(1, changed.rowcount)
        course = seed_next_csdiy_course_batches(self.database, self.jobs)["courses"][
            self.course_id
        ]
        self.assertEqual("KICKOFF_REVISION_EVIDENCE_INVALID", course["status"])
        self.assertIn("attempt-bound", course["reason"])
        coverage = status_snapshot(self.database)["metrics"]["scaleout_coverage"][
            "csdiy"
        ]
        self.assertEqual(0, coverage["succeeded_cohorts"])
        self.assertEqual(1, coverage["invalid_kickoff_revision_chains"])

    def test_semantically_identical_duplicate_evidence_remains_unambiguous(self) -> None:
        revision = self._seed_first_revision()
        self._complete_revision(revision, evaluation_result="FAIL")
        with self.database.transaction(immediate=True) as connection:
            original = connection.execute(
                """
                SELECT e.attempt_id,e.evaluator,e.rubric_json,e.result,e.score,
                       e.evidence_json
                FROM evaluations e JOIN attempts a ON a.attempt_id=e.attempt_id
                WHERE a.task_id=? AND a.attempt_number=2
                """,
                (f"{self.course_id}-kickoff-examiner-v2",),
            ).fetchone()
            connection.execute(
                """
                INSERT INTO evaluations(
                    evaluation_id,attempt_id,evaluator,rubric_json,result,score,
                    evidence_json,created_at
                ) VALUES (?,?,?,?,?,?,?,?)
                """,
                (
                    "identical_kickoff_revision_evaluation",
                    original["attempt_id"],
                    original["evaluator"],
                    original["rubric_json"],
                    original["result"],
                    original["score"],
                    original["evidence_json"],
                    102.0,
                ),
            )

        course = seed_next_csdiy_course_batches(
            self.database, self.jobs, max_revisions=2
        )["courses"][self.course_id]
        self.assertEqual("KICKOFF_REVISION_GRAPH_SEEDED", course["status"])
        self.assertEqual(3, course["attempt_number"])
        self.assertEqual(2, course["created_jobs"])

    def test_reporting_uses_highest_valid_ordinal_and_rejects_a_fork(self) -> None:
        revision = self._seed_first_revision()
        self._complete_revision(revision, evaluation_result="PASS")
        csdiy = status_snapshot(self.database)["metrics"]["scaleout_coverage"][
            "csdiy"
        ]
        self.assertEqual(1, csdiy["succeeded_cohorts"])
        self.assertEqual(0, csdiy["invalid_kickoff_revision_chains"])
        self.assertEqual(
            {"PASS": 1, "REVISE": 0, "FAIL": 0, "UNKNOWN": 0, "AMBIGUOUS": 0},
            csdiy["examiner_outcomes"],
        )

        graph = revision["jobs"]
        assert isinstance(graph, dict)
        original = self.jobs.get(str(graph["student_revision"]))
        assert original is not None
        self.jobs.create(
            "codex_task",
            "student",
            original["payload"],
            job_id="job_forked_kickoff_revision_student",
            priority=original["priority"],
            score_components=original["score_components"],
            max_attempts=2,
            dependencies=list(self._dependencies(str(graph["student_revision"]))),
            model="gpt-5.6-sol",
            reasoning_effort="ultra",
        )
        forked = status_snapshot(self.database)["metrics"]["scaleout_coverage"][
            "csdiy"
        ]
        self.assertEqual(0, forked["succeeded_cohorts"])
        self.assertEqual(1, forked["invalid_kickoff_revision_chains"])
        self.assertEqual(1, forked["examiner_outcomes"]["AMBIGUOUS"])

    def test_reporting_rejects_a_revision_ordinal_gap(self) -> None:
        revision = self._seed_first_revision()
        graph = revision["jobs"]
        assert isinstance(graph, dict)
        student_id = str(graph["student_revision"])
        examiner_id = str(graph["examiner_revision"])
        student = self.jobs.get(student_id)
        assert student is not None
        gap_payload = json.loads(canonical_json(student["payload"]))
        gap_payload["seed_policy"]["attempt_number"] = 3
        gap_payload["revision_snapshot"]["attempt_number"] = 3
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                "DELETE FROM events WHERE job_id IN (?,?)",
                (student_id, examiner_id),
            )
            connection.execute("DELETE FROM jobs WHERE job_id=?", (examiner_id,))
            connection.execute("DELETE FROM jobs WHERE job_id=?", (student_id,))
        self.jobs.create(
            "codex_task",
            "student",
            gap_payload,
            job_id="job_gapped_kickoff_revision_student",
            priority=student["priority"],
            score_components=student["score_components"],
            max_attempts=2,
            dependencies=[
                CODEX_BACKEND_GATE_JOB_ID,
                self.kickoff["preparation"],
                self.kickoff["student"],
                self.kickoff["examiner"],
            ],
            model="gpt-5.6-sol",
            reasoning_effort="ultra",
        )
        coverage = status_snapshot(self.database)["metrics"]["scaleout_coverage"][
            "csdiy"
        ]
        self.assertEqual(0, coverage["succeeded_cohorts"])
        self.assertEqual(1, coverage["invalid_kickoff_revision_chains"])
        self.assertEqual(1, coverage["examiner_outcomes"]["AMBIGUOUS"])


if __name__ == "__main__":
    unittest.main()
