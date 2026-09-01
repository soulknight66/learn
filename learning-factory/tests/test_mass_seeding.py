from __future__ import annotations

import copy
import hashlib
import json
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from learnfactory.backend_policy import (
    MASS_SEED_BACKEND_REQUIREMENT,
    MASS_SEED_EXECUTION_POLICY,
)
from learnfactory.cli import build_parser, cmd_seed_all
from learnfactory.byox_baselines import (
    BYOX_SNAPSHOT_JOB_SCHEME_VERSION,
    load_verified_binding,
)
from learnfactory.byox_jobs import (
    build_byox_job_spec,
    load_active_byox_projects,
)
from learnfactory.db import Database
from learnfactory.jobs import JobRepository
from learnfactory.learners import seed_students
from learnfactory.review_contract import MAX_REVIEW_EVALUATION_BYTES
from learnfactory.seeding import (
    BYOX_BUILD_S2_POLICY_KIND,
    BYOX_REVIEW_CONTRACT_VERSION,
    BYOX_REVIEW_S2_POLICY_KIND,
    CODEX_BACKEND_GATE_JOB_ID,
    COURSE_EXAMINER_REMEDIATION_POLICY_VERSION,
    _byox_review_job_id,
    _byox_reviewer_payload,
    _has_byox_review_contract,
    seed_all_byox_reference_jobs,
    seed_all_catalog_jobs,
    seed_codex_backend_gate,
)
from learnfactory.util import tree_sha256


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = REPOSITORY_ROOT / "migrations"


class MassCatalogSeedingTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="learnfactory-mass-seed-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.warehouse = (self.root / "warehouse").resolve()
        self.database = Database(self.root / "factory.db", MIGRATIONS)
        self.database.migrate()
        self.jobs = JobRepository(self.database)
        seed_students(self.database, self.warehouse)
        full_catalog = (
            self._testMethodName
            == "test_exact_coverage_dependencies_isolation_and_learner_policy"
        )
        self._insert_exact_catalogs(
            course_count=82 if full_catalog else 2,
            unit_count=394 if full_catalog else 6,
            project_count=359 if full_catalog else 4,
        )
        self.specialized_project_id = "project_00000000000000000000000000000000"
        self.specialized_job_id = "job_existing_specialized_builder"
        self._insert_successful_specialized_builder()

    def _insert_exact_catalogs(
        self, *, course_count: int, unit_count: int, project_count: int
    ) -> None:
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
                    json.dumps(
                        {
                            "adapter": "build_your_own_x",
                            "extractor_version": "1.1",
                            "snapshot_reader": "git-object-database",
                            "tree_hash": "byox-tree-1",
                        }
                    ),
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
                    for index in range(course_count)
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
                        f"course_{index % course_count:032x}",
                        "reading",
                        index // 82,
                        f"Catalog resource {index}",
                        "[]",
                        f"https://example.invalid/resource/{index}",
                        json.dumps({"normalized_resource_link": True}),
                    )
                    for index in range(unit_count)
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
                    for index in range(project_count)
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
            policy = payload.get("seed_policy")
            if (
                isinstance(policy, dict)
                and policy.get("kind") == kind
                and policy.get("role") == role
                and (
                    kind != "csdiy_course_cohort"
                    or role not in {"student", "examiner"}
                    or policy.get("version")
                    == COURSE_EXAMINER_REMEDIATION_POLICY_VERSION
                )
            ):
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

    def _force_fixture_dependencies_succeeded(
        self,
        connection: sqlite3.Connection,
        job_id: str,
        visited: set[str] | None = None,
    ) -> None:
        """Complete fixture prerequisites through legal state transitions."""

        active = set() if visited is None else visited
        if job_id in active:
            raise AssertionError("fixture dependency cycle")
        active.add(job_id)
        dependencies = [
            str(row[0])
            for row in connection.execute(
                """
                SELECT depends_on_job_id FROM job_dependencies
                WHERE job_id=? ORDER BY depends_on_job_id
                """,
                (job_id,),
            )
        ]
        for dependency in dependencies:
            self._force_fixture_dependencies_succeeded(
                connection,
                dependency,
                active,
            )
            row = connection.execute(
                "SELECT state FROM jobs WHERE job_id=?",
                (dependency,),
            ).fetchone()
            if row is None:
                raise AssertionError(f"missing fixture dependency: {dependency}")
            state = str(row[0])
            if state == "SUCCEEDED":
                continue
            if state in {"BLOCKED", "FAILED", "RETRY_WAIT"}:
                connection.execute(
                    """
                    UPDATE jobs SET state='READY',cancel_requested=0,retry_at=NULL
                    WHERE job_id=?
                    """,
                    (dependency,),
                )
                state = "READY"
            elif state == "DISCOVERED":
                connection.execute(
                    "UPDATE jobs SET state='READY' WHERE job_id=?",
                    (dependency,),
                )
                state = "READY"
            if state == "READY":
                connection.execute(
                    """
                    UPDATE jobs SET state='CLAIMED',owner=?,lease_token=?,
                        lease_expires_at=9999999999,attempt_count=MAX(attempt_count,1)
                    WHERE job_id=?
                    """,
                    (
                        f"fixture-owner-{dependency}",
                        f"fixture-lease-{dependency}",
                        dependency,
                    ),
                )
                state = "CLAIMED"
            if state == "CLAIMED":
                connection.execute(
                    "UPDATE jobs SET state='RUNNING' WHERE job_id=?",
                    (dependency,),
                )
                state = "RUNNING"
            if state != "RUNNING":
                raise AssertionError(
                    f"unsupported fixture dependency state: {dependency}={state}"
                )
            connection.execute(
                """
                UPDATE jobs SET state='SUCCEEDED',owner=NULL,lease_token=NULL,
                    lease_expires_at=NULL,finished_at=2000
                WHERE job_id=?
                """,
                (dependency,),
            )
        active.remove(job_id)

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
            if state == "SUCCEEDED":
                self._force_fixture_dependencies_succeeded(connection, job_id)
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

    def _clone_reviewer_version(
        self,
        source_job_id: str,
        project_id: str,
        policy_version: int,
        *,
        legacy_command_contract: bool = False,
    ) -> str:
        source = self.jobs.get(source_job_id)
        assert source is not None
        payload = copy.deepcopy(source["payload"])
        payload["seed_policy"]["version"] = policy_version
        payload["provenance"]["policy_version"] = policy_version
        payload["artifact_path"] = (
            payload["artifact_path"].rsplit("/review-v", 1)[0]
            + f"/review-v{policy_version}"
        )
        if legacy_command_contract:
            for validator in payload["validators"]:
                if validator.get("type") == "review_verdict":
                    validator.pop("contract_version", None)
            payload["validators"].insert(
                -1,
                {
                    "type": "command",
                    "name": "byox-independent-review-concrete-evidence",
                    "argv": ["python3", "-c", "raise SystemExit(0)"],
                    "timeout_seconds": 10,
                },
            )
        reviewer_id = _byox_review_job_id(
            project_id, policy_version=policy_version
        )
        self.jobs.create(
            source["type"],
            source["worker_type"],
            payload,
            priority=source["priority"],
            score_components=source["score_components"],
            max_attempts=source["max_attempts"],
            dependencies=sorted(self._dependencies(source_job_id)),
            job_id=reviewer_id,
            model=source["model"],
            reasoning_effort=source["reasoning_effort"],
        )
        return reviewer_id

    def _mark_job_succeeded_after_one_attempt(
        self, connection: sqlite3.Connection, job_id: str, *, finished_at: float
    ) -> None:
        self._force_fixture_dependencies_succeeded(connection, job_id)
        connection.execute(
            "UPDATE jobs SET state='READY' WHERE job_id=?", (job_id,)
        )
        connection.execute(
            """
            UPDATE jobs SET state='CLAIMED',owner='fixture-reviewer',
                            lease_token='fixture-lease',lease_expires_at=9999999999,
                            attempt_count=1
            WHERE job_id=?
            """,
            (job_id,),
        )
        connection.execute(
            "UPDATE jobs SET state='RUNNING' WHERE job_id=?", (job_id,)
        )
        connection.execute(
            """
            UPDATE jobs SET state='SUCCEEDED',owner=NULL,lease_token=NULL,
                            lease_expires_at=NULL,finished_at=?
            WHERE job_id=?
            """,
            (finished_at, job_id),
        )

    def test_exact_coverage_dependencies_isolation_and_learner_policy(self) -> None:
        result = seed_all_catalog_jobs(self.database, self.jobs, warehouse=self.warehouse)

        self.assertEqual(82, result["courses"]["active_catalog_entries"])
        self.assertEqual(82, result["courses"]["covered_entries"])
        self.assertEqual(82, result["courses"]["seeded_cohorts"])
        self.assertEqual(359, result["build_projects"]["active_catalog_entries"])
        self.assertEqual(359, result["build_projects"]["covered_entries"])
        self.assertEqual(359, result["build_projects"]["generic_builders"])
        self.assertEqual(0, result["build_projects"]["recognized_specialized"])
        self.assertEqual(359, result["build_projects"]["reviewers"])

        managers = self._policy_jobs("csdiy_course_cohort", "preparation")
        students = self._policy_jobs("csdiy_course_cohort", "student")
        examiners = self._policy_jobs("csdiy_course_cohort", "examiner")
        builders = self._policy_jobs(BYOX_BUILD_S2_POLICY_KIND, "builder")
        reviewers = self._policy_jobs(BYOX_REVIEW_S2_POLICY_KIND, "reviewer")
        self.assertEqual((82, 82, 82), (len(managers), len(students), len(examiners)))
        self.assertEqual(359, len(builders))
        self.assertEqual(359, len(reviewers))
        self.assertEqual(965, result["created_jobs"])
        for job in managers + students + examiners + builders + reviewers:
            payload = job["payload"]
            self.assertEqual(
                MASS_SEED_BACKEND_REQUIREMENT, payload["required_backend"]
            )
            self.assertEqual(
                MASS_SEED_EXECUTION_POLICY, payload["execution_policy"]
            )

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
        with self.database.connect() as connection:
            binding_by_job = {
                str(row["job_id"]): row
                for row in connection.execute(
                    "SELECT * FROM byox_baseline_job_bindings"
                )
            }
            verified_binding_by_job = {
                identifier: load_verified_binding(connection, identifier)
                for graph in project_coverage.values()
                for identifier in (graph["builder"], graph["reviewer"])
            }
        self.assertEqual(718, len(binding_by_job))
        self.assertTrue(all(verified_binding_by_job.values()))
        self.assertNotEqual(
            self.specialized_job_id,
            project_coverage[self.specialized_project_id]["builder"],
        )
        for project_id, graph in project_coverage.items():
            builder_id = graph["builder"]
            reviewer_id = graph["reviewer"]
            self.assertEqual("seeded_generic_s2", graph["mode"])
            self.assertEqual({CODEX_BACKEND_GATE_JOB_ID}, self._dependencies(builder_id))
            self.assertEqual(
                {CODEX_BACKEND_GATE_JOB_ID, builder_id},
                self._dependencies(reviewer_id),
            )
            self.assertRegex(graph["baseline_sha256"], r"^[0-9a-f]{64}$")
            builder_binding = binding_by_job[builder_id]
            reviewer_binding = binding_by_job[reviewer_id]
            self.assertEqual(
                graph["baseline_sha256"], builder_binding["baseline_sha256"]
            )
            self.assertEqual(
                graph["baseline_sha256"], reviewer_binding["baseline_sha256"]
            )
            self.assertEqual("builder", builder_binding["role"])
            self.assertEqual(
                BYOX_SNAPSHOT_JOB_SCHEME_VERSION,
                builder_binding["policy_version"],
            )
            self.assertIsNone(builder_binding["builder_job_id"])
            self.assertEqual("reviewer", reviewer_binding["role"])
            self.assertEqual(
                BYOX_REVIEW_CONTRACT_VERSION,
                reviewer_binding["policy_version"],
            )
            self.assertEqual(builder_id, reviewer_binding["builder_job_id"])
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
                        "contract_version": BYOX_REVIEW_CONTRACT_VERSION,
                    }
                ],
                verdict_validators,
            )
            schema_validators = [
                item
                for item in reviewer["payload"]["validators"]
                if item.get("type") == "json_schema"
            ]
            self.assertEqual(1, len(schema_validators))
            self.assertEqual(
                MAX_REVIEW_EVALUATION_BYTES,
                schema_validators[0]["max_bytes"],
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
            self.assertFalse(
                any(
                    item.get("type") == "command"
                    for item in reviewer["payload"]["validators"]
                )
            )
            self.assertEqual(4, len(reviewer["payload"]["validators"]))
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
            self.assertTrue(
                all(
                    item["artifact_type"] == "byox-challenge-pack"
                    for item in reviewer["payload"]["inputs_from_dependencies"]
                )
            )
            builder = self.jobs.get(builder_id)
            assert builder is not None
            self.assertEqual(BYOX_BUILD_S2_POLICY_KIND, builder["payload"]["seed_policy"]["kind"])
            self.assertEqual(graph["baseline_sha256"], builder["payload"]["baseline_sha256"])
            self.assertTrue(builder["payload"]["retry_validation"])
            self.assertEqual(7, len(builder["payload"]["validators"]))
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

    def test_s2_repeat_and_observation_drift_reuse_immutable_lineage(self) -> None:
        first = seed_all_catalog_jobs(
            self.database, self.jobs, warehouse=self.warehouse
        )["build_projects"]
        job_ids = {
            identifier
            for graph in first["projects"].values()
            for identifier in (graph["builder"], graph["reviewer"])
        }
        with self.database.connect() as connection:
            before_payloads = {
                str(row["job_id"]): str(row["payload_json"])
                for row in connection.execute(
                    "SELECT job_id,payload_json FROM jobs ORDER BY job_id"
                )
                if row["job_id"] in job_ids
            }
            metadata = json.loads(
                connection.execute(
                    "SELECT metadata_json FROM sources WHERE source_id='source_byox_active'"
                ).fetchone()["metadata_json"]
            )
        metadata.update(
            {
                "head_ref": "refs/heads/relocated",
                "working_tree_dirty": True,
                "last_ingestion": {"at": 2002.0, "projects": 4, "warnings": []},
            }
        )
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                """
                UPDATE sources
                SET name=?,path=?,upstream_url=?,ingested_at=?,metadata_json=?
                WHERE source_id='source_byox_active'
                """,
                (
                    "Build Your Own X (relocated)",
                    "/relocated/public/build-your-own-x",
                    "https://mirror.invalid/build-your-own-x",
                    2002.0,
                    json.dumps(metadata, sort_keys=True),
                ),
            )

        second = seed_all_byox_reference_jobs(
            self.database, self.jobs, warehouse=self.warehouse
        )

        self.assertEqual(0, second["created_jobs"])
        self.assertEqual(first["projects"], second["projects"])
        with self.database.connect() as connection:
            after_payloads = {
                str(row["job_id"]): str(row["payload_json"])
                for row in connection.execute(
                    "SELECT job_id,payload_json FROM jobs ORDER BY job_id"
                )
                if row["job_id"] in job_ids
            }
        self.assertEqual(before_payloads, after_payloads)

    def test_bound_s2_job_definitions_are_sql_immutable(self) -> None:
        seeded = seed_all_catalog_jobs(
            self.database, self.jobs, warehouse=self.warehouse
        )
        graph = seeded["build_projects"]["projects"][self.specialized_project_id]
        before = {
            job_id: self.jobs.get(job_id)
            for job_id in (graph["builder"], graph["reviewer"])
        }

        for job_id in before:
            with self.subTest(job_id=job_id, field="payload_json"):
                with self.assertRaisesRegex(
                    sqlite3.IntegrityError,
                    "bound BYOX job definition is immutable",
                ):
                    with self.database.transaction(immediate=True) as connection:
                        connection.execute(
                            "UPDATE jobs SET payload_json='{}' WHERE job_id=?",
                            (job_id,),
                        )
            with self.subTest(job_id=job_id, field="model"):
                with self.assertRaisesRegex(
                    sqlite3.IntegrityError,
                    "bound BYOX job definition is immutable",
                ):
                    with self.database.transaction(immediate=True) as connection:
                        connection.execute(
                            "UPDATE jobs SET model='forged-model' WHERE job_id=?",
                            (job_id,),
                        )

        self.assertEqual(
            before,
            {
                job_id: self.jobs.get(job_id)
                for job_id in (graph["builder"], graph["reviewer"])
            },
        )

    def test_bound_s2_retry_and_interrupt_use_runtime_allowance(self) -> None:
        seeded = seed_all_catalog_jobs(
            self.database, self.jobs, warehouse=self.warehouse
        )
        graph = seeded["build_projects"]["projects"][self.specialized_project_id]
        builder_id = graph["builder"]
        builder = self.jobs.get(builder_id)
        assert builder is not None
        base_limit = builder["max_attempts"]
        self.assertEqual(0, builder["retry_allowance"])
        with self.database.connect() as connection:
            binding_before = load_verified_binding(connection, builder_id)
        self.assertIsNotNone(binding_before)
        assert binding_before is not None

        with self.database.transaction(immediate=True) as connection:
            gate_created = connection.execute(
                "SELECT created_at FROM jobs WHERE job_id=?",
                (CODEX_BACKEND_GATE_JOB_ID,),
            ).fetchone()["created_at"]
            connection.execute(
                """
                UPDATE jobs SET state='CLAIMED',attempt_count=1,owner='gate-owner',
                    lease_token='gate-lease',lease_expires_at=9999999999,
                    heartbeat_at=?,started_at=?
                WHERE job_id=? AND state='READY'
                """,
                (gate_created + 1, gate_created + 1, CODEX_BACKEND_GATE_JOB_ID),
            )
            connection.execute(
                "UPDATE jobs SET state='RUNNING' WHERE job_id=?",
                (CODEX_BACKEND_GATE_JOB_ID,),
            )
            connection.execute(
                """
                UPDATE jobs SET state='SUCCEEDED',owner=NULL,lease_token=NULL,
                    lease_expires_at=NULL,finished_at=?,heartbeat_at=?
                WHERE job_id=?
                """,
                (gate_created + 2, gate_created + 2, CODEX_BACKEND_GATE_JOB_ID),
            )
            created = connection.execute(
                "SELECT created_at FROM jobs WHERE job_id=?", (builder_id,)
            ).fetchone()["created_at"]
            connection.execute(
                "UPDATE jobs SET state='READY' WHERE job_id=?",
                (builder_id,),
            )
            connection.execute(
                """
                UPDATE jobs SET state='CLAIMED',attempt_count=?,owner='old-owner',
                    lease_token='old-lease',lease_expires_at=9999999999,
                    heartbeat_at=?,started_at=?
                WHERE job_id=?
                """,
                (base_limit, created + 1, created + 1, builder_id),
            )
            connection.execute(
                "UPDATE jobs SET state='RUNNING' WHERE job_id=?", (builder_id,)
            )
            connection.execute(
                """
                UPDATE jobs SET state='FAILED',owner=NULL,lease_token=NULL,
                    lease_expires_at=NULL,finished_at=?,heartbeat_at=?,
                    error='fixture exhausted',failure_kind='deterministic'
                WHERE job_id=?
                """,
                (created + 2, created + 2, builder_id),
            )

        self.jobs.retry(builder_id)
        retried = self.jobs.get(builder_id)
        assert retried is not None
        self.assertEqual("READY", retried["state"])
        self.assertEqual(base_limit, retried["max_attempts"])
        self.assertEqual(1, retried["retry_allowance"])
        self.assertEqual(1, self.jobs.count_ready_claimable(frozenset()))
        third = self.jobs.claim_next(
            "bound-owner-3", 30, max_total=1, type_limits={}
        )
        self.assertIsNotNone(third)
        assert third is not None
        self.assertEqual(builder_id, third.job_id)
        self.assertEqual(base_limit + 1, third.attempt_count)
        workspace = self.root / "workspaces" / builder_id / "attempt-003"
        workspace.mkdir(parents=True)
        worker_id = "worker-bound-attempt-3"
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
                    "reference_builder",
                    "STARTING",
                    timestamp,
                    timestamp,
                    builder_id,
                    str(workspace),
                ),
            )
        self.jobs.start(
            builder_id,
            "bound-owner-3",
            third.lease_token,
            worker_id,
            str(workspace),
            lease_seconds=30,
        )
        self.jobs.interrupt(
            builder_id,
            "bound-owner-3",
            third.lease_token,
            worker_id,
            reason="controller shutdown",
        )
        interrupted = self.jobs.get(builder_id)
        assert interrupted is not None
        self.assertEqual("RETRY_WAIT", interrupted["state"])
        self.assertEqual(base_limit, interrupted["max_attempts"])
        self.assertEqual(2, interrupted["retry_allowance"])
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                """
                UPDATE jobs SET state='CANCELLED',cancel_requested=1,
                    finished_at=?
                WHERE state='DISCOVERED' AND job_id<>?
                """,
                (time.time(), builder_id),
            )

        restarted = JobRepository(Database(self.database.path, MIGRATIONS))
        self.assertEqual(
            1, restarted.promote_eligible(at=interrupted["retry_at"])
        )
        fourth = restarted.claim_next(
            "bound-owner-4", 30, max_total=1, type_limits={}
        )
        self.assertIsNotNone(fourth)
        assert fourth is not None
        self.assertEqual(builder_id, fourth.job_id)
        self.assertEqual(base_limit + 2, fourth.attempt_count)
        after = restarted.get(builder_id)
        assert after is not None
        self.assertEqual(base_limit, after["max_attempts"])
        self.assertEqual(2, after["retry_allowance"])
        with self.database.connect() as connection:
            binding_after = load_verified_binding(connection, builder_id)
            events = [
                json.loads(row["payload_json"])
                for row in connection.execute(
                    """
                    SELECT payload_json FROM events
                    WHERE job_id=? AND type IN (
                        'JOB_MANUALLY_RETRIED','JOB_INTERRUPTED_FOR_RETRY'
                    ) ORDER BY event_id
                    """,
                    (builder_id,),
                )
            ]
        self.assertEqual(binding_before, binding_after)
        self.assertEqual(
            [base_limit + 1, base_limit + 2],
            [event["effective_attempt_limit"] for event in events],
        )

    def test_unbound_exact_legacy_pair_is_retired_before_s2_publication(self) -> None:
        self.assertEqual(
            CODEX_BACKEND_GATE_JOB_ID,
            seed_codex_backend_gate(self.jobs),
        )
        snapshot = next(
            item
            for item in load_active_byox_projects(self.database)
            if item.project_id == self.specialized_project_id
        )
        legacy = build_byox_job_spec(snapshot)
        legacy_builder_id = self.jobs.create(
            legacy.job_type,
            legacy.worker_type,
            legacy.payload,
            priority=legacy.priority,
            score_components=legacy.score_components,
            dependencies=[CODEX_BACKEND_GATE_JOB_ID],
            max_attempts=legacy.max_attempts,
            job_id=legacy.job_id,
            model=legacy.model,
            reasoning_effort=legacy.reasoning_effort,
        )
        legacy_reviewer_id = _byox_review_job_id(
            self.specialized_project_id, policy_version=1
        )
        legacy_reviewer_payload = _byox_reviewer_payload(
            project_id=self.specialized_project_id,
            builder_job_id=legacy_builder_id,
            builder_payload=legacy.payload,
            specialized=False,
            policy_version=1,
        )
        self.jobs.create(
            "codex_task",
            "examiner",
            legacy_reviewer_payload,
            priority=round(max(35.0, min(94.0, legacy.priority - 1)), 4),
            score_components=legacy.score_components,
            dependencies=[CODEX_BACKEND_GATE_JOB_ID, legacy_builder_id],
            max_attempts=2,
            job_id=legacy_reviewer_id,
            model="gpt-5.6-sol",
            reasoning_effort="ultra",
        )
        legacy_payloads = {
            legacy_builder_id: self.jobs.get(legacy_builder_id)["payload"],
            legacy_reviewer_id: self.jobs.get(legacy_reviewer_id)["payload"],
        }

        result = seed_all_byox_reference_jobs(
            self.database, self.jobs, warehouse=self.warehouse
        )

        graph = result["projects"][self.specialized_project_id]
        self.assertEqual("seeded_generic_s2", graph["mode"])
        self.assertNotIn(
            graph["builder"], {legacy_builder_id, legacy_reviewer_id}
        )
        self.assertNotIn(
            graph["reviewer"], {legacy_builder_id, legacy_reviewer_id}
        )
        for legacy_job_id in (legacy_builder_id, legacy_reviewer_id):
            record = self.jobs.get(legacy_job_id)
            assert record is not None
            self.assertEqual("CANCELLED", record["state"])
            self.assertEqual(1, record["cancel_requested"])
            self.assertEqual(
                "superseded_byox_snapshot_scheme", record["failure_kind"]
            )
            self.assertEqual(legacy_payloads[legacy_job_id], record["payload"])

    def test_review_contract_recognizer_requires_the_exact_non_executable_bundle(self) -> None:
        seeded = seed_all_catalog_jobs(self.database, self.jobs, warehouse=self.warehouse)
        reviewer_id = seeded["build_projects"]["projects"][
            self.specialized_project_id
        ]["reviewer"]
        reviewer = self.jobs.get(reviewer_id)
        assert reviewer is not None
        payload = reviewer["payload"]
        self.assertTrue(_has_byox_review_contract(payload))

        variants = []
        extra = copy.deepcopy(payload)
        extra["validators"].append(
            {"type": "required_paths", "name": "extra", "paths": ["REVIEW.md"]}
        )
        variants.append(extra)
        executable = copy.deepcopy(payload)
        executable["validators"].append(
            {"type": "command", "name": "legacy", "argv": ["true"]}
        )
        variants.append(executable)
        open_acceptance = copy.deepcopy(payload)
        next(
            item
            for item in open_acceptance["validators"]
            if item.get("type") == "review_acceptance"
        )["mode"] = "command"
        variants.append(open_acceptance)
        old_verdict = copy.deepcopy(payload)
        next(
            item
            for item in old_verdict["validators"]
            if item.get("type") == "review_verdict"
        ).pop("contract_version")
        variants.append(old_verdict)
        float_verdict = copy.deepcopy(payload)
        next(
            item
            for item in float_verdict["validators"]
            if item.get("type") == "review_verdict"
        )["contract_version"] = 2.0
        variants.append(float_verdict)
        duplicate_float_verdict = copy.deepcopy(payload)
        verdict_index = next(
            index
            for index, item in enumerate(duplicate_float_verdict["validators"])
            if item.get("type") == "review_verdict"
        )
        duplicate_float_verdict["validators"][verdict_index] = json.loads(
            '{"type":"review_verdict",'
            '"name":"byox-independent-review-verdict",'
            '"path":"EVALUATION.json",'
            '"contract_version":2,"contract_version":2.0}'
        )
        variants.append(duplicate_float_verdict)
        wrong_schema = copy.deepcopy(payload)
        wrong_schema["output_schema"]["required"].remove("limitations")
        variants.append(wrong_schema)

        self.assertTrue(all(not _has_byox_review_contract(item) for item in variants))
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                "UPDATE jobs SET state='READY' WHERE job_id=?", (reviewer_id,)
            )
        self.assertEqual(
            0,
            self.jobs.count_ready_held_by_validator_fence(
                frozenset({"command"})
            ),
        )

    def test_bound_s2_payload_rejects_ambiguous_or_pathological_rewrites(self) -> None:
        seeded = seed_all_catalog_jobs(
            self.database, self.jobs, warehouse=self.warehouse
        )
        reviewer_id = seeded["build_projects"]["projects"][
            self.specialized_project_id
        ]["reviewer"]
        with self.database.connect() as connection:
            original = connection.execute(
                "SELECT payload_json FROM jobs WHERE job_id=?", (reviewer_id,)
            ).fetchone()["payload_json"]
        self.assertIn('"contract_version":2', original)
        mutations = {
            "duplicate-version-float-then-int": original.replace(
                '"contract_version":2',
                '"contract_version":2.0,"contract_version":2',
                1,
            ),
            "nonfinite-number": original.replace(
                '"contract_version":2', '"contract_version":NaN', 1
            ),
            "deep-nesting": original[:-1]
            + ',"pathological":'
            + "[" * 1_100
            + "0"
            + "]" * 1_100
            + "}",
            "integer-digit-limit": original[:-1]
            + ',"pathological":'
            + "9" * 5_000
            + "}",
        }
        for suffix, attacked in mutations.items():
            with self.subTest(suffix=suffix):
                self.assertNotEqual(original, attacked)
                with self.assertRaisesRegex(
                    sqlite3.IntegrityError,
                    "bound BYOX job definition is immutable",
                ):
                    with self.database.transaction(immediate=True) as connection:
                        connection.execute(
                            "UPDATE jobs SET payload_json=? WHERE job_id=?",
                            (attacked, reviewer_id),
                        )
                with self.database.connect() as connection:
                    persisted = connection.execute(
                        "SELECT payload_json FROM jobs WHERE job_id=?", (reviewer_id,)
                    ).fetchone()["payload_json"]
                self.assertEqual(original, persisted)

    def test_corrupt_unbound_legacy_cutover_fails_without_mutation(self) -> None:
        seed_codex_backend_gate(self.jobs)
        snapshot = next(
            item
            for item in load_active_byox_projects(self.database)
            if item.project_id == self.specialized_project_id
        )
        legacy = build_byox_job_spec(snapshot)
        legacy_id = self.jobs.create(
            legacy.job_type,
            legacy.worker_type,
            legacy.payload,
            priority=legacy.priority,
            score_components=legacy.score_components,
            dependencies=[CODEX_BACKEND_GATE_JOB_ID],
            max_attempts=legacy.max_attempts,
            job_id=legacy.job_id,
            model=legacy.model,
            reasoning_effort=legacy.reasoning_effort,
        )
        with self.database.connect() as connection:
            original = connection.execute(
                "SELECT payload_json FROM jobs WHERE job_id=?", (legacy_id,)
            ).fetchone()["payload_json"]
        mutations = {
            "duplicate-project-id": original[:-1]
            + ',"project_id":"forged-duplicate"}',
            "deep-nesting": original[:-1]
            + ',"pathological":'
            + "[" * 1_100
            + "0"
            + "]" * 1_100
            + "}",
        }
        for name, attacked in mutations.items():
            with self.subTest(name=name):
                with self.database.transaction(immediate=True) as connection:
                    connection.execute(
                        "UPDATE jobs SET payload_json=? WHERE job_id=?",
                        (attacked, legacy_id),
                    )
                with self.database.connect() as connection:
                    before = "\n".join(connection.iterdump())
                with self.assertRaisesRegex(
                    RuntimeError, "invalid|ambiguous|exact released definition"
                ):
                    seed_all_byox_reference_jobs(
                        self.database, self.jobs, warehouse=self.warehouse
                    )
                with self.database.connect() as connection:
                    after = "\n".join(connection.iterdump())
                self.assertEqual(before, after)
                with self.database.transaction(immediate=True) as connection:
                    connection.execute(
                        "UPDATE jobs SET payload_json=? WHERE job_id=?",
                        (original, legacy_id),
                    )

    def test_repeated_byox_seed_is_an_nfs_friendly_read_only_noop(self) -> None:
        first = seed_all_catalog_jobs(self.database, self.jobs, warehouse=self.warehouse)
        with self.database.connect() as connection:
            before_events = connection.execute(
                "SELECT COUNT(*) AS n FROM events"
            ).fetchone()["n"]
        before_sha = hashlib.sha256(self.database.path.read_bytes()).hexdigest()

        with patch.object(
            self.database,
            "transaction",
            side_effect=AssertionError("no-op seed attempted a writer transaction"),
        ):
            repeated = seed_all_byox_reference_jobs(self.database, self.jobs, warehouse=self.warehouse)

        self.assertEqual(0, repeated["created_jobs"])
        self.assertEqual(
            first["build_projects"]["projects"], repeated["projects"]
        )
        self.assertEqual(before_sha, hashlib.sha256(self.database.path.read_bytes()).hexdigest())
        with self.database.connect() as connection:
            self.assertEqual(
                before_events,
                connection.execute("SELECT COUNT(*) AS n FROM events").fetchone()["n"],
            )

    def test_cli_exposes_unified_seed_only_command(self) -> None:
        config = self.root / "factory.toml"
        config.write_text(
            "\n".join(
                (
                    "[factory]",
                    f'database = "{self.database.path}"',
                    f'warehouse = "{self.warehouse}"',
                    "[backend]",
                    'command = "codex"',
                    'model = "gpt-5.6-sol"',
                    'reasoning_effort = "ultra"',
                )
            )
            + "\n",
            encoding="utf-8",
        )
        args = build_parser().parse_args(
            ["--config", str(config), "seed-all"]
        )
        self.assertIs(cmd_seed_all, args.func)
        with patch("builtins.print") as emitted:
            self.assertEqual(0, cmd_seed_all(args))
        result = json.loads(str(emitted.call_args.args[0]))
        self.assertEqual(str(self.warehouse), str((self.root / "warehouse").resolve()))
        self.assertEqual(4, result["build_projects"]["covered_entries"])
        self.assertEqual(2, result["courses"]["covered_entries"])
        self.assertFalse(result["execution_started"])


if __name__ == "__main__":
    unittest.main()
