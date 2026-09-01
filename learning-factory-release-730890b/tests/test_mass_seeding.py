from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from learnfactory.cli import build_parser, cmd_seed_all
from learnfactory.db import Database
from learnfactory.jobs import JobRepository
from learnfactory.learners import seed_students
from learnfactory.seeding import (
    BYOX_REVIEW_REMEDIATION_POLICY_VERSION,
    CODEX_BACKEND_GATE_JOB_ID,
    seed_all_catalog_jobs,
)
from learnfactory.util import tree_sha256


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = REPOSITORY_ROOT / "migrations"


class MassCatalogSeedingTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="learnfactory-mass-seed-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.database = Database(self.root / "factory.db", MIGRATIONS)
        self.database.migrate()
        self.jobs = JobRepository(self.database)
        seed_students(self.database, self.root / "warehouse")
        self._insert_exact_catalogs()
        self.specialized_project_id = "project_00000000000000000000000000000000"
        self.specialized_job_id = "job_existing_specialized_builder"
        self._insert_successful_specialized_builder()

    def _insert_exact_catalogs(self) -> None:
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                """
                INSERT INTO sources(
                    source_id,type,name,path,upstream_url,commit_hash,license,
                    ingested_at,metadata_json,is_active
                ) VALUES (?,?,?,?,?,?,?,?,?,1)
                """,
                (
                    "source_csdiy_active",
                    "course_catalog",
                    "CSDIY",
                    "/public/catalogs/csdiy",
                    "https://github.com/PKUFlyingPig/cs-self-learning",
                    "csdiy-commit-1",
                    "CC-BY-SA-4.0",
                    1000.0,
                    json.dumps({"adapter": "cs_self_learning", "extractor_version": "1.0"}),
                ),
            )
            connection.execute(
                """
                INSERT INTO sources(
                    source_id,type,name,path,upstream_url,commit_hash,license,
                    ingested_at,metadata_json,is_active
                ) VALUES (?,?,?,?,?,?,?,?,?,1)
                """,
                (
                    "source_byox_active",
                    "project_catalog",
                    "Build Your Own X",
                    "/public/catalogs/build-your-own-x",
                    "https://github.com/codecrafters-io/build-your-own-x",
                    "byox-commit-1",
                    "CC0-1.0",
                    1001.0,
                    json.dumps({"adapter": "build_your_own_x", "extractor_version": "1.1"}),
                ),
            )
            connection.executemany(
                """
                INSERT INTO courses(
                    course_id,source_id,slug,institution,title,topic,description,
                    prerequisites_json,estimated_human_hours,difficulty,
                    source_metadata_json,status
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                [
                    (
                        f"course_{index:032x}",
                        "source_csdiy_active",
                        f"systems-course-{index}",
                        f"Institution {index % 7}",
                        f"Systems Engineering Course {index}",
                        "systems",
                        "A source-derived catalog description.",
                        "[]",
                        float(20 + index),
                        float(1 + index % 10),
                        json.dumps({"catalog_index": index, "links": [f"https://example.invalid/{index}"]}),
                        "DISCOVERED",
                    )
                    for index in range(82)
                ],
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
                        f"unit_{index:032x}",
                        f"course_{index % 82:032x}",
                        "reading",
                        index // 82,
                        f"Catalog resource {index}",
                        "[]",
                        f"https://example.invalid/resource/{index}",
                        json.dumps({"normalized_resource_link": True}),
                    )
                    for index in range(394)
                ],
            )
            connection.executemany(
                """
                INSERT INTO build_projects(
                    project_id,source_id,slug,title,category,implementation_language,
                    upstream_reference,concepts_json,difficulty,production_relevance,
                    source_format,priority_tier,metadata_json
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                [
                    (
                        f"project_{index:032x}",
                        "source_byox_active",
                        f"build-system-{index}",
                        f"Build System {index}",
                        ("Database" if index % 2 == 0 else "Networking"),
                        ("Rust" if index % 3 == 0 else "C++"),
                        f"https://example.invalid/byox/{index}",
                        json.dumps(["testing", "systems", f"concept-{index % 11}"]),
                        float(3 + index % 8),
                        float(4 + index % 7),
                        "repository",
                        1 + index % 3,
                        json.dumps(
                            {
                                "catalog_index": index,
                                "linked_resource_license": "NOASSERTION",
                            }
                        ),
                    )
                    for index in range(359)
                ],
            )

    def _insert_successful_specialized_builder(self) -> None:
        payload = {
            "project_id": self.specialized_project_id,
            "provenance": {
                "source_id": "source_byox_active",
                "commit": "byox-commit-1",
                "classification": "independently generated specialized vertical slice",
            },
        }
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                """
                INSERT INTO jobs(
                    job_id,type,worker_type,state,priority,score_components_json,
                    payload_json,attempt_count,max_attempts,created_at,finished_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    self.specialized_job_id,
                    "specialized_vertical_slice",
                    "reference_builder",
                    "SUCCEEDED",
                    90.0,
                    "{}",
                    json.dumps(payload, sort_keys=True, separators=(",", ":")),
                    1,
                    2,
                    10.0,
                    20.0,
                ),
            )
            artifact_path = self.root / "specialized-artifact"
            artifact_path.mkdir()
            (artifact_path / "README.md").write_text("validated\n", encoding="utf-8")
            connection.execute(
                """
                INSERT INTO artifacts(
                    artifact_id,job_id,type,path,checksum,metadata_json,created_at,
                    validation_status,attempt_number,checksum_algorithm,integrity_status
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    "artifact_existing_specialized",
                    self.specialized_job_id,
                    "specialized-reference",
                    str(artifact_path),
                    tree_sha256(artifact_path),
                    "{}",
                    20.0,
                    "GENERATED",
                    1,
                    "tree-sha256-v2",
                    "VERIFIED_V2",
                ),
            )

    def _policy_jobs(self, kind: str, role: str) -> list[dict[str, object]]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM jobs ORDER BY job_id"
            ).fetchall()
        result: list[dict[str, object]] = []
        for row in rows:
            payload = json.loads(row["payload_json"])
            if payload.get("seed_policy") == {"kind": kind, "version": 1, "role": role}:
                item = dict(row)
                item["payload"] = payload
                result.append(item)
        return result

    def _dependencies(self, job_id: str) -> set[str]:
        with self.database.connect() as connection:
            return {
                str(row["depends_on_job_id"])
                for row in connection.execute(
                    "SELECT depends_on_job_id FROM job_dependencies WHERE job_id=?",
                    (job_id,),
                )
            }

    def _make_attempted_review(
        self,
        job_id: str,
        state: str,
        *,
        remove_validator: str,
    ) -> str:
        record = self.jobs.get(job_id)
        assert record is not None
        payload = record["payload"]
        payload["validators"] = [
            item
            for item in payload["validators"]
            if item.get("name") != remove_validator
        ]
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                "UPDATE jobs SET payload_json=?,state='READY' WHERE job_id=?",
                (encoded, job_id),
            )
            if state == "READY":
                connection.execute(
                    "UPDATE jobs SET attempt_count=1 WHERE job_id=?", (job_id,)
                )
            elif state == "BLOCKED":
                connection.execute(
                    """
                    UPDATE jobs
                    SET state='BLOCKED',attempt_count=1,failure_kind='test_blocked'
                    WHERE job_id=?
                    """,
                    (job_id,),
                )
            elif state == "CANCELLED":
                connection.execute(
                    """
                    UPDATE jobs
                    SET state='CANCELLED',attempt_count=1,cancel_requested=1
                    WHERE job_id=?
                    """,
                    (job_id,),
                )
            else:
                connection.execute(
                    """
                    UPDATE jobs
                    SET state='CLAIMED',owner='legacy-owner',lease_token=?,
                        lease_expires_at=9999999999,attempt_count=1
                    WHERE job_id=?
                    """,
                    (f"lease-{job_id}", job_id),
                )
                if state == "RUNNING" or state == "SUCCEEDED":
                    connection.execute(
                        "UPDATE jobs SET state='RUNNING' WHERE job_id=?", (job_id,)
                    )
                if state not in {"CLAIMED", "RUNNING"}:
                    connection.execute(
                        """
                        UPDATE jobs
                        SET state=?,owner=NULL,lease_token=NULL,lease_expires_at=NULL,
                            retry_at=CASE WHEN ?='RETRY_WAIT' THEN 9999999999 ELSE NULL END,
                            finished_at=CASE WHEN ? IN ('FAILED','SUCCEEDED') THEN 2000 ELSE NULL END
                        WHERE job_id=?
                        """,
                        (state, state, state, job_id),
                    )
        return encoded

    def test_exact_coverage_dependencies_isolation_and_learner_policy(self) -> None:
        result = seed_all_catalog_jobs(self.database, self.jobs)

        self.assertEqual(82, result["courses"]["active_catalog_entries"])
        self.assertEqual(82, result["courses"]["covered_entries"])
        self.assertEqual(82, result["courses"]["seeded_cohorts"])
        self.assertEqual(359, result["build_projects"]["active_catalog_entries"])
        self.assertEqual(359, result["build_projects"]["covered_entries"])
        self.assertEqual(358, result["build_projects"]["generic_builders"])
        self.assertEqual(1, result["build_projects"]["recognized_specialized"])
        self.assertEqual(359, result["build_projects"]["reviewers"])

        managers = self._policy_jobs("csdiy_course_cohort", "preparation")
        students = self._policy_jobs("csdiy_course_cohort", "student")
        examiners = self._policy_jobs("csdiy_course_cohort", "examiner")
        builders = self._policy_jobs("byox_reference_build", "builder")
        reviewers = self._policy_jobs("byox_reference_review", "reviewer")
        self.assertEqual((82, 82, 82), (len(managers), len(students), len(examiners)))
        self.assertEqual(358, len(builders))
        self.assertEqual(359, len(reviewers))
        self.assertEqual(964, result["created_jobs"])

        course_coverage = result["courses"]["cohorts"]
        for course_id, graph in course_coverage.items():
            manager_id = graph["preparation"]
            student_id = graph["student"]
            examiner_id = graph["examiner"]
            self.assertEqual({CODEX_BACKEND_GATE_JOB_ID}, self._dependencies(manager_id))
            self.assertEqual({manager_id}, self._dependencies(student_id))
            self.assertEqual({manager_id, student_id}, self._dependencies(examiner_id))
            self.assertEqual(3, len({manager_id, student_id, examiner_id}))

            student = self.jobs.get(student_id)
            examiner = self.jobs.get(examiner_id)
            manager = self.jobs.get(manager_id)
            assert student is not None and examiner is not None and manager is not None
            self.assertTrue(
                all(
                    item["subpath"].startswith("student_safe/")
                    for item in student["payload"]["inputs_from_dependencies"]
                )
            )
            self.assertNotIn("RUBRIC.md", student["payload"]["prompt"])
            self.assertIn("UNIT_GRAPH.json", manager["payload"]["prompt"])
            self.assertIn("MATERIAL_AVAILABILITY.json", manager["payload"]["prompt"])
            self.assertIn("kickoff", student["payload"]["prompt"])
            policy = examiner["payload"]["learner_evidence"]
            self.assertEqual("student-target", policy["student_id"])
            self.assertEqual(student_id, policy["student_job_id"])
            self.assertEqual("student-course-attempt", policy["student_artifact_type"])
            self.assertEqual("course-examiner-evidence", policy["schema_validator"])
            self.assertEqual("evaluation.json", policy["evaluation_path"])
            self.assertEqual(course_id, policy["concepts"][0]["source_reference"])

        project_coverage = result["build_projects"]["projects"]
        self.assertEqual(self.specialized_job_id, project_coverage[self.specialized_project_id]["builder"])
        for project_id, graph in project_coverage.items():
            builder_id = graph["builder"]
            reviewer_id = graph["reviewer"]
            if graph["mode"] == "seeded_generic":
                self.assertEqual({CODEX_BACKEND_GATE_JOB_ID}, self._dependencies(builder_id))
            self.assertEqual(
                {CODEX_BACKEND_GATE_JOB_ID, builder_id},
                self._dependencies(reviewer_id),
            )
            reviewer = self.jobs.get(reviewer_id)
            assert reviewer is not None
            self.assertEqual(project_id, reviewer["payload"]["project_id"])
            verdict_validators = [
                item
                for item in reviewer["payload"]["validators"]
                if item.get("type") == "review_verdict"
            ]
            self.assertEqual(
                [
                    {
                        "type": "review_verdict",
                        "name": "byox-independent-review-verdict",
                        "path": "EVALUATION.json",
                    }
                ],
                verdict_validators,
            )
            acceptance_validators = [
                item
                for item in reviewer["payload"]["validators"]
                if item.get("type") == "review_acceptance"
            ]
            self.assertEqual(
                [
                    {
                        "type": "review_acceptance",
                        "name": "byox-independent-review-acceptance",
                        "mode": "closed",
                    }
                ],
                acceptance_validators,
            )
            self.assertTrue(
                all(
                    item["destination"].startswith("CANDIDATE/")
                    for item in reviewer["payload"]["inputs_from_dependencies"]
                )
            )
            staged = {
                item["subpath"]
                for item in reviewer["payload"]["inputs_from_dependencies"]
            }
            self.assertTrue(
                {
                    "starter",
                    "public_tests",
                    "environment",
                    "sealed",
                    "adversarial",
                    "debugging",
                    "review_exercises",
                    "benchmarks",
                }.issubset(staged)
            )
            expected_type = (
                "specialized-reference"
                if graph["mode"] == "recognized_specialized"
                else "byox-challenge-pack"
            )
            self.assertTrue(
                all(
                    item["artifact_type"] == expected_type
                    for item in reviewer["payload"]["inputs_from_dependencies"]
                )
            )
            if graph["mode"] == "seeded_generic":
                builder = self.jobs.get(builder_id)
                assert builder is not None
                self.assertTrue(builder["payload"]["retry_validation"])
                self.assertEqual(
                    7,
                    len(builder["payload"]["validators"]),
                )
                self.assertEqual(
                    1,
                    sum(
                        validator.get("type") == "byox_code_presence"
                        for validator in builder["payload"]["validators"]
                    ),
                )

        with self.database.connect() as connection:
            seeded = connection.execute(
                """
                SELECT state,attempt_count,owner,workspace,model,reasoning_effort,payload_json
                FROM jobs WHERE job_id<>?
                """,
                (self.specialized_job_id,),
            ).fetchall()
        self.assertTrue(seeded)
        for row in seeded:
            self.assertEqual(0, row["attempt_count"])
            self.assertIsNone(row["owner"])
            self.assertIsNone(row["workspace"])
            self.assertEqual("gpt-5.6-sol", row["model"])
            self.assertEqual("ultra", row["reasoning_effort"])
        self.assertEqual("READY", self.jobs.get(CODEX_BACKEND_GATE_JOB_ID)["state"])
        self.assertTrue(all(row["state"] == "DISCOVERED" for row in seeded if json.loads(row["payload_json"])["seed_policy"]["kind"] != "codex_backend_gate"))

    def test_idempotency_and_immutable_seed_provenance(self) -> None:
        first = seed_all_catalog_jobs(self.database, self.jobs)
        generic_id = next(
            item["builder"]
            for item in first["build_projects"]["projects"].values()
            if item["mode"] == "seeded_generic"
        )
        manager_id = next(iter(first["courses"]["cohorts"].values()))["preparation"]
        reviewer_id = next(iter(first["build_projects"]["projects"].values()))["reviewer"]
        with self.database.connect() as connection:
            before_count = connection.execute("SELECT COUNT(*) AS n FROM jobs").fetchone()["n"]
            before_payloads = {
                job_id: connection.execute(
                    "SELECT payload_json FROM jobs WHERE job_id=?", (job_id,)
                ).fetchone()["payload_json"]
                for job_id in (generic_id, manager_id, reviewer_id)
            }
            degraded = json.loads(before_payloads[generic_id])
            degraded["retry_validation"] = False
            degraded["validators"] = degraded["validators"][:2]
            degraded_reviewer = json.loads(before_payloads[reviewer_id])
            degraded_reviewer["validators"] = [
                item
                for item in degraded_reviewer["validators"]
                if item.get("type") != "review_verdict"
            ]
            connection.execute(
                "UPDATE jobs SET payload_json=? WHERE job_id=?",
                (
                    json.dumps(degraded, sort_keys=True, separators=(",", ":")),
                    generic_id,
                ),
            )
            connection.execute(
                "UPDATE jobs SET payload_json=? WHERE job_id=?",
                (
                    json.dumps(
                        degraded_reviewer, sort_keys=True, separators=(",", ":")
                    ),
                    reviewer_id,
                ),
            )

        second = seed_all_catalog_jobs(self.database, self.jobs)
        self.assertEqual(0, second["created_jobs"])
        with self.database.connect() as connection:
            self.assertEqual(
                before_count,
                connection.execute("SELECT COUNT(*) AS n FROM jobs").fetchone()["n"],
            )
            self.assertEqual(
                before_payloads[reviewer_id],
                connection.execute(
                    "SELECT payload_json FROM jobs WHERE job_id=?", (reviewer_id,)
                ).fetchone()["payload_json"],
            )
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "UPDATE sources SET commit_hash='csdiy-commit-2' WHERE source_id='source_csdiy_active'"
            )
            connection.execute(
                "UPDATE sources SET commit_hash='byox-commit-2' WHERE source_id='source_byox_active'"
            )
            connection.commit()

        third = seed_all_catalog_jobs(self.database, self.jobs)
        self.assertEqual(0, third["created_jobs"])
        with self.database.connect() as connection:
            for job_id, payload in before_payloads.items():
                self.assertEqual(
                    payload,
                    connection.execute(
                        "SELECT payload_json FROM jobs WHERE job_id=?", (job_id,)
                    ).fetchone()["payload_json"],
                )

    def test_attempted_v1_review_without_verdict_contract_gets_idempotent_v2(self) -> None:
        first = seed_all_catalog_jobs(self.database, self.jobs)
        graph = first["build_projects"]["projects"][self.specialized_project_id]
        v1_reviewer_id = graph["reviewer"]
        v1 = self.jobs.get(v1_reviewer_id)
        assert v1 is not None
        old_payload = v1["payload"]
        old_payload["validators"] = [
            item
            for item in old_payload["validators"]
            if item.get("type") != "review_verdict"
        ]
        encoded_old_payload = json.dumps(
            old_payload, sort_keys=True, separators=(",", ":")
        )
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                "UPDATE jobs SET payload_json=?,state='READY' WHERE job_id=?",
                (encoded_old_payload, v1_reviewer_id),
            )
            connection.execute(
                """
                UPDATE jobs
                SET state='CLAIMED',owner='old-reviewer',lease_token='old-lease',
                    lease_expires_at=9999999999,attempt_count=1
                WHERE job_id=?
                """,
                (v1_reviewer_id,),
            )
            connection.execute(
                "UPDATE jobs SET state='RUNNING' WHERE job_id=?",
                (v1_reviewer_id,),
            )

        while_running = seed_all_catalog_jobs(self.database, self.jobs)
        self.assertEqual(0, while_running["created_jobs"])
        self.assertEqual(
            v1_reviewer_id,
            while_running["build_projects"]["projects"][
                self.specialized_project_id
            ]["reviewer"],
        )

        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                """
                UPDATE jobs
                SET state='SUCCEEDED',owner=NULL,lease_token=NULL,lease_expires_at=NULL,
                    finished_at=2000
                WHERE job_id=?
                """,
                (v1_reviewer_id,),
            )

        second = seed_all_catalog_jobs(self.database, self.jobs)
        remediated = second["build_projects"]["projects"][self.specialized_project_id]
        v2_reviewer_id = remediated["reviewer"]
        self.assertNotEqual(v1_reviewer_id, v2_reviewer_id)
        self.assertEqual(
            BYOX_REVIEW_REMEDIATION_POLICY_VERSION,
            remediated["review_policy_version"],
        )
        self.assertEqual(1, second["build_projects"]["created_reviewer_jobs"])
        self.assertEqual(1, second["created_jobs"])
        v2 = self.jobs.get(v2_reviewer_id)
        assert v2 is not None
        self.assertEqual(
            {
                "kind": "byox_reference_review",
                "version": BYOX_REVIEW_REMEDIATION_POLICY_VERSION,
                "role": "reviewer",
            },
            v2["payload"]["seed_policy"],
        )
        self.assertTrue(
            any(
                item.get("type") == "review_verdict"
                for item in v2["payload"]["validators"]
            )
        )
        self.assertTrue(v2["payload"]["artifact_path"].endswith("/review-v2"))
        self.assertEqual(
            v1_reviewer_id,
            v2["payload"]["provenance"]["supersedes_reviewer_job_id"],
        )
        self.assertEqual("gpt-5.6-sol", v2["model"])
        self.assertEqual("ultra", v2["reasoning_effort"])
        self.assertEqual(
            {CODEX_BACKEND_GATE_JOB_ID, self.specialized_job_id},
            self._dependencies(v2_reviewer_id),
        )
        with self.database.connect() as connection:
            persisted_v1_payload = connection.execute(
                "SELECT payload_json FROM jobs WHERE job_id=?", (v1_reviewer_id,)
            ).fetchone()["payload_json"]
        self.assertEqual(encoded_old_payload, persisted_v1_payload)

        third = seed_all_catalog_jobs(self.database, self.jobs)
        self.assertEqual(0, third["created_jobs"])
        self.assertEqual(
            v2_reviewer_id,
            third["build_projects"]["projects"][self.specialized_project_id]["reviewer"],
        )

    def test_review_remediation_covers_nonactive_states_and_fences_queued_v1(self) -> None:
        first = seed_all_catalog_jobs(self.database, self.jobs)
        selected = list(first["build_projects"]["projects"].items())[:9]
        states = (
            "READY",
            "RETRY_WAIT",
            "BLOCKED",
            "FAILED",
            "SUCCEEDED",
            "CANCELLED",
            "CLAIMED",
            "RUNNING",
        )
        legacy: dict[str, tuple[str, str]] = {}
        original_payloads: dict[str, str] = {}
        for index, ((project_id, graph), state) in enumerate(
            zip(selected[:8], states)
        ):
            reviewer_id = graph["reviewer"]
            removed = (
                "byox-independent-review-concrete-evidence"
                if index == 0
                else "byox-independent-review-verdict"
            )
            original_payloads[reviewer_id] = self._make_attempted_review(
                reviewer_id,
                state,
                remove_validator=removed,
            )
            legacy[project_id] = (reviewer_id, state)

        full_contract_project, full_contract_graph = selected[8]
        full_contract_reviewer = full_contract_graph["reviewer"]
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                """
                UPDATE jobs SET state='READY',attempt_count=1 WHERE job_id=?
                """,
                (full_contract_reviewer,),
            )

        remediated = seed_all_catalog_jobs(self.database, self.jobs)
        self.assertEqual(6, remediated["build_projects"]["created_reviewer_jobs"])
        self.assertEqual(6, remediated["created_jobs"])
        self.assertEqual(
            full_contract_reviewer,
            remediated["build_projects"]["projects"][full_contract_project][
                "reviewer"
            ],
        )
        full_contract_record = self.jobs.get(full_contract_reviewer)
        assert full_contract_record is not None
        self.assertEqual("READY", full_contract_record["state"])
        self.assertEqual(0, full_contract_record["cancel_requested"])
        for project_id, (v1_job_id, previous_state) in legacy.items():
            graph = remediated["build_projects"]["projects"][project_id]
            if previous_state in {"CLAIMED", "RUNNING"}:
                self.assertEqual(v1_job_id, graph["reviewer"])
                self.assertEqual(1, graph["review_policy_version"])
                continue
            self.assertNotEqual(v1_job_id, graph["reviewer"])
            self.assertEqual(
                BYOX_REVIEW_REMEDIATION_POLICY_VERSION,
                graph["review_policy_version"],
            )
            v2 = self.jobs.get(graph["reviewer"])
            assert v2 is not None
            validator_names = {
                item.get("name") for item in v2["payload"]["validators"]
            }
            self.assertIn("byox-independent-review-verdict", validator_names)
            self.assertIn(
                "byox-independent-review-concrete-evidence", validator_names
            )
            self.assertIn(
                "byox-independent-review-acceptance", validator_names
            )
            self.assertEqual("gpt-5.6-sol", v2["model"])
            self.assertEqual("ultra", v2["reasoning_effort"])

        for project_id, previous_state in (
            (selected[0][0], "READY"),
            (selected[1][0], "RETRY_WAIT"),
        ):
            v1_job_id = legacy[project_id][0]
            v1 = self.jobs.get(v1_job_id)
            assert v1 is not None
            self.assertEqual("CANCELLED", v1["state"])
            self.assertEqual(1, v1["cancel_requested"])
            self.assertEqual("superseded_review_policy", v1["failure_kind"])
            self.assertIn("contract v2", v1["error"])
            self.jobs.promote_eligible()
            self.assertEqual("CANCELLED", self.jobs.get(v1_job_id)["state"])

        with self.database.connect() as connection:
            superseded_ids = [
                legacy[selected[0][0]][0], legacy[selected[1][0]][0]
            ]
            dispatchable_superseded = connection.execute(
                """
                SELECT COUNT(*) AS n FROM jobs
                WHERE job_id IN (?,?) AND state='READY' AND cancel_requested=0
                  AND attempt_count < max_attempts
                """,
                superseded_ids,
            ).fetchone()["n"]
            superseded = connection.execute(
                """
                SELECT job_id,payload_json FROM events
                WHERE type='JOB_SUPERSEDED' ORDER BY job_id
                """
            ).fetchall()
            persisted_payloads = {
                job_id: connection.execute(
                    "SELECT payload_json FROM jobs WHERE job_id=?", (job_id,)
                ).fetchone()["payload_json"]
                for job_id, _ in legacy.values()
            }
        self.assertEqual(
            0,
            dispatchable_superseded,
        )
        self.assertEqual(
            sorted(superseded_ids),
            [row["job_id"] for row in superseded],
        )
        self.assertTrue(
            all(
                json.loads(row["payload_json"])["superseding_policy_version"]
                == BYOX_REVIEW_REMEDIATION_POLICY_VERSION
                for row in superseded
            )
        )
        self.assertEqual(original_payloads, persisted_payloads)

        active_projects = [selected[6][0], selected[7][0]]
        with self.database.transaction(immediate=True) as connection:
            claimed_id = legacy[active_projects[0]][0]
            running_id = legacy[active_projects[1]][0]
            connection.execute(
                """
                UPDATE jobs
                SET state='FAILED',owner=NULL,lease_token=NULL,lease_expires_at=NULL,
                    finished_at=3000
                WHERE job_id=?
                """,
                (claimed_id,),
            )
            connection.execute(
                """
                UPDATE jobs
                SET state='SUCCEEDED',owner=NULL,lease_token=NULL,lease_expires_at=NULL,
                    finished_at=3000
                WHERE job_id=?
                """,
                (running_id,),
            )
        after_active = seed_all_catalog_jobs(self.database, self.jobs)
        self.assertEqual(2, after_active["created_jobs"])
        self.assertTrue(
            all(
                after_active["build_projects"]["projects"][project_id][
                    "review_policy_version"
                ]
                == BYOX_REVIEW_REMEDIATION_POLICY_VERSION
                for project_id in active_projects
            )
        )
        final = seed_all_catalog_jobs(self.database, self.jobs)
        self.assertEqual(0, final["created_jobs"])

    def test_cli_exposes_unified_seed_only_command(self) -> None:
        args = build_parser().parse_args(["seed-all"])
        self.assertIs(cmd_seed_all, args.func)


if __name__ == "__main__":
    unittest.main()
