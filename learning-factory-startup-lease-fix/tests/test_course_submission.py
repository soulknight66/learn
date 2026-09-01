from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from unittest.mock import patch

import learnfactory.course_submission as course_submission
from learnfactory.course_submission import (
    EXAMINER_SUBMISSION_LIMITS,
    SUBMISSION_DESTINATION,
    StudentSubmissionLimits,
    parse_student_submission_binding,
    project_student_submission,
    submission_binding_evidence,
    student_submission_binding_payload,
)
from learnfactory.db import Database
from learnfactory.course_progression import seed_next_csdiy_course_batches
from learnfactory.jobs import JobRepository
from learnfactory.learners import (
    effective_learner_concepts,
    invalidate_legacy_csdiy_learner_evidence,
    record_validated_attempt,
    seed_students,
    unambiguous_examiner_evaluation_result,
)
from learnfactory.seeding import (
    COURSE_EXAMINER_REMEDIATION_POLICY_VERSION,
    seed_all_csdiy_course_cohorts,
    seed_codex_backend_gate,
)
from learnfactory.util import canonical_json, file_sha256, tree_sha256
from learnfactory.workspace import WorkspaceError


ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "migrations"


class StudentSubmissionProjectionTests(unittest.TestCase):
    def test_projection_preserves_code_tests_and_omits_mutable_state(self) -> None:
        with tempfile.TemporaryDirectory(prefix="submission-projection-") as raw:
            root = Path(raw)
            source = root / "source" / "student_work"
            (source / "src").mkdir(parents=True)
            (source / "tests").mkdir()
            (source / "build").mkdir()
            (source / "src/server.py").write_text("print('server')\n", encoding="utf-8")
            (source / "tests/test_server.py").write_text("assert True\n", encoding="utf-8")
            (source / "notes.md").write_text("notes\n", encoding="utf-8")
            (source / "build/server.o").write_text("object\n", encoding="utf-8")

            destination = root / "projection"
            evidence = project_student_submission(source.parent, destination)

            self.assertTrue((destination / "src/server.py").is_file())
            self.assertTrue((destination / "tests/test_server.py").is_file())
            self.assertFalse((destination / "build").exists())
            self.assertEqual("student_work", evidence["source_prefix"])
            self.assertEqual(2, evidence["code_file_count"])
            self.assertEqual(1, evidence["test_file_count"])
            self.assertRegex(evidence["paths_manifest_sha256"], r"^[0-9a-f]{64}$")

    def test_projection_rejects_examiner_or_reference_material(self) -> None:
        with tempfile.TemporaryDirectory(prefix="submission-separation-") as raw:
            source = Path(raw) / "source"
            (source / "src").mkdir(parents=True)
            (source / "sealed").mkdir()
            (source / "src/main.py").write_text("print('ok')\n", encoding="utf-8")
            (source / "sealed/answer.py").write_text("answer = 42\n", encoding="utf-8")
            with self.assertRaisesRegex(
                WorkspaceError, "examiner/reference material"
            ):
                project_student_submission(source, Path(raw) / "projection")

    def test_binding_contract_is_exact_and_versioned(self) -> None:
        raw = student_submission_binding_payload(
            "job_student", "student-course-attempt"
        )
        parsed = parse_student_submission_binding(raw)
        self.assertEqual("job_student", parsed.student_job_id)
        self.assertEqual(SUBMISSION_DESTINATION, parsed.destination)
        malformed = {**raw, "extra": True}
        with self.assertRaisesRegex(ValueError, "invalid shape"):
            parse_student_submission_binding(malformed)

    def test_binding_rejects_a_projection_checksum_mismatch(self) -> None:
        raw = student_submission_binding_payload(
            "job_student", "student-course-attempt"
        )
        staged = {
            "path": SUBMISSION_DESTINATION,
            "kind": "directory",
            "checksum_algorithm": "tree-sha256-v2",
            "checksum": "1" * 64,
            "origin": "dependency-artifact",
            "job_id": "job_student",
            "artifact_id": "artifact_student",
            "artifact_type": "student-course-attempt",
            "artifact_checksum": "2" * 64,
            "artifact_checksum_algorithm": "tree-sha256-v2",
            "artifact_attempt": 1,
            "artifact_subpath": ".",
            "student_submission_projection": {
                "projected_checksum_algorithm": "tree-sha256-v2",
                "projected_checksum": "3" * 64,
                "paths_manifest_sha256": "4" * 64,
            },
        }
        with self.assertRaisesRegex(ValueError, "projection evidence is inconsistent"):
            submission_binding_evidence(raw, [staged])

    def test_examiner_entry_limit_fails_before_retaining_or_copying_4097th(self) -> None:
        with tempfile.TemporaryDirectory(prefix="submission-entry-bound-") as raw:
            root = Path(raw)
            source = root / "source" / "student_work"
            source.mkdir(parents=True)
            for index in range(EXAMINER_SUBMISSION_LIMITS.max_entries + 1):
                (source / f"entry-{index:04d}.txt").touch()

            admitted_names: list[str] = []
            original_name_check = course_submission._submission_name

            def observe_name(name: str) -> None:
                original_name_check(name)
                if name != "student_work":
                    admitted_names.append(name)

            destination = root / "projection"
            with mock.patch.object(
                course_submission,
                "_submission_name",
                side_effect=observe_name,
            ), mock.patch.object(
                course_submission,
                "_copy_submission_file",
                wraps=course_submission._copy_submission_file,
            ) as copied, self.assertRaisesRegex(WorkspaceError, "maximum entries"):
                project_student_submission(
                    source.parent,
                    destination,
                    limits=EXAMINER_SUBMISSION_LIMITS,
                )

            self.assertEqual(EXAMINER_SUBMISSION_LIMITS.max_entries, len(admitted_names))
            self.assertEqual(len(admitted_names), len(set(admitted_names)))
            copied.assert_not_called()
            self.assertFalse(destination.exists())

    def test_examiner_preflight_rejects_large_total_and_deep_trees_before_copy(self) -> None:
        cases = {
            "single-file": (
                StudentSubmissionLimits(10, 10, 20, 4, 5),
                {"large.txt": b"12345"},
            ),
            "aggregate": (
                StudentSubmissionLimits(10, 10, 5, 4, 5),
                {"a.txt": b"123", "b.txt": b"456"},
            ),
        }
        with tempfile.TemporaryDirectory(prefix="submission-byte-bound-") as raw:
            base = Path(raw)
            for case, (limits, files) in cases.items():
                source = base / case / "source" / "student_work"
                source.mkdir(parents=True)
                for relative, content in files.items():
                    (source / relative).write_bytes(content)
                destination = base / case / "projection"
                with self.subTest(case=case), mock.patch.object(
                    course_submission,
                    "_copy_submission_file",
                    wraps=course_submission._copy_submission_file,
                ) as copied, self.assertRaises(WorkspaceError):
                    project_student_submission(
                        source.parent, destination, limits=limits
                    )
                copied.assert_not_called()
                self.assertFalse(destination.exists())

            deep_source = base / "depth" / "source" / "student_work"
            (deep_source / "one" / "two" / "three").mkdir(parents=True)
            (deep_source / "one" / "two" / "three" / "answer.txt").touch()
            destination = base / "depth" / "projection"
            limits = StudentSubmissionLimits(20, 10, 20, 20, 2)
            with mock.patch.object(
                course_submission,
                "_copy_submission_file",
                wraps=course_submission._copy_submission_file,
            ) as copied, self.assertRaisesRegex(WorkspaceError, "depth"):
                project_student_submission(
                    deep_source.parent, destination, limits=limits
                )
            copied.assert_not_called()
            self.assertFalse(destination.exists())

    def test_projection_rejects_hardlinks_and_strips_special_mode_bits(self) -> None:
        with tempfile.TemporaryDirectory(prefix="submission-hardlink-") as raw:
            root = Path(raw)
            source = root / "source" / "student_work"
            source.mkdir(parents=True)
            candidate = source / "answer.txt"
            candidate.write_text("answer\n", encoding="utf-8")
            os.link(candidate, root / "external-alias")
            destination = root / "projection"
            with self.assertRaisesRegex(WorkspaceError, "hard-link"):
                project_student_submission(source.parent, destination)
            self.assertFalse(destination.exists())

            (root / "external-alias").unlink()
            candidate.chmod(0o6755)
            evidence = project_student_submission(source.parent, destination)
            self.assertEqual(1, evidence["regular_file_count"])
            self.assertEqual(0o555, destination.joinpath("answer.txt").stat().st_mode & 0o7777)

    def test_projection_detects_root_and_directory_rename_races(self) -> None:
        with tempfile.TemporaryDirectory(prefix="submission-rename-race-") as raw:
            base = Path(raw)
            for race in ("root", "directory"):
                source = base / race / "source"
                student = source / "student_work"
                nested = student / "nested"
                nested.mkdir(parents=True)
                (nested / "answer.txt").write_text("answer\n", encoding="utf-8")
                destination = base / race / "projection"
                original_copy = course_submission._copy_submission_file
                raced = False

                def rename_after_copy(*args: object, **kwargs: object):
                    nonlocal raced
                    result = original_copy(*args, **kwargs)
                    if not raced:
                        raced = True
                        target = source if race == "root" else nested
                        target.rename(target.with_name(target.name + "-retired"))
                        target.mkdir()
                    return result

                with self.subTest(race=race), mock.patch.object(
                    course_submission,
                    "_copy_submission_file",
                    side_effect=rename_after_copy,
                ), self.assertRaises(WorkspaceError):
                    project_student_submission(source, destination)
                self.assertTrue(raced)
                self.assertFalse(destination.exists())


class CourseExaminerRemediationSeedingTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="course-examiner-remediation-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.database = Database(self.root / "factory.db", MIGRATIONS)
        self.database.migrate()
        self.jobs = JobRepository(self.database)
        seed_students(self.database, self.root / "warehouse")
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                """
                INSERT INTO sources(
                    source_id,type,name,path,upstream_url,commit_hash,license,
                    ingested_at,metadata_json,is_active
                ) VALUES ('source_csdiy','course_catalog','CSDIY','/public/csdiy',
                          'https://example.test/csdiy','commit-1','CC-BY-SA-4.0',1,
                          '{"adapter":"csdiy"}',1)
                """
            )
            connection.execute(
                """
                INSERT INTO courses(
                    course_id,source_id,slug,institution,title,topic,description,
                    prerequisites_json,estimated_human_hours,difficulty,
                    source_metadata_json,status
                ) VALUES ('course_remediation','source_csdiy','remediation','Example',
                          'Remediation Course','systems','test','[]',10,5,'{}','DISCOVERED')
                """
            )
        seed_codex_backend_gate(self.jobs)

    def _succeed_with_artifact(
        self, job_id: str, artifact_type: str, files: dict[str, str]
    ) -> Path:
        artifact_path = self.root / "warehouse" / "artifacts" / "fixtures" / job_id
        artifact_path.mkdir(parents=True)
        for relative, content in files.items():
            target = artifact_path / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        with self.database.transaction(immediate=True) as connection:
            connection.execute("UPDATE jobs SET state='READY' WHERE job_id=?", (job_id,))
            connection.execute(
                """
                UPDATE jobs SET state='CLAIMED',attempt_count=1,owner='test',
                    lease_token='lease',lease_expires_at=10,heartbeat_at=1,
                    started_at=1 WHERE job_id=?
                """,
                (job_id,),
            )
            connection.execute("UPDATE jobs SET state='RUNNING' WHERE job_id=?", (job_id,))
            connection.execute(
                """
                UPDATE jobs SET state='SUCCEEDED',owner=NULL,lease_token=NULL,
                    lease_expires_at=NULL,finished_at=2 WHERE job_id=?
                """,
                (job_id,),
            )
            connection.execute(
                """
                INSERT INTO artifacts(
                    artifact_id,job_id,type,path,checksum,metadata_json,created_at,
                    validation_status,attempt_number,checksum_algorithm,integrity_status
                ) VALUES (?,?,?,?,?,'{}',2,'GENERATED',1,'tree-sha256-v2','VERIFIED_V2')
                """,
                (
                    f"artifact_{job_id}",
                    job_id,
                    artifact_type,
                    str(artifact_path),
                    tree_sha256(artifact_path),
                ),
            )
        return artifact_path

    def test_existing_v1_examiner_is_preserved_and_v2_is_idempotent(self) -> None:
        legacy_id = "job_csdiy_remediation_examiner_v1"
        legacy_payload = {
            "seed_policy": {
                "kind": "csdiy_course_cohort",
                "version": 1,
                "role": "examiner",
            },
            "course_id": "course_remediation",
            "legacy": "narrative-only",
        }
        self.jobs.create(
            "codex_task",
            "examiner",
            legacy_payload,
            job_id=legacy_id,
            model="gpt-5.6-sol",
            reasoning_effort="ultra",
        )
        before = self.jobs.get(legacy_id)

        first = seed_all_csdiy_course_cohorts(self.database, self.jobs)
        graph = first["cohorts"]["course_remediation"]
        self.assertEqual(
            "job_csdiy_remediation_examiner_v2", graph["examiner"]
        )
        self.assertEqual(3, first["created_jobs"])
        self.assertEqual(before["payload"], self.jobs.get(legacy_id)["payload"])
        self.assertEqual("CANCELLED", self.jobs.get(legacy_id)["state"])
        remediation = self.jobs.get(graph["examiner"])
        self.assertEqual(
            COURSE_EXAMINER_REMEDIATION_POLICY_VERSION,
            remediation["payload"]["seed_policy"]["version"],
        )
        self.assertEqual(
            legacy_id,
            remediation["payload"]["provenance"]["remediation"][
                "supersedes_examiner_job_id"
            ],
        )

        second = seed_all_csdiy_course_cohorts(self.database, self.jobs)
        self.assertEqual(0, second["created_jobs"])
        self.assertEqual(graph, second["cohorts"]["course_remediation"])
        with self.database.connect() as connection:
            self.assertEqual(
                1,
                connection.execute(
                    """
                    SELECT COUNT(*) AS n FROM events
                    WHERE job_id=? AND type='JOB_SUPERSEDED'
                    """,
                    (legacy_id,),
                ).fetchone()["n"],
            )

    def test_active_legacy_course_job_is_not_cancelled(self) -> None:
        legacy_id = "job_csdiy_remediation_student_target_v1"
        self.jobs.create(
            "codex_task",
            "student",
            {
                "seed_policy": {
                    "kind": "csdiy_course_cohort",
                    "version": 1,
                    "role": "student",
                },
                "course_id": "course_remediation",
                "student_id": "student-target",
            },
            job_id=legacy_id,
            model="gpt-5.6-sol",
            reasoning_effort="ultra",
        )
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                "UPDATE jobs SET state='READY' WHERE job_id=?", (legacy_id,)
            )
            connection.execute(
                """
                UPDATE jobs SET state='CLAIMED',attempt_count=1,owner='active-worker',
                    lease_token='active-lease',lease_expires_at=99999999999,
                    heartbeat_at=1 WHERE job_id=?
                """,
                (legacy_id,),
            )

        seeded = seed_all_csdiy_course_cohorts(self.database, self.jobs)
        active = self.jobs.get(legacy_id)
        assert active is not None
        self.assertEqual("CLAIMED", active["state"])
        self.assertFalse(active["cancel_requested"])
        self.assertNotEqual(
            legacy_id,
            seeded["cohorts"]["course_remediation"]["student"],
        )
        with self.database.connect() as connection:
            self.assertEqual(
                0,
                connection.execute(
                    """
                    SELECT COUNT(*) AS n FROM events
                    WHERE job_id=? AND type='JOB_SUPERSEDED'
                    """,
                    (legacy_id,),
                ).fetchone()["n"],
            )

    def test_unbound_legacy_examiner_result_is_never_authoritative(self) -> None:
        legacy_id = "job_csdiy_remediation_examiner_v1"
        payload = {
            "seed_policy": {
                "kind": "csdiy_course_cohort",
                "version": 1,
                "role": "examiner",
            },
            "learner_evidence": {
                "schema_version": 1,
                "student_id": "student-target",
                "student_job_id": "job_legacy_student",
                "student_artifact_type": "student-course-attempt",
                "task_id": "legacy-kickoff",
                "task_type": "course-kickoff",
                "attempt_number": 1,
                "evaluator": "legacy examiner",
                "evaluation_path": "evaluation.json",
                "schema_validator": "legacy-schema",
                "rubric": {"scope": "legacy"},
                "concepts": [
                    {
                        "concept": "legacy",
                        "description": "legacy",
                        "kind": "legacy",
                        "source_reference": None,
                        "result_weights": {
                            "PASS": 0.1,
                            "REVISE": 0.0,
                            "FAIL": -0.1,
                        },
                    }
                ],
            },
        }
        self.jobs.create(
            "codex_task",
            "examiner",
            payload,
            job_id=legacy_id,
            model="gpt-5.6-sol",
            reasoning_effort="ultra",
        )
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                "UPDATE jobs SET state='READY' WHERE job_id=?",
                (legacy_id,),
            )
            connection.execute(
                """
                UPDATE jobs SET state='CLAIMED',attempt_count=1,owner='test',
                    lease_token='lease',lease_expires_at=10,heartbeat_at=1
                WHERE job_id=?
                """,
                (legacy_id,),
            )
            connection.execute(
                "UPDATE jobs SET state='RUNNING' WHERE job_id=?",
                (legacy_id,),
            )
            connection.execute(
                """
                UPDATE jobs SET state='SUCCEEDED',owner=NULL,lease_token=NULL,
                    lease_expires_at=NULL WHERE job_id=?
                """,
                (legacy_id,),
            )
        with self.database.connect() as connection:
            self.assertIsNone(
                unambiguous_examiner_evaluation_result(connection, legacy_id)
            )

    def test_completed_narrative_v1_chain_gets_new_student_and_examiner(self) -> None:
        preparation = "job_csdiy_remediation_prepare_v1"
        legacy_student = "job_csdiy_remediation_student_target_v1"
        legacy_examiner = "job_csdiy_remediation_examiner_v1"
        self.jobs.create(
            "codex_task",
            "course_manager",
            {
                "seed_policy": {
                    "kind": "csdiy_course_cohort",
                    "version": 1,
                    "role": "preparation",
                },
                "course_id": "course_remediation",
                "course_snapshot": {
                    "source": {"commit_hash": "commit-1"}
                },
            },
            job_id=preparation,
            model="gpt-5.6-sol",
            reasoning_effort="ultra",
        )
        self.jobs.create(
            "codex_task",
            "student",
            {
                "seed_policy": {
                    "kind": "csdiy_course_cohort",
                    "version": 1,
                    "role": "student",
                },
                "course_id": "course_remediation",
                "student_id": "student-target",
            },
            job_id=legacy_student,
            dependencies=[preparation],
            model="gpt-5.6-sol",
            reasoning_effort="ultra",
        )
        legacy_evidence = {
            "schema_version": 1,
            "student_id": "student-target",
            "student_job_id": legacy_student,
            "student_artifact_type": "student-course-attempt",
            "task_id": "course_remediation-kickoff-v1",
            "task_type": "course-kickoff",
            "attempt_number": 1,
            "evaluator": "legacy narrative examiner",
            "evaluation_path": "evaluation.json",
            "schema_validator": "legacy-schema",
            "rubric": {"scope": "legacy"},
            "concepts": [
                {
                    "concept": "legacy",
                    "description": "legacy",
                    "kind": "legacy",
                    "source_reference": None,
                    "result_weights": {
                        "PASS": 0.1,
                        "REVISE": 0.0,
                        "FAIL": -0.1,
                    },
                }
            ],
        }
        self.jobs.create(
            "codex_task",
            "examiner",
            {
                "seed_policy": {
                    "kind": "csdiy_course_cohort",
                    "version": 1,
                    "role": "examiner",
                },
                "course_id": "course_remediation",
                "learner_evidence": legacy_evidence,
            },
            job_id=legacy_examiner,
            dependencies=[preparation, legacy_student],
            model="gpt-5.6-sol",
            reasoning_effort="ultra",
        )
        self._succeed_with_artifact(
            preparation,
            "course-preparation",
            {
                "student_safe/COURSE_BRIEF.md": "brief\n",
                "student_safe/STUDY_TASK.md": "task\n",
                "student_safe/COMPREHENSION.md": "questions\n",
                "examiner_only/RUBRIC.md": "rubric\n",
            },
        )
        self._succeed_with_artifact(
            legacy_student,
            "student-course-attempt",
            {
                "notes.md": "claims code exists\n",
                "submission.md": "all tests passed\n",
                "debugging-log.md": "no source was archived\n",
            },
        )
        evaluation_path = self._succeed_with_artifact(
            legacy_examiner,
            "independent-course-evaluation",
            {"evaluation.json": '{"result":"PASS"}\n', "feedback.md": "pass\n"},
        )
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                """
                INSERT INTO attempts(
                    attempt_id,student_id,task_id,task_type,attempt_number,
                    start_time,end_time,result,workspace
                ) VALUES ('attempt_legacy','student-target',?,'course-kickoff',1,1,2,
                          'PASS',?)
                """,
                (legacy_evidence["task_id"], str(evaluation_path)),
            )
            connection.execute(
                """
                INSERT INTO evaluations(
                    evaluation_id,attempt_id,evaluator,rubric_json,result,score,
                    evidence_json,created_at
                ) VALUES ('evaluation_legacy','attempt_legacy',?,?,'PASS',99,?,2)
                """,
                (
                    legacy_evidence["evaluator"],
                    canonical_json(legacy_evidence["rubric"]),
                    canonical_json({"legacy": "narrative-only PASS"}),
                ),
            )

        first = seed_all_csdiy_course_cohorts(self.database, self.jobs)
        graph = first["cohorts"]["course_remediation"]
        self.assertEqual(2, first["created_jobs"])
        self.assertEqual(
            "job_csdiy_remediation_student_target_v2", graph["student"]
        )
        self.assertEqual("job_csdiy_remediation_examiner_v2", graph["examiner"])
        with self.database.connect() as connection:
            self.assertIsNone(
                unambiguous_examiner_evaluation_result(connection, legacy_examiner)
            )
            examiner_dependencies = {
                row["depends_on_job_id"]
                for row in connection.execute(
                    "SELECT depends_on_job_id FROM job_dependencies WHERE job_id=?",
                    (graph["examiner"],),
                )
            }
            self.assertEqual(1, connection.execute(
                "SELECT COUNT(*) AS n FROM evaluations WHERE evaluation_id='evaluation_legacy'"
            ).fetchone()["n"])
        self.assertEqual(
            {preparation, graph["student"]}, examiner_dependencies
        )
        self.assertNotIn(legacy_student, examiner_dependencies)
        waiting = seed_next_csdiy_course_batches(self.database, self.jobs)
        self.assertEqual(
            "WAITING_FOR_VERIFIED_KICKOFF_EXAMINER",
            waiting["courses"]["course_remediation"]["status"],
        )
        repeated = seed_all_csdiy_course_cohorts(self.database, self.jobs)
        self.assertEqual(0, repeated["created_jobs"])

    def test_legacy_learner_evidence_is_invalidated_and_v2_is_append_only(self) -> None:
        legacy_examiner = "job_csdiy_remediation_examiner_v1"
        concept = "course-kickoff:course_remediation"
        concept_description = "Legacy kickoff concept."
        evaluator = "legacy narrative examiner"
        legacy_task = "course_remediation-kickoff-examiner-v1"
        learner_policy = {
            "schema_version": 1,
            "student_id": "student-target",
            "student_job_id": "job_csdiy_remediation_student_target_v1",
            "student_artifact_type": "student-course-attempt",
            "task_id": legacy_task,
            "task_type": "course-kickoff",
            "attempt_number": 1,
            "evaluator": evaluator,
            "evaluation_path": "evaluation.json",
            "schema_validator": "legacy-schema",
            "rubric": {"scope": "legacy"},
            "concepts": [
                {
                    "concept": concept,
                    "description": concept_description,
                    "kind": "independent-course-examiner",
                    "source_reference": "course_remediation",
                    "result_weights": {
                        "PASS": 0.3,
                        "REVISE": 0.05,
                        "FAIL": -0.25,
                    },
                }
            ],
        }
        self.jobs.create(
            "codex_task",
            "examiner",
            {
                "seed_policy": {
                    "kind": "csdiy_course_cohort",
                    "version": 1,
                    "role": "examiner",
                },
                "course_id": "course_remediation",
                "learner_evidence": learner_policy,
            },
            job_id=legacy_examiner,
            model="gpt-5.6-sol",
            reasoning_effort="ultra",
        )
        legacy_observation = "narrative only"
        legacy_attempt = record_validated_attempt(
            self.database,
            self.root / "warehouse",
            student_id="student-target",
            task_id=legacy_task,
            task_type="course-kickoff",
            attempt_number=1,
            start_time=1.0,
            end_time=2.0,
            result="PASS",
            workspace="/legacy/narrative-only",
            evaluator=evaluator,
            rubric={"scope": "legacy"},
            score=99.0,
            evaluation_evidence={
                "observations": [legacy_observation],
                "examiner_job_id": legacy_examiner,
            },
            concepts=[
                {
                    "concept": concept,
                    "description": (
                        concept_description
                        + " Independent examiner result PASS with score 99. "
                        + f"Observations: {legacy_observation}"
                    ),
                    "kind": "independent-course-examiner",
                    "source_reference": "course_remediation",
                    "weight": 0.3,
                }
            ],
        )
        with self.database.connect() as connection:
            legacy_attempt_before = dict(
                connection.execute(
                    "SELECT * FROM attempts WHERE attempt_id=?", (legacy_attempt,)
                ).fetchone()
            )
            legacy_evaluations_before = [
                dict(row)
                for row in connection.execute(
                    "SELECT * FROM evaluations WHERE attempt_id=? ORDER BY evaluation_id",
                    (legacy_attempt,),
                )
            ]

        seeded = seed_all_csdiy_course_cohorts(self.database, self.jobs)
        self.assertEqual(
            {"attempts": 1, "evidence": 1},
            seeded["invalidated_legacy_learner_evidence"],
        )
        with self.database.connect() as connection:
            self.assertEqual([], effective_learner_concepts(connection, "student-target"))

        v2_examiner = self.jobs.get(
            seeded["cohorts"]["course_remediation"]["examiner"]
        )
        assert v2_examiner is not None
        v2_policy = v2_examiner["payload"]["learner_evidence"]
        v2_concept = v2_policy["concepts"][0]
        observation = "compiled and tested complete tree"
        record_validated_attempt(
            self.database,
            self.root / "warehouse",
            student_id="student-target",
            task_id=v2_policy["task_id"],
            task_type=v2_policy["task_type"],
            attempt_number=1,
            start_time=3.0,
            end_time=4.0,
            result="PASS",
            workspace="/v2/complete-tree",
            evaluator=v2_policy["evaluator"],
            rubric=v2_policy["rubric"],
            score=90.0,
            evaluation_evidence={
                "observations": [observation],
                "examiner_job_id": v2_examiner["job_id"],
            },
            concepts=[
                {
                    "concept": v2_concept["concept"],
                    "description": (
                        v2_concept["description"]
                        + " Independent examiner result PASS with score 90. "
                        + f"Observations: {observation}"
                    ),
                    "kind": v2_concept["kind"],
                    "source_reference": v2_concept["source_reference"],
                    "weight": v2_concept["result_weights"]["PASS"],
                }
            ],
        )
        with self.database.connect() as connection:
            self.assertEqual(
                legacy_attempt_before,
                dict(
                    connection.execute(
                        "SELECT * FROM attempts WHERE attempt_id=?", (legacy_attempt,)
                    ).fetchone()
                ),
            )
            self.assertEqual(
                legacy_evaluations_before,
                [
                    dict(row)
                    for row in connection.execute(
                        "SELECT * FROM evaluations WHERE attempt_id=? ORDER BY evaluation_id",
                        (legacy_attempt,),
                    )
                ],
            )
            self.assertEqual(
                2,
                connection.execute(
                    "SELECT COUNT(*) AS n FROM attempts WHERE student_id='student-target'"
                ).fetchone()["n"],
            )
            effective = effective_learner_concepts(connection, "student-target")
        self.assertEqual(1, len(effective))
        self.assertEqual(1, len(effective[0]["evidence"]))
        self.assertEqual(1, effective[0]["invalidated_evidence_count"])
        rendered = json.loads(
            (
                self.root
                / "warehouse/learners/student-target/KNOWLEDGE.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(1, len(rendered["invalidated_evidence"]))
        self.assertIn(
            "Authority: SUPERSEDED",
            (
                self.root
                / "warehouse/learners/student-target/EXPERIENCE.md"
            ).read_text(encoding="utf-8"),
        )
        repeated = seed_all_csdiy_course_cohorts(self.database, self.jobs)
        self.assertEqual(
            {"attempts": 0, "evidence": 0},
            repeated["invalidated_legacy_learner_evidence"],
        )
        database_hash = file_sha256(self.database.path)
        with patch.object(
            self.database,
            "transaction",
            side_effect=AssertionError("steady-state invalidation acquired a write lock"),
        ):
            self.assertEqual(
                {"attempts": 0, "evidence": 0},
                invalidate_legacy_csdiy_learner_evidence(self.database),
            )
        self.assertEqual(database_hash, file_sha256(self.database.path))


if __name__ == "__main__":
    unittest.main()
