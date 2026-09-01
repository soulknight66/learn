from __future__ import annotations

import asyncio
import json
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import learnfactory.course_progression as course_progression
from learnfactory.cli import build_parser, cmd_seed_course_next
from learnfactory.config import FactorySettings, load_settings
from learnfactory.course_progression import (
    COURSE_PROGRESSION_POLICY_KIND,
    seed_next_csdiy_course_batches,
)
from learnfactory.db import Database
from learnfactory.handlers import JobHandlers
from learnfactory.jobs import JobRepository
from learnfactory.learners import seed_students
from learnfactory.scheduler import run_scheduler
from learnfactory.seeding import (
    CODEX_BACKEND_GATE_JOB_ID,
    seed_all_csdiy_course_cohorts,
    seed_codex_backend_gate,
)
from learnfactory.util import canonical_json, file_sha256, tree_sha256
from learnfactory.validation import Validator
from learnfactory.workspace import WorkspaceError, WorkspaceManager


ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "migrations"


class CourseProgressionTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="learnfactory-course-next-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.database = Database(self.root / "factory.db", MIGRATIONS)
        self.database.migrate()
        self.jobs = JobRepository(self.database)
        seed_students(self.database, self.root / "warehouse")
        self.course_id = "course_systems_101"
        self._insert_course()
        seed_codex_backend_gate(self.jobs)
        cohort = seed_all_csdiy_course_cohorts(self.database, self.jobs)["cohorts"][
            self.course_id
        ]
        self.kickoff = {
            "preparation": cohort["preparation"],
            "student": cohort["student"],
            "examiner": cohort["examiner"],
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
                    "course-commit-1",
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
                    "systems-101",
                    "Example University",
                    "Systems Engineering 101",
                    "systems",
                    "A normalized course catalog entry.",
                    "[]",
                    80.0,
                    7.0,
                    canonical_json({"resource_urls": ["https://example.test/course"]}),
                    "DISCOVERED",
                ),
            )
            connection.executemany(
                """
                INSERT INTO course_units(
                    unit_id,course_id,type,unit_order,title,dependencies_json,
                    source_reference,metadata_json
                ) VALUES (?,?,?,?,?,?,?,?)
                """,
                [
                    (
                        "unit_overview",
                        self.course_id,
                        "reading",
                        0,
                        "Catalog overview",
                        "[]",
                        "courses/systems.en.md",
                        canonical_json(
                            {
                                "role": "catalog_overview",
                                "official_course_unit": False,
                            }
                        ),
                    ),
                    (
                        "unit_lab_one",
                        self.course_id,
                        "lab",
                        10,
                        "Lifecycle lab",
                        "[]",
                        "courses/systems.en.md#L10",
                        canonical_json(
                            {
                                "official_course_unit": True,
                                "availability": "public-link-recorded",
                            }
                        ),
                    ),
                    (
                        "unit_project_two",
                        self.course_id,
                        "project",
                        20,
                        "Concurrency project",
                        canonical_json(["unit_lab_one"]),
                        "courses/systems.en.md#L20",
                        canonical_json(
                            {
                                "official_course_unit": True,
                                "availability": "metadata-only",
                            }
                        ),
                    ),
                ],
            )

    def _complete(
        self,
        job_id: str,
        artifact_type: str,
        files: dict[str, str] | None = None,
        *,
        archive: bool = True,
        evaluation_result: str = "PASS",
    ) -> None:
        self.jobs.promote_eligible()
        job = self.jobs.get(job_id)
        assert job is not None
        self.assertEqual("READY", job["state"], job_id)
        artifact_path = (
            self.root / "warehouse" / "artifacts" / "test-fixtures" / job_id
        )
        artifact_path.mkdir(parents=True)
        for relative, content in (files or {"evidence.txt": "validated\n"}).items():
            target = artifact_path / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                """
                UPDATE jobs
                SET state='CLAIMED',owner='test-owner',lease_token='test-lease',
                    lease_expires_at=10000,heartbeat_at=100,attempt_count=1,started_at=100
                WHERE job_id=? AND state='READY'
                """,
                (job_id,),
            )
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
            if archive:
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
            if artifact_type.startswith("independent-course-"):
                policy = job["payload"]["learner_evidence"]
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
                        90.0 if evaluation_result == "PASS" else 50.0,
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
                            }
                        ),
                        101.0,
                    ),
                )

    def _complete_kickoff(self, *, archive_preparation: bool = True) -> None:
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
                "student_safe/COURSE_BRIEF.md": "brief\n",
                "student_safe/STUDY_TASK.md": "task\n",
                "student_safe/COMPREHENSION.md": "questions\n",
                "examiner_only/RUBRIC.md": "rubric\n",
            },
            archive=archive_preparation,
        )
        self._complete(
            self.kickoff["student"],
            "student-course-attempt",
            {
                "notes.md": "notes\n",
                "submission.md": "submission\n",
                "debugging-log.md": "debugging\n",
            },
        )
        self._complete(
            self.kickoff["examiner"],
            "independent-course-evaluation",
            {"evaluation.json": "{}\n", "feedback.md": "feedback\n"},
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

    def _cancel_unstarted_legacy_materializer(
        self,
        *,
        payload_mutation: tuple[str, object] | None = None,
    ) -> tuple[dict[str, object], dict[str, object]]:
        self._complete_kickoff()
        seeded = seed_next_csdiy_course_batches(self.database, self.jobs)
        course = seeded["courses"][self.course_id]
        graph = course["jobs"]
        materializer = self.jobs.get(graph["materializer"])
        assert materializer is not None
        snapshot = materializer["payload"]["batch_snapshot"]
        legacy_payload = course_progression._legacy_materializer_payload(
            materializer["payload"], snapshot
        )
        if payload_mutation is not None:
            key, value = payload_mutation
            legacy_payload[key] = value
        with self.database.transaction(immediate=True) as connection:
            changed = connection.execute(
                """
                UPDATE jobs SET payload_json=?
                WHERE job_id=? AND state='DISCOVERED' AND attempt_count=0
                """,
                (canonical_json(legacy_payload), graph["materializer"]),
            )
        self.assertEqual(1, changed.rowcount)
        self.jobs.cancel(graph["materializer"])
        self.jobs.promote_eligible()
        return course, legacy_payload

    def _seed_revision_graph(
        self,
        *,
        evaluation_result: str = "REVISE",
        max_revisions: int = 2,
    ) -> tuple[dict[str, object], dict[str, object]]:
        self._complete_kickoff()
        first = seed_next_csdiy_course_batches(self.database, self.jobs)
        first_course = first["courses"][self.course_id]
        jobs = first_course["jobs"]
        self._complete(
            jobs["materializer"],
            "course-unit-materialization",
            {
                "BATCH_MANIFEST.json": "{}\n",
                "student_safe/UNIT_BRIEF.md": "brief\n",
                "student_safe/LEARNING_TASK.md": "task\n",
                "student_safe/SELF_CHECK.md": "questions\n",
                "examiner_only/RUBRIC.md": "withheld rubric\n",
                "examiner_only/NOVEL_CHECK.md": "withheld novel check\n",
            },
        )
        self._complete(
            jobs["student"],
            "student-course-unit-attempt",
            {
                "student_work/notes.md": "prior notes\n",
                "student_work/submission.md": "prior submission\n",
                "student_work/debugging-log.md": "prior debugging\n",
                "student_work/self-check.md": "prior self-check\n",
            },
        )
        self._complete(
            jobs["examiner"],
            "independent-course-unit-evaluation",
            {
                "evaluation.json": canonical_json(
                    {
                        "result": evaluation_result,
                        "score": 50,
                        "evidence": ["bounded externally observed gap"],
                        "transfer_gaps": [],
                    }
                ),
                "feedback.md": "Address the bounded externally observed gap.\n",
            },
            evaluation_result=evaluation_result,
        )
        revision = seed_next_csdiy_course_batches(
            self.database,
            self.jobs,
            max_revisions=max_revisions,
        )
        return first_course, revision["courses"][self.course_id]

    def test_waits_for_verified_kickoff_and_seeds_isolated_bounded_graph(self) -> None:
        waiting = seed_next_csdiy_course_batches(self.database, self.jobs)
        self.assertEqual(
            "WAITING_FOR_VERIFIED_PREPARATION",
            waiting["courses"][self.course_id]["status"],
        )
        self.assertEqual(0, waiting["created_jobs"])

        self._complete_kickoff()
        result = seed_next_csdiy_course_batches(self.database, self.jobs)
        course = result["courses"][self.course_id]
        self.assertEqual("BOUNDED_BATCH_GRAPH_SEEDED", course["status"])
        self.assertEqual(["unit_lab_one"], course["unit_ids"])
        self.assertEqual("NOT_CLAIMED", course["course_completion"])
        self.assertEqual("NOT_CLAIMED", course["transfer_verification"])
        self.assertEqual(3, result["created_jobs"])
        self.assertEqual("NONE", result["completion_claim"])

        materializer_id = course["jobs"]["materializer"]
        student_id = course["jobs"]["student"]
        examiner_id = course["jobs"]["examiner"]
        self.assertEqual(
            {
                CODEX_BACKEND_GATE_JOB_ID,
                self.kickoff["preparation"],
                self.kickoff["examiner"],
            },
            self._dependencies(materializer_id),
        )
        self.assertEqual(
            {CODEX_BACKEND_GATE_JOB_ID, materializer_id},
            self._dependencies(student_id),
        )
        self.assertEqual(
            {CODEX_BACKEND_GATE_JOB_ID, materializer_id, student_id},
            self._dependencies(examiner_id),
        )

        for role, job_id in course["jobs"].items():
            job = self.jobs.get(job_id)
            assert job is not None
            self.assertEqual("gpt-5.6-sol", job["model"])
            self.assertEqual("ultra", job["reasoning_effort"])
            self.assertEqual(
                {
                    "kind": COURSE_PROGRESSION_POLICY_KIND,
                    "version": 1,
                    "role": role,
                },
                job["payload"]["seed_policy"],
            )

        student = self.jobs.get(student_id)
        examiner = self.jobs.get(examiner_id)
        materializer = self.jobs.get(materializer_id)
        assert student is not None and examiner is not None and materializer is not None
        self.assertTrue(
            all(
                item["subpath"].startswith("student_safe/")
                for item in student["payload"]["inputs_from_dependencies"]
            )
        )
        self.assertNotIn("RUBRIC.md", student["payload"]["prompt"])
        examiner_paths = {
            item["subpath"] for item in examiner["payload"]["inputs_from_dependencies"]
        }
        self.assertIn("examiner_only/RUBRIC.md", examiner_paths)
        self.assertIn("examiner_only/NOVEL_CHECK.md", examiner_paths)
        self.assertEqual(
            "one bounded normalized-resource batch; not course completion",
            examiner["payload"]["learner_evidence"]["rubric"]["assessment_scope"],
        )
        self.assertEqual(
            "NOT_CLAIMED",
            materializer["payload"]["batch_snapshot"]["completion_scope"][
                "course_completion"
            ],
        )
        snapshot = materializer["payload"]["batch_snapshot"]
        manifest_template = materializer["payload"]["batch_manifest_template"]
        manifest_schema = next(
            validator["schema"]
            for validator in materializer["payload"]["validators"]
            if validator["name"] == "bounded-unit-manifest"
        )
        self.assertEqual(2, materializer["payload"]["materializer_contract_version"])
        self.assertEqual(
            {
                "course_id",
                "batch_id",
                "sequence",
                "status",
                "course_completion",
                "unit_ids",
                "availability",
                "blocked",
                "completion_policy",
                "provenance",
            },
            set(manifest_template),
        )
        self.assertEqual(self.course_id, manifest_template["course_id"])
        self.assertEqual(snapshot["batch_id"], manifest_template["batch_id"])
        self.assertEqual(["unit_lab_one"], manifest_template["unit_ids"])
        self.assertFalse(manifest_schema["additionalProperties"])
        prompt = materializer["payload"]["prompt"]
        self.assertIn(
            f"BATCH_MANIFEST_TEMPLATE_JSON={canonical_json(manifest_template)}",
            prompt,
        )
        self.assertIn(
            f"BATCH_MANIFEST_JSON_SCHEMA={canonical_json(manifest_schema)}",
            prompt,
        )
        self.assertIn("exactly these root keys and no others", prompt)
        self.assertIn("do not rename fields or introduce a richer alternate", prompt)
        learner_snapshot = materializer["payload"]["batch_snapshot"][
            "learner_snapshot"
        ]
        self.assertEqual("student-target", learner_snapshot["student_id"])
        self.assertIn("algorithms", learner_snapshot["profile"]["strengths"])

    def test_failed_legacy_materializer_contract_is_retried_with_evidence_intact(
        self,
    ) -> None:
        self._complete_kickoff()
        seeded = seed_next_csdiy_course_batches(self.database, self.jobs)
        materializer_id = seeded["courses"][self.course_id]["jobs"]["materializer"]
        materializer = self.jobs.get(materializer_id)
        assert materializer is not None
        snapshot = materializer["payload"]["batch_snapshot"]
        legacy_payload = course_progression._legacy_materializer_payload(
            materializer["payload"], snapshot
        )

        self.jobs.promote_eligible()
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                "UPDATE jobs SET payload_json=? WHERE job_id=? AND state='READY'",
                (canonical_json(legacy_payload), materializer_id),
            )
            connection.execute(
                """
                UPDATE jobs
                SET state='CLAIMED',owner='legacy-worker',lease_token='legacy-lease',
                    lease_expires_at=10000,heartbeat_at=100,attempt_count=1,
                    started_at=100
                WHERE job_id=? AND state='READY'
                """,
                (materializer_id,),
            )
            connection.execute(
                "UPDATE jobs SET state='RUNNING' WHERE job_id=? AND state='CLAIMED'",
                (materializer_id,),
            )
            connection.execute(
                """
                INSERT INTO job_runs(
                    run_id,job_id,attempt_number,backend,model,reasoning_effort,
                    started_at,finished_at,exit_code
                ) VALUES (?,?,?,?,?,?,?,?,?)
                """,
                (
                    "run_legacy_materializer_failure",
                    materializer_id,
                    1,
                    "exec",
                    "gpt-5.6-sol",
                    "ultra",
                    100.0,
                    101.0,
                    0,
                ),
            )
            connection.execute(
                """
                INSERT INTO validations(
                    validation_id,job_id,validator,status,evidence_json,
                    started_at,finished_at,attempt_number,claims_json
                ) VALUES (?,?,?,?,?,?,?,?,?)
                """,
                (
                    "validation_legacy_materializer_manifest",
                    materializer_id,
                    "bounded-unit-manifest",
                    "FAIL",
                    canonical_json(
                        {
                            "error": "unexpected richer manifest shape",
                            "preserved": True,
                        }
                    ),
                    100.5,
                    101.0,
                    1,
                    "[]",
                ),
            )
            connection.execute(
                """
                UPDATE jobs
                SET state='FAILED',owner=NULL,lease_token=NULL,
                    lease_expires_at=NULL,heartbeat_at=101,finished_at=101,
                    error='validation failed',failure_kind='validation_failure'
                WHERE job_id=? AND state='RUNNING'
                """,
                (materializer_id,),
            )

        retried = seed_next_csdiy_course_batches(self.database, self.jobs)
        self.assertEqual(
            "WAITING_FOR_BATCH_PIPELINE",
            retried["courses"][self.course_id]["status"],
        )
        repaired = self.jobs.get(materializer_id)
        assert repaired is not None
        self.assertEqual("READY", repaired["state"])
        self.assertEqual(1, repaired["attempt_count"])
        self.assertEqual(2, repaired["payload"]["materializer_contract_version"])
        self.assertIn("BATCH_MANIFEST_TEMPLATE_JSON=", repaired["payload"]["prompt"])
        self.assertIn("BATCH_MANIFEST_JSON_SCHEMA=", repaired["payload"]["prompt"])
        with self.database.connect() as connection:
            validation = connection.execute(
                """
                SELECT status,evidence_json,attempt_number FROM validations
                WHERE validation_id='validation_legacy_materializer_manifest'
                """
            ).fetchone()
            run = connection.execute(
                """
                SELECT attempt_number,exit_code FROM job_runs
                WHERE run_id='run_legacy_materializer_failure'
                """
            ).fetchone()
            remediation_events = connection.execute(
                """
                SELECT COUNT(*) AS n FROM events
                WHERE job_id=?
                  AND type='COURSE_MATERIALIZER_FAILED_CONTRACT_REMEDIATED'
                """,
                (materializer_id,),
            ).fetchone()["n"]
        self.assertEqual("FAIL", validation["status"])
        self.assertEqual(1, validation["attempt_number"])
        self.assertTrue(json.loads(validation["evidence_json"])["preserved"])
        self.assertEqual(1, run["attempt_number"])
        self.assertEqual(0, run["exit_code"])
        self.assertEqual(1, remediation_events)

    def test_cancelled_unstarted_legacy_graph_is_immutably_superseded(self) -> None:
        original_course, legacy_payload = self._cancel_unstarted_legacy_materializer()
        original_graph = original_course["jobs"]
        original_materializer_id = original_graph["materializer"]
        with self.database.connect() as connection:
            terminal_before = dict(
                connection.execute(
                    "SELECT * FROM jobs WHERE job_id=?",
                    (original_materializer_id,),
                ).fetchone()
            )
            reservation_before = dict(
                connection.execute(
                    """
                    SELECT * FROM course_progression_reservations
                    WHERE batch_id=?
                    """,
                    (original_course["batch_id"],),
                ).fetchone()
            )

        superseded = seed_next_csdiy_course_batches(self.database, self.jobs)
        course = superseded["courses"][self.course_id]
        successor_graph = course["jobs"]
        self.assertEqual("CANCELLED_LEGACY_GRAPH_SUPERSEDED", course["status"])
        self.assertEqual(3, superseded["created_jobs"])
        self.assertEqual("CANCELLED", course["terminal_state_preserved"])
        self.assertEqual(original_graph, course["superseded_jobs"])
        self.assertTrue(
            all(successor_graph[role] != original_graph[role] for role in original_graph)
        )

        successor_materializer = self.jobs.get(successor_graph["materializer"])
        successor_student = self.jobs.get(successor_graph["student"])
        successor_examiner = self.jobs.get(successor_graph["examiner"])
        assert (
            successor_materializer is not None
            and successor_student is not None
            and successor_examiner is not None
        )
        for role, successor in (
            ("materializer", successor_materializer),
            ("student", successor_student),
            ("examiner", successor_examiner),
        ):
            self.assertEqual("gpt-5.6-sol", successor["model"])
            self.assertEqual("ultra", successor["reasoning_effort"])
            marker = successor["payload"]["contract_supersession"]
            self.assertEqual(
                course_progression.MATERIALIZER_CONTRACT_SUPERSESSION_KIND,
                marker["kind"],
            )
            self.assertEqual(original_graph[role], marker["supersedes_job_id"])
            self.assertEqual(original_graph, marker["superseded_graph"])
        self.assertEqual(
            2,
            successor_materializer["payload"]["materializer_contract_version"],
        )
        self.assertIn(
            "BATCH_MANIFEST_TEMPLATE_JSON=",
            successor_materializer["payload"]["prompt"],
        )
        self.assertEqual(
            {
                CODEX_BACKEND_GATE_JOB_ID,
                self.kickoff["preparation"],
                self.kickoff["examiner"],
            },
            self._dependencies(successor_graph["materializer"]),
        )
        self.assertEqual(
            {CODEX_BACKEND_GATE_JOB_ID, successor_graph["materializer"]},
            self._dependencies(successor_graph["student"]),
        )
        self.assertEqual(
            {
                CODEX_BACKEND_GATE_JOB_ID,
                successor_graph["materializer"],
                successor_graph["student"],
            },
            self._dependencies(successor_graph["examiner"]),
        )

        with self.database.connect() as connection:
            terminal_after = dict(
                connection.execute(
                    "SELECT * FROM jobs WHERE job_id=?",
                    (original_materializer_id,),
                ).fetchone()
            )
            reservation_after = dict(
                connection.execute(
                    """
                    SELECT * FROM course_progression_reservations
                    WHERE batch_id=?
                    """,
                    (original_course["batch_id"],),
                ).fetchone()
            )
            old_descendant_states = {
                str(row["job_id"]): str(row["state"])
                for row in connection.execute(
                    "SELECT job_id,state FROM jobs WHERE job_id IN (?,?)",
                    (original_graph["student"], original_graph["examiner"]),
                )
            }
        self.assertEqual(terminal_before, terminal_after)
        self.assertEqual(canonical_json(legacy_payload), terminal_after["payload_json"])
        self.assertEqual("CANCELLED", terminal_after["state"])
        self.assertEqual(reservation_before, reservation_after)
        self.assertEqual(
            {
                original_graph["student"]: "BLOCKED",
                original_graph["examiner"]: "BLOCKED",
            },
            old_descendant_states,
        )

        repeated = seed_next_csdiy_course_batches(self.database, self.jobs)
        self.assertEqual(0, repeated["created_jobs"])
        self.assertEqual(
            "WAITING_FOR_BATCH_PIPELINE",
            repeated["courses"][self.course_id]["status"],
        )
        with self.database.connect() as connection:
            events = connection.execute(
                """
                SELECT COUNT(*) AS n FROM events
                WHERE job_id=?
                  AND type='COURSE_MATERIALIZER_CANCELLED_CONTRACT_SUPERSEDED'
                """,
                (original_materializer_id,),
            ).fetchone()["n"]
        self.assertEqual(1, events)

    def test_modified_legacy_cancellation_is_not_superseded(self) -> None:
        original_course, _ = self._cancel_unstarted_legacy_materializer(
            payload_mutation=("prompt", "modified legacy prompt")
        )
        with self.assertRaisesRegex(
            RuntimeError, "cancelled payload is not the exact legacy contract"
        ):
            seed_next_csdiy_course_batches(self.database, self.jobs)
        self.assertEqual(
            "CANCELLED",
            self.jobs.get(original_course["jobs"]["materializer"])["state"],
        )
        with self.database.connect() as connection:
            successors = connection.execute(
                """
                SELECT COUNT(*) AS n FROM jobs
                WHERE json_extract(
                    payload_json,'$.contract_supersession.kind'
                )=?
                """,
                (course_progression.MATERIALIZER_CONTRACT_SUPERSESSION_KIND,),
            ).fetchone()["n"]
        self.assertEqual(0, successors)

    def test_current_contract_cancellation_is_not_treated_as_legacy(self) -> None:
        self._complete_kickoff()
        seeded = seed_next_csdiy_course_batches(self.database, self.jobs)
        materializer_id = seeded["courses"][self.course_id]["jobs"][
            "materializer"
        ]
        self.jobs.cancel(materializer_id)
        self.jobs.promote_eligible()

        with self.assertRaisesRegex(
            RuntimeError, "cancelled payload is not the exact legacy contract"
        ):
            seed_next_csdiy_course_batches(self.database, self.jobs)
        self.assertEqual("CANCELLED", self.jobs.get(materializer_id)["state"])

    def test_attempted_legacy_cancellation_is_not_superseded(self) -> None:
        self._complete_kickoff()
        seeded = seed_next_csdiy_course_batches(self.database, self.jobs)
        materializer_id = seeded["courses"][self.course_id]["jobs"][
            "materializer"
        ]
        materializer = self.jobs.get(materializer_id)
        assert materializer is not None
        legacy_payload = course_progression._legacy_materializer_payload(
            materializer["payload"], materializer["payload"]["batch_snapshot"]
        )
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                "UPDATE jobs SET payload_json=? WHERE job_id=?",
                (canonical_json(legacy_payload), materializer_id),
            )
        self.jobs.promote_eligible()
        claim = self.jobs.claim_next(
            "attempted-legacy-worker",
            30,
            max_total=1,
            type_limits={"course_manager": 1},
        )
        assert claim is not None
        self.assertEqual(materializer_id, claim.job_id)
        self.jobs.cancel(materializer_id)
        self.jobs.finish_cancelled(
            materializer_id,
            "attempted-legacy-worker",
            claim.lease_token,
            None,  # type: ignore[arg-type]
        )

        with self.assertRaisesRegex(RuntimeError, "was attempted"):
            seed_next_csdiy_course_batches(self.database, self.jobs)
        attempted = self.jobs.get(materializer_id)
        assert attempted is not None
        self.assertEqual("CANCELLED", attempted["state"])
        self.assertEqual(1, attempted["attempt_count"])

    def test_concurrent_cancelled_legacy_refillers_share_one_successor_graph(
        self,
    ) -> None:
        original_course, _ = self._cancel_unstarted_legacy_materializer()
        barrier = threading.Barrier(2)
        original_ensure_graph = course_progression._ensure_graph

        def synchronized_ensure_graph(
            *args: object, **kwargs: object
        ) -> tuple[dict[str, str], int]:
            barrier.wait(timeout=10)
            return original_ensure_graph(*args, **kwargs)

        with patch.object(
            course_progression,
            "_ensure_graph",
            side_effect=synchronized_ensure_graph,
        ):
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [
                    pool.submit(
                        seed_next_csdiy_course_batches,
                        self.database,
                        self.jobs,
                    )
                    for _ in range(2)
                ]
                results = [future.result(timeout=20) for future in futures]

        courses = [result["courses"][self.course_id] for result in results]
        self.assertTrue(
            all(
                course["status"] == "CANCELLED_LEGACY_GRAPH_SUPERSEDED"
                for course in courses
            )
        )
        self.assertEqual(
            1,
            len({tuple(sorted(course["jobs"].items())) for course in courses}),
        )
        self.assertEqual(3, sum(result["created_jobs"] for result in results))
        with self.database.connect() as connection:
            successor_jobs = connection.execute(
                """
                SELECT COUNT(*) AS n FROM jobs
                WHERE json_extract(payload_json,'$.contract_supersession.kind')=?
                """,
                (course_progression.MATERIALIZER_CONTRACT_SUPERSESSION_KIND,),
            ).fetchone()["n"]
            supersession_events = connection.execute(
                """
                SELECT COUNT(*) AS n FROM events
                WHERE job_id=?
                  AND type='COURSE_MATERIALIZER_CANCELLED_CONTRACT_SUPERSEDED'
                """,
                (original_course["jobs"]["materializer"],),
            ).fetchone()["n"]
        self.assertEqual(3, successor_jobs)
        self.assertEqual(1, supersession_events)
        self.assertEqual(
            "CANCELLED",
            self.jobs.get(original_course["jobs"]["materializer"])["state"],
        )

    def test_superseding_graph_drives_revisions_and_next_batch(self) -> None:
        self._cancel_unstarted_legacy_materializer()
        superseded = seed_next_csdiy_course_batches(self.database, self.jobs)
        successor = superseded["courses"][self.course_id]["jobs"]
        self._complete(successor["materializer"], "course-unit-materialization")
        self._complete(successor["student"], "student-course-unit-attempt")
        self._complete(
            successor["examiner"],
            "independent-course-unit-evaluation",
            evaluation_result="REVISE",
        )

        revision_result = seed_next_csdiy_course_batches(
            self.database, self.jobs, max_revisions=2
        )
        revision = revision_result["courses"][self.course_id]
        self.assertEqual("REVISION_GRAPH_SEEDED", revision["status"])
        revision_jobs = revision["jobs"]
        self.assertIn(
            successor["materializer"],
            self._dependencies(revision_jobs["student_revision"]),
        )
        self.assertIn(
            successor["materializer"],
            self._dependencies(revision_jobs["examiner_revision"]),
        )
        self.assertNotIn(
            superseded["courses"][self.course_id]["superseded_jobs"]["materializer"],
            self._dependencies(revision_jobs["student_revision"]),
        )
        revision_student = self.jobs.get(revision_jobs["student_revision"])
        revision_examiner = self.jobs.get(revision_jobs["examiner_revision"])
        assert revision_student is not None and revision_examiner is not None
        self.assertEqual(
            successor["materializer"],
            revision_student["payload"]["provenance"]["materializer_job_id"],
        )
        self.assertEqual(
            successor["materializer"],
            revision_examiner["payload"]["learner_evidence"]["rubric"][
                "source_job_id"
            ],
        )

        self._complete(
            revision_jobs["student_revision"], "student-course-unit-attempt"
        )
        self._complete(
            revision_jobs["examiner_revision"],
            "independent-course-unit-evaluation",
            evaluation_result="PASS",
        )
        advanced = seed_next_csdiy_course_batches(
            self.database, self.jobs, max_revisions=2
        )
        next_course = advanced["courses"][self.course_id]
        self.assertEqual("BOUNDED_BATCH_GRAPH_SEEDED", next_course["status"])
        self.assertEqual(2, next_course["sequence"])
        self.assertIn(
            revision_jobs["examiner_revision"],
            self._dependencies(next_course["jobs"]["materializer"]),
        )

    def test_refill_is_idempotent_then_advances_only_after_verified_examiner(self) -> None:
        self._complete_kickoff()
        first = seed_next_csdiy_course_batches(self.database, self.jobs)
        first_course = first["courses"][self.course_id]
        first_jobs = first_course["jobs"]

        repeated = seed_next_csdiy_course_batches(self.database, self.jobs)
        self.assertEqual(0, repeated["created_jobs"])
        self.assertEqual(
            "WAITING_FOR_BATCH_PIPELINE",
            repeated["courses"][self.course_id]["status"],
        )

        self._complete(
            first_jobs["materializer"],
            "course-unit-materialization",
            {"BATCH_MANIFEST.json": "{}\n"},
        )
        self._complete(
            first_jobs["student"],
            "student-course-unit-attempt",
            {"student_work/submission.md": "submission\n"},
        )
        self._complete(
            first_jobs["examiner"],
            "independent-course-unit-evaluation",
            {"evaluation.json": "{}\n"},
        )

        second = seed_next_csdiy_course_batches(self.database, self.jobs)
        second_course = second["courses"][self.course_id]
        self.assertEqual("BOUNDED_BATCH_GRAPH_SEEDED", second_course["status"])
        self.assertEqual(2, second_course["sequence"])
        self.assertEqual(["unit_project_two"], second_course["unit_ids"])
        self.assertNotEqual(first_course["batch_id"], second_course["batch_id"])
        self.assertIn(
            first_jobs["examiner"],
            self._dependencies(second_course["jobs"]["materializer"]),
        )

        for role, artifact_type in (
            ("materializer", "course-unit-materialization"),
            ("student", "student-course-unit-attempt"),
            ("examiner", "independent-course-unit-evaluation"),
        ):
            self._complete(second_course["jobs"][role], artifact_type)
        exhausted = seed_next_csdiy_course_batches(self.database, self.jobs)
        status = exhausted["courses"][self.course_id]
        self.assertEqual("NORMALIZED_RECORDS_EXHAUSTED", status["status"])
        self.assertEqual("NOT_CLAIMED", status["course_completion"])
        self.assertIn("does not prove", status["reason"])
        self.assertEqual(0, exhausted["created_jobs"])

    def test_partial_graph_is_repaired_from_durable_batch_snapshot(self) -> None:
        self._complete_kickoff()
        first = seed_next_csdiy_course_batches(self.database, self.jobs)
        course = first["courses"][self.course_id]
        examiner_id = course["jobs"]["examiner"]
        with self.database.transaction(immediate=True) as connection:
            connection.execute("DELETE FROM events WHERE job_id=?", (examiner_id,))
            connection.execute("DELETE FROM jobs WHERE job_id=?", (examiner_id,))

        repaired = seed_next_csdiy_course_batches(self.database, self.jobs)
        repaired_course = repaired["courses"][self.course_id]
        self.assertEqual("PARTIAL_GRAPH_REPAIRED", repaired_course["status"])
        self.assertEqual(course["batch_id"], repaired_course["batch_id"])
        self.assertEqual(1, repaired_course["created_jobs"])
        self.assertEqual(examiner_id, repaired_course["jobs"]["examiner"])
        examiner = self.jobs.get(examiner_id)
        assert examiner is not None
        self.assertEqual(
            ["unit_lab_one"],
            [
                record["unit_id"]
                for record in examiner["payload"]["batch_snapshot"][
                    "normalized_records"
                ]
            ],
        )

    def test_nonpassing_examiner_seeds_isolated_versioned_revision(self) -> None:
        self._complete_kickoff()
        first = seed_next_csdiy_course_batches(self.database, self.jobs)
        jobs = first["courses"][self.course_id]["jobs"]
        self._complete(jobs["materializer"], "course-unit-materialization")
        self._complete(jobs["student"], "student-course-unit-attempt")
        self._complete(
            jobs["examiner"],
            "independent-course-unit-evaluation",
            {
                "evaluation.json": canonical_json(
                    {
                        "result": "REVISE",
                        "score": 50,
                        "evidence": ["one bounded gap"],
                        "transfer_gaps": [],
                    }
                ),
                "feedback.md": "Address the observed bounded gap.\n",
            },
            evaluation_result="REVISE",
        )

        revised = seed_next_csdiy_course_batches(
            self.database, self.jobs, max_revisions=2
        )
        course = revised["courses"][self.course_id]
        self.assertEqual("REVISION_GRAPH_SEEDED", course["status"])
        self.assertEqual("REVISE", course["evaluation_result"])
        self.assertEqual(2, revised["created_jobs"])
        self.assertEqual(2, course["attempt_number"])
        self.assertEqual("NOT_CLAIMED", course["course_completion"])
        student_id = course["jobs"]["student_revision"]
        examiner_id = course["jobs"]["examiner_revision"]
        student = self.jobs.get(student_id)
        examiner = self.jobs.get(examiner_id)
        assert student is not None and examiner is not None
        for revision_job in (student, examiner):
            self.assertEqual("gpt-5.6-sol", revision_job["model"])
            self.assertEqual("ultra", revision_job["reasoning_effort"])
            self.assertEqual(2, revision_job["payload"]["seed_policy"]["attempt_number"])
        student_inputs = student["payload"]["inputs_from_dependencies"]
        self.assertEqual(
            {"evaluation.json", "feedback.md"},
            {
                item["subpath"]
                for item in student_inputs
                if item["job_id"] == jobs["examiner"]
            },
        )
        self.assertFalse(
            any(
                "RUBRIC" in item["subpath"].upper()
                or "NOVEL_CHECK" in item["subpath"].upper()
                or "REFERENCE" in item["subpath"].upper()
                for item in student_inputs
            )
        )
        self.assertIn(
            "examiner_only/RUBRIC.md",
            {
                item["subpath"]
                for item in examiner["payload"]["inputs_from_dependencies"]
            },
        )
        self.assertEqual(
            {
                CODEX_BACKEND_GATE_JOB_ID,
                jobs["materializer"],
                jobs["student"],
                jobs["examiner"],
            },
            self._dependencies(student_id),
        )
        self.assertEqual(
            {
                CODEX_BACKEND_GATE_JOB_ID,
                jobs["materializer"],
                student_id,
                jobs["examiner"],
            },
            self._dependencies(examiner_id),
        )
        with self.database.connect() as connection:
            original_artifacts = connection.execute(
                """
                SELECT COUNT(*) AS n FROM artifacts
                WHERE job_id IN (?,?)
                """,
                (jobs["student"], jobs["examiner"]),
            ).fetchone()["n"]
        self.assertEqual(2, original_artifacts)

        repeated = seed_next_csdiy_course_batches(
            self.database, self.jobs, max_revisions=2
        )
        self.assertEqual(0, repeated["created_jobs"])
        self.assertEqual(
            "WAITING_FOR_REVISION_PIPELINE",
            repeated["courses"][self.course_id]["status"],
        )

    def test_passing_revision_advances_with_exact_attempt_bound_evidence(self) -> None:
        _, revision = self._seed_revision_graph()
        revision_jobs = revision["jobs"]
        self._complete(
            revision_jobs["student_revision"],
            "student-course-unit-attempt",
        )
        self._complete(
            revision_jobs["examiner_revision"],
            "independent-course-unit-evaluation",
            {
                "evaluation.json": canonical_json(
                    {
                        "result": "PASS",
                        "score": 88,
                        "evidence": ["revision addressed the bounded gap"],
                        "transfer_gaps": [],
                    }
                ),
                "feedback.md": "The bounded revision passed.\n",
            },
            evaluation_result="PASS",
        )

        advanced = seed_next_csdiy_course_batches(
            self.database, self.jobs, max_revisions=2
        )
        course = advanced["courses"][self.course_id]
        self.assertEqual("BOUNDED_BATCH_GRAPH_SEEDED", course["status"])
        self.assertEqual(2, course["sequence"])
        self.assertIn(
            revision_jobs["examiner_revision"],
            self._dependencies(course["jobs"]["materializer"]),
        )
        examiner = self.jobs.get(revision_jobs["examiner_revision"])
        assert examiner is not None
        self.assertEqual(
            2, examiner["payload"]["learner_evidence"]["attempt_number"]
        )
        self.assertEqual(
            revision_jobs["student_revision"],
            examiner["payload"]["learner_evidence"]["student_job_id"],
        )

    def test_revision_staging_allows_only_bound_prior_work_and_feedback(self) -> None:
        first, revision = self._seed_revision_graph()
        student_id = revision["jobs"]["student_revision"]
        self.jobs.promote_eligible()
        claim = self.jobs.claim_next(
            "revision-staging-test",
            30,
            max_total=1,
            type_limits={"student": 1},
        )
        assert claim is not None
        self.assertEqual(student_id, claim.job_id)
        manager = WorkspaceManager(self.root / "warehouse", self.database)
        manager.initialize()
        settings = FactorySettings(
            root=ROOT,
            database=self.database.path,
            warehouse=self.root / "warehouse",
        )
        workspace = manager.allocate(student_id, claim.attempt_count)
        integrity, _ = JobHandlers(
            settings, self.database, manager
        )._stage_declared_inputs(claim, workspace)

        self.assertEqual(
            "prior submission\n",
            (workspace / "PRIOR_ATTEMPT/submission.md").read_text(
                encoding="utf-8"
            ),
        )
        self.assertEqual(
            "Address the bounded externally observed gap.\n",
            (workspace / "EXAMINER_FEEDBACK/feedback.md").read_text(
                encoding="utf-8"
            ),
        )
        self.assertEqual(
            {"ASSIGNMENT", "PRIOR_ATTEMPT", "EXAMINER_FEEDBACK"},
            {record["path"] for record in integrity},
        )
        self.assertFalse((workspace / "RUBRIC.md").exists())
        self.assertFalse((workspace / "examiner_only").exists())
        self.assertNotIn("withheld rubric", "\n".join(
            path.read_text(encoding="utf-8")
            for path in workspace.rglob("*")
            if path.is_file()
        ))

        malicious_payload = dict(claim.payload)
        malicious_payload["inputs_from_dependencies"] = [
            {
                "job_id": first["jobs"]["materializer"],
                "subpath": "examiner_only/RUBRIC.md",
                "destination": "RUBRIC.md",
                "artifact_type": "course-unit-materialization",
            },
            *claim.payload["inputs_from_dependencies"],
        ]
        malicious = replace(claim, payload=malicious_payload)
        rejected_workspace = manager.allocate(student_id, claim.attempt_count + 1)
        with self.assertRaisesRegex(WorkspaceError, "under student_safe"):
            JobHandlers(settings, self.database, manager)._stage_declared_inputs(
                malicious, rejected_workspace
            )

    def test_revision_limit_reports_blocked_and_can_be_raised_explicitly(self) -> None:
        _, revision = self._seed_revision_graph(
            evaluation_result="FAIL", max_revisions=1
        )
        revision_jobs = revision["jobs"]
        self._complete(
            revision_jobs["student_revision"],
            "student-course-unit-attempt",
        )
        self._complete(
            revision_jobs["examiner_revision"],
            "independent-course-unit-evaluation",
            {
                "evaluation.json": canonical_json(
                    {
                        "result": "FAIL",
                        "score": 20,
                        "evidence": ["bounded revision still fails"],
                        "transfer_gaps": ["same unit concept"],
                    }
                ),
                "feedback.md": "The bounded revision still needs work.\n",
            },
            evaluation_result="FAIL",
        )

        blocked = seed_next_csdiy_course_batches(
            self.database, self.jobs, max_revisions=1
        )
        course = blocked["courses"][self.course_id]
        self.assertEqual("BLOCKED_REVISION_LIMIT_EXHAUSTED", course["status"])
        self.assertEqual("BLOCKED", course["progression_state"])
        self.assertEqual(2, course["attempt_number"])
        self.assertEqual(1, course["max_revisions"])
        self.assertEqual(0, blocked["created_jobs"])
        self.assertTrue(course["block_recorded"])
        self.assertIn("finite revision limit", course["reason"])

        repeated_block = seed_next_csdiy_course_batches(
            self.database, self.jobs, max_revisions=1
        )["courses"][self.course_id]
        self.assertFalse(repeated_block["block_recorded"])
        with self.database.connect() as connection:
            block_rows = connection.execute(
                "SELECT COUNT(*) AS n FROM course_progression_revision_blocks"
            ).fetchone()["n"]
            block_events = connection.execute(
                "SELECT COUNT(*) AS n FROM events WHERE type='COURSE_REVISION_BLOCKED'"
            ).fetchone()["n"]
        self.assertEqual(1, block_rows)
        self.assertEqual(1, block_events)

        raised = seed_next_csdiy_course_batches(
            self.database, self.jobs, max_revisions=2
        )
        raised_course = raised["courses"][self.course_id]
        self.assertEqual("REVISION_GRAPH_SEEDED", raised_course["status"])
        self.assertEqual(3, raised_course["attempt_number"])
        self.assertEqual(2, raised["created_jobs"])

    def test_revision_result_must_match_exact_examiner_attempt(self) -> None:
        _, revision = self._seed_revision_graph()
        revision_jobs = revision["jobs"]
        self._complete(
            revision_jobs["student_revision"],
            "student-course-unit-attempt",
        )
        self._complete(
            revision_jobs["examiner_revision"],
            "independent-course-unit-evaluation",
            evaluation_result="PASS",
        )
        with self.database.transaction(immediate=True) as connection:
            row = connection.execute(
                """
                SELECT e.evaluation_id,e.evidence_json
                FROM evaluations e JOIN attempts a ON a.attempt_id=e.attempt_id
                WHERE a.task_id=? AND a.attempt_number=2
                """,
                (revision["batch_id"],),
            ).fetchone()
            evidence = json.loads(row["evidence_json"])
            evidence["examiner_attempt"] = 999
            connection.execute(
                "UPDATE evaluations SET evidence_json=? WHERE evaluation_id=?",
                (canonical_json(evidence), row["evaluation_id"]),
            )

        rejected = seed_next_csdiy_course_batches(
            self.database, self.jobs, max_revisions=2
        )
        course = rejected["courses"][self.course_id]
        self.assertEqual("PROGRESSION_EVIDENCE_INVALID", course["status"])
        self.assertIn("attempt-bound", course["reason"])

    def test_conflicting_unit_revision_evidence_cannot_extend_progression(self) -> None:
        _, revision = self._seed_revision_graph()
        revision_jobs = revision["jobs"]
        self._complete(
            revision_jobs["student_revision"],
            "student-course-unit-attempt",
        )
        self._complete(
            revision_jobs["examiner_revision"],
            "independent-course-unit-evaluation",
            evaluation_result="FAIL",
        )
        with self.database.transaction(immediate=True) as connection:
            original = connection.execute(
                """
                SELECT e.attempt_id,e.evaluator,e.rubric_json,e.evidence_json
                FROM evaluations e JOIN attempts a ON a.attempt_id=e.attempt_id
                WHERE a.task_id=? AND a.attempt_number=2
                """,
                (revision["batch_id"],),
            ).fetchone()
            connection.execute(
                """
                INSERT INTO evaluations(
                    evaluation_id,attempt_id,evaluator,rubric_json,result,score,
                    evidence_json,created_at
                ) VALUES (?,?,?,?,?,?,?,?)
                """,
                (
                    "conflicting_unit_revision_evaluation",
                    original["attempt_id"],
                    original["evaluator"],
                    original["rubric_json"],
                    "PASS",
                    99.0,
                    original["evidence_json"],
                    102.0,
                ),
            )

        result = seed_next_csdiy_course_batches(
            self.database, self.jobs, max_revisions=2
        )
        course = result["courses"][self.course_id]
        self.assertEqual("PROGRESSION_EVIDENCE_INVALID", course["status"])
        self.assertIn("attempt-bound control-plane evaluation", course["reason"])
        self.assertEqual(0, result["created_jobs"])

    def test_partial_revision_graph_is_repaired_from_reserved_snapshot(self) -> None:
        _, revision = self._seed_revision_graph()
        examiner_id = revision["jobs"]["examiner_revision"]
        with self.database.transaction(immediate=True) as connection:
            connection.execute("DELETE FROM events WHERE job_id=?", (examiner_id,))
            connection.execute("DELETE FROM jobs WHERE job_id=?", (examiner_id,))

        repaired = seed_next_csdiy_course_batches(
            self.database, self.jobs, max_revisions=2
        )
        course = repaired["courses"][self.course_id]
        self.assertEqual("PARTIAL_REVISION_GRAPH_REPAIRED", course["status"])
        self.assertEqual(revision["revision_id"], course["revision_id"])
        self.assertEqual(1, course["created_jobs"])
        self.assertEqual(examiner_id, course["jobs"]["examiner_revision"])

    def test_concurrent_revision_refillers_share_one_attempt_reservation(self) -> None:
        self._complete_kickoff()
        first = seed_next_csdiy_course_batches(self.database, self.jobs)
        jobs = first["courses"][self.course_id]["jobs"]
        self._complete(jobs["materializer"], "course-unit-materialization")
        self._complete(jobs["student"], "student-course-unit-attempt")
        self._complete(
            jobs["examiner"],
            "independent-course-unit-evaluation",
            evaluation_result="REVISE",
        )
        barrier = threading.Barrier(2)
        original_new_revision = course_progression._new_revision_snapshot

        def synchronized_revision(*args: object, **kwargs: object) -> dict[str, object]:
            snapshot = original_new_revision(*args, **kwargs)
            barrier.wait(timeout=10)
            return snapshot

        with patch.object(
            course_progression,
            "_new_revision_snapshot",
            side_effect=synchronized_revision,
        ):
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [
                    pool.submit(
                        seed_next_csdiy_course_batches,
                        self.database,
                        self.jobs,
                        max_revisions=2,
                    )
                    for _ in range(2)
                ]
                results = [future.result(timeout=20) for future in futures]

        courses = [result["courses"][self.course_id] for result in results]
        self.assertEqual(1, len({course["revision_id"] for course in courses}))
        self.assertEqual(2, sum(result["created_jobs"] for result in results))
        with self.database.connect() as connection:
            reservations = connection.execute(
                """
                SELECT revision_id FROM course_progression_revision_reservations
                WHERE course_id=? AND source_id='source_csdiy'
                  AND source_commit_hash='course-commit-1'
                  AND sequence=1 AND attempt_number=2
                """,
                (self.course_id,),
            ).fetchall()
        self.assertEqual(1, len(reservations))
        self.assertEqual(courses[0]["revision_id"], reservations[0]["revision_id"])

    def test_tampered_durable_snapshot_fails_closed(self) -> None:
        self._complete_kickoff()
        first = seed_next_csdiy_course_batches(self.database, self.jobs)
        materializer_id = first["courses"][self.course_id]["jobs"]["materializer"]
        materializer = self.jobs.get(materializer_id)
        assert materializer is not None
        payload = materializer["payload"]
        payload["batch_snapshot"]["completion_scope"]["course_completion"] = "COMPLETE"
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                "UPDATE jobs SET payload_json=? WHERE job_id=?",
                (canonical_json(payload), materializer_id),
            )

        rejected = seed_next_csdiy_course_batches(self.database, self.jobs)
        course = rejected["courses"][self.course_id]
        self.assertEqual("PROGRESSION_EVIDENCE_INVALID", course["status"])
        self.assertEqual("batch snapshot checksum mismatch", course["reason"])
        self.assertEqual(0, rejected["created_jobs"])

    def test_existing_graph_missing_backend_gate_dependency_fails_closed(self) -> None:
        self._complete_kickoff()
        first = seed_next_csdiy_course_batches(self.database, self.jobs)
        student_id = first["courses"][self.course_id]["jobs"]["student"]
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                """
                DELETE FROM job_dependencies
                WHERE job_id=? AND depends_on_job_id=?
                """,
                (student_id, CODEX_BACKEND_GATE_JOB_ID),
            )
        with self.assertRaisesRegex(RuntimeError, "dependency mismatch"):
            seed_next_csdiy_course_batches(self.database, self.jobs)

    def test_material_and_student_contracts_are_externally_validatable(self) -> None:
        self._complete_kickoff()
        seeded = seed_next_csdiy_course_batches(self.database, self.jobs)
        graph = seeded["courses"][self.course_id]["jobs"]
        materializer = self.jobs.get(graph["materializer"])
        student = self.jobs.get(graph["student"])
        assert materializer is not None and student is not None
        snapshot = materializer["payload"]["batch_snapshot"]

        material_workspace = self.root / "material-validation"
        for relative, content in {
            "BATCH_MANIFEST.json": canonical_json(
                {
                    "course_id": self.course_id,
                    "batch_id": snapshot["batch_id"],
                    "sequence": snapshot["sequence"],
                    "status": "BOUNDED_UNIT_PREPARED",
                    "course_completion": "NOT_CLAIMED",
                    "unit_ids": ["unit_lab_one"],
                    "availability": ["metadata recorded"],
                    "blocked": [],
                    "completion_policy": {"scope": "this batch"},
                    "provenance": {"classification": "agent-generated"},
                }
            ),
            "student_safe/UNIT_BRIEF.md": "brief\n",
            "student_safe/LEARNING_TASK.md": "task\n",
            "student_safe/SELF_CHECK.md": "questions\n",
            "examiner_only/RUBRIC.md": "rubric\n",
            "examiner_only/NOVEL_CHECK.md": "withheld check\n",
        }.items():
            target = material_workspace / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        validator = Validator(self.database)
        material_results = validator.run(
            graph["materializer"],
            material_workspace,
            materializer["payload"]["validators"],
            self.root / "material-validator-logs",
        )
        self.assertTrue(all(result.passed for result in material_results))

        student_workspace = self.root / "student-validation"
        for name in ("notes.md", "submission.md", "debugging-log.md", "self-check.md"):
            target = student_workspace / "student_work" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("student evidence\n", encoding="utf-8")
        student_results = validator.run(
            graph["student"],
            student_workspace,
            student["payload"]["validators"],
            self.root / "student-validator-logs",
        )
        self.assertTrue(all(result.passed for result in student_results))
        (student_workspace / "student_work" / "RuBrIc.md").write_text(
            "leak\n", encoding="utf-8"
        )
        leaked = validator.run(
            graph["student"],
            student_workspace,
            student["payload"]["validators"],
            self.root / "student-leak-validator-logs",
        )
        self.assertEqual("FAIL", leaked[1].status)

    def test_succeeded_preparation_without_verified_artifact_cannot_unlock_work(self) -> None:
        self._complete_kickoff(archive_preparation=False)
        result = seed_next_csdiy_course_batches(self.database, self.jobs)
        course = result["courses"][self.course_id]
        self.assertEqual("WAITING_FOR_VERIFIED_PREPARATION", course["status"])
        self.assertEqual(0, result["created_jobs"])

    def test_stale_preparation_is_not_reused_after_source_commit_changes(self) -> None:
        self._complete_kickoff()
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                "UPDATE sources SET commit_hash='course-commit-2' WHERE source_id='source_csdiy'"
            )
        result = seed_next_csdiy_course_batches(self.database, self.jobs)
        self.assertEqual(
            "KICKOFF_PREPARATION_STALE",
            result["courses"][self.course_id]["status"],
        )
        self.assertEqual(0, result["created_jobs"])

    def test_limit_and_cli_are_explicit(self) -> None:
        with self.assertRaises(ValueError):
            seed_next_csdiy_course_batches(self.database, self.jobs, max_courses=0)
        for invalid in (-1, 11, True):
            with self.subTest(max_revisions=invalid), self.assertRaises(ValueError):
                seed_next_csdiy_course_batches(
                    self.database,
                    self.jobs,
                    max_revisions=invalid,
                )
        parsed = build_parser().parse_args(
            [
                "seed-course-next",
                "--course-id",
                self.course_id,
                "--max-courses",
                "7",
                "--max-revisions",
                "3",
            ]
        )
        self.assertIs(cmd_seed_course_next, parsed.func)
        self.assertEqual([self.course_id], parsed.course_id)
        self.assertEqual(7, parsed.max_courses)
        self.assertEqual(3, parsed.max_revisions)

    def test_max_courses_bounds_new_graphs_without_hiding_deferred_courses(self) -> None:
        self._complete_kickoff()
        second_course = "course_systems_102"
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                """
                INSERT INTO courses(
                    course_id,source_id,slug,institution,title,topic,description,
                    prerequisites_json,estimated_human_hours,difficulty,
                    source_metadata_json,status
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    second_course,
                    "source_csdiy",
                    "systems-102",
                    "Example University",
                    "Systems Engineering 102",
                    "systems",
                    "Another normalized course.",
                    "[]",
                    80.0,
                    7.0,
                    "{}",
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
                    "unit_second_course",
                    second_course,
                    "lab",
                    1,
                    "Second course lab",
                    "[]",
                    "courses/systems-102.en.md#L1",
                    canonical_json({"official_course_unit": True}),
                ),
            )
        second = seed_all_csdiy_course_cohorts(self.database, self.jobs)["cohorts"][
            second_course
        ]
        self._complete(
            second["preparation"],
            "course-preparation",
            {
                "COURSE_MANIFEST.json": "{}\n",
                "UNIT_GRAPH.json": "{}\n",
                "MATERIAL_AVAILABILITY.json": "{}\n",
            },
        )
        self._complete(second["student"], "student-course-attempt")
        self._complete(
            second["examiner"],
            "independent-course-evaluation",
        )

        bounded = seed_next_csdiy_course_batches(
            self.database, self.jobs, max_courses=1
        )
        self.assertEqual(1, bounded["scheduled_courses"])
        self.assertEqual(3, bounded["created_jobs"])
        self.assertEqual(
            "BOUNDED_BATCH_GRAPH_SEEDED",
            bounded["courses"][self.course_id]["status"],
        )
        self.assertEqual(
            "DEFERRED_BY_LIMIT",
            bounded["courses"][second_course]["status"],
        )

    def test_concurrent_refillers_share_one_authoritative_sequence_reservation(self) -> None:
        self._complete_kickoff()
        barrier = threading.Barrier(2)
        original_new_snapshot = course_progression._new_batch_snapshot

        def distinct_learner_snapshot(database: Database) -> dict[str, object]:
            del database
            return {
                "student_id": "student-target",
                "persona": "target",
                "profile": {},
                "current_state": {},
                "knowledge": [],
                "concurrent_reader": threading.current_thread().name,
            }

        def synchronized_new_snapshot(*args: object, **kwargs: object) -> dict[str, object]:
            snapshot = original_new_snapshot(*args, **kwargs)
            barrier.wait(timeout=10)
            return snapshot

        with patch.object(
            course_progression,
            "_learner_snapshot",
            side_effect=distinct_learner_snapshot,
        ), patch.object(
            course_progression,
            "_new_batch_snapshot",
            side_effect=synchronized_new_snapshot,
        ):
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [
                    pool.submit(
                        seed_next_csdiy_course_batches,
                        self.database,
                        self.jobs,
                    )
                    for _ in range(2)
                ]
                results = [future.result(timeout=20) for future in futures]

        courses = [result["courses"][self.course_id] for result in results]
        self.assertEqual(1, len({course["batch_id"] for course in courses}))
        self.assertEqual(3, sum(result["created_jobs"] for result in results))
        with self.database.connect() as connection:
            reservations = connection.execute(
                """
                SELECT batch_id,batch_snapshot_json
                FROM course_progression_reservations
                WHERE course_id=? AND source_id='source_csdiy'
                  AND source_commit_hash='course-commit-1' AND sequence=1
                """,
                (self.course_id,),
            ).fetchall()
            progression_jobs = connection.execute(
                """
                SELECT COUNT(*) AS n FROM jobs
                WHERE json_extract(payload_json,'$.seed_policy.kind')=?
                  AND json_extract(payload_json,'$.course_id')=?
                """,
                (COURSE_PROGRESSION_POLICY_KIND, self.course_id),
            ).fetchone()["n"]
        self.assertEqual(1, len(reservations))
        self.assertEqual(courses[0]["batch_id"], reservations[0]["batch_id"])
        self.assertEqual(
            courses[0]["batch_id"],
            json.loads(reservations[0]["batch_snapshot_json"])["batch_id"],
        )
        self.assertEqual(3, progression_jobs)

    def test_scheduler_run_automatically_refills_eligible_course(self) -> None:
        self._complete_kickoff()
        sentinel = self.jobs.create(
            "fake",
            "test",
            {
                "files": {"sentinel.txt": "completed\n"},
                "validators": [
                    {
                        "type": "regular_files",
                        "name": "automatic-refill-sentinel",
                        "paths": ["sentinel.txt"],
                        "minimum_bytes": 1,
                    }
                ],
                "artifact_type": "automatic-refill-test",
                "artifact_path": "tests/automatic-refill",
            },
            job_id="job_automatic_refill_sentinel",
            priority=1_000,
            max_attempts=1,
        )
        self.jobs.promote_eligible()
        config_path = self.root / "automatic-refill.toml"
        config_path.write_text(
            "\n".join(
                [
                    "[factory]",
                    f'database = "{self.database.path}"',
                    f'warehouse = "{self.root / "warehouse"}"',
                    "lease_seconds = 5",
                    "heartbeat_seconds = 0.05",
                    "poll_seconds = 0.01",
                    "max_concurrency = 1",
                    "shutdown_grace_seconds = 1",
                    "[backend]",
                    'name = "exec"',
                    'command = "codex"',
                    'model = "gpt-5.6-sol"',
                    'reasoning_effort = "ultra"',
                    "timeout_seconds = 5",
                    "[limits]",
                    "test = 1",
                    "[retry]",
                    "base_seconds = 0.01",
                    "max_seconds = 0.02",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        settings = load_settings(config_path)

        dispatched = asyncio.run(
            run_scheduler(
                settings,
                self.database,
                until_idle=True,
                max_jobs=1,
            )
        )

        self.assertEqual(1, dispatched)
        self.assertEqual("SUCCEEDED", self.jobs.get(sentinel)["state"])
        with self.database.connect() as connection:
            roles = {
                str(row["role"]): str(row["state"])
                for row in connection.execute(
                    """
                    SELECT json_extract(payload_json,'$.seed_policy.role') AS role,state
                    FROM jobs
                    WHERE json_extract(payload_json,'$.seed_policy.kind')=?
                      AND json_extract(payload_json,'$.course_id')=?
                    """,
                    (COURSE_PROGRESSION_POLICY_KIND, self.course_id),
                )
            }
            refill_events = connection.execute(
                "SELECT COUNT(*) AS n FROM events WHERE type='COURSE_PROGRESSION_REFILLED'"
            ).fetchone()["n"]
        self.assertEqual(
            {"materializer": "READY", "student": "DISCOVERED", "examiner": "DISCOVERED"},
            roles,
        )
        self.assertEqual(1, refill_events)


if __name__ == "__main__":
    unittest.main()
