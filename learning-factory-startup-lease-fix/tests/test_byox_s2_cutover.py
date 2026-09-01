from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import threading
import unittest
from pathlib import Path
from typing import Any

from learnfactory.byox_baselines import (
    BYOX_SNAPSHOT_JOB_SCHEME_VERSION,
    ByoxBaselineConflict,
    byox_s2_builder_job_id,
    byox_s2_reviewer_job_id,
    derive_byox_baseline,
    load_verified_binding,
)
from learnfactory.byox_jobs import (
    ByoxBuildJobSpec,
    build_byox_job_spec,
    load_active_byox_projects,
)
from learnfactory.db import Database
from learnfactory.jobs import JobRepository
from learnfactory.seeding import (
    BYOX_BUILD_S2_POLICY_KIND,
    BYOX_REVIEW_CONTRACT_VERSION,
    BYOX_REVIEW_S2_POLICY_KIND,
    CODEX_BACKEND_GATE_JOB_ID,
    _byox_review_job_id,
    _byox_reviewer_payload,
    seed_all_byox_reference_jobs,
    seed_codex_backend_gate,
)
from learnfactory.util import tree_sha256


ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "migrations"
PROJECT_ID = "project_44e8061be7b19deb5e3e6b2fdef38d1a"
SOURCE_ID = "source_byox_s2_cutover"
DISPATCHABLE_STATES = frozenset(
    {"DISCOVERED", "READY", "RETRY_WAIT", "BLOCKED", "CLAIMED", "RUNNING"}
)


class ByoxS2CutoverTests(unittest.TestCase):
    """Production-level contract for immutable BYOX S2 publication and cutover."""

    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="learnfactory-byox-s2-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.warehouse = (self.root / "durable" / "warehouse").resolve()
        self.warehouse.mkdir(parents=True)
        self.database = Database(self.root / "state" / "factory.db", MIGRATIONS)
        self.database.migrate()
        self.jobs = JobRepository(self.database)
        self.assertEqual(
            CODEX_BACKEND_GATE_JOB_ID,
            seed_codex_backend_gate(self.jobs),
        )
        self._insert_catalog()

    @staticmethod
    def _source_metadata(*, observation: int = 1) -> dict[str, Any]:
        return {
            "adapter": "build_your_own_x",
            "extractor_version": "1.1",
            "snapshot_reader": "git-object-database",
            "tree_hash": "tree-material-a",
            "license_file": "README.md#origins--license",
            "license_sha256": "a" * 64,
            "license_source_commit": "commit-a",
            "license_evidence": "explicit CC0 waiver declaration",
            "linked_resource_license": "NOASSERTION",
            "head_ref": f"observation-{observation}",
            "working_tree_dirty": bool(observation % 2),
            "last_ingestion": {
                "at": observation,
                "projects": 1,
                "warnings": [f"observation-{observation}"],
            },
        }

    @staticmethod
    def _project_metadata() -> dict[str, Any]:
        return {
            "provenance": {
                "classification": "source-derived",
                "source_commit": "commit-a",
                "source_file": "README.md",
                "source_line": 42,
                "content_sha256": "b" * 64,
                "adapter": "build_your_own_x",
                "extractor_version": "1.1",
            },
            "languages": ["Rust"],
            "linked_resource_license": "NOASSERTION",
            "scoring": {
                "classification": "inferred",
                "priority_tier": 1,
                "basis": "systems-depth heuristic",
            },
        }

    def _insert_catalog(self) -> None:
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                """
                INSERT INTO sources(
                    source_id,type,name,path,upstream_url,commit_hash,license,
                    ingested_at,metadata_json,is_active
                ) VALUES (?,?,?,?,?,?,?,?,?,1)
                """,
                (
                    SOURCE_ID,
                    "project_catalog",
                    "Build Your Own X",
                    "/public/catalogs/build-your-own-x",
                    "https://github.com/codecrafters-io/build-your-own-x",
                    "commit-a",
                    "CC0-1.0",
                    1000.0,
                    json.dumps(self._source_metadata(), sort_keys=True),
                ),
            )
            connection.execute(
                """
                INSERT INTO build_projects(
                    project_id,source_id,slug,title,category,
                    implementation_language,upstream_reference,concepts_json,
                    difficulty,production_relevance,source_format,priority_tier,
                    metadata_json
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    PROJECT_ID,
                    SOURCE_ID,
                    "build-a-database",
                    "Build a Database",
                    "Database",
                    "Rust",
                    "https://example.invalid/build-a-database",
                    json.dumps(["storage", "indexing", "persistence"]),
                    8.0,
                    9.0,
                    "repository",
                    1,
                    json.dumps(self._project_metadata(), sort_keys=True),
                ),
            )

    def _snapshot(self):
        snapshots = load_active_byox_projects(self.database)
        self.assertEqual(1, len(snapshots))
        return snapshots[0]

    def _seed(self) -> dict[str, Any]:
        return seed_all_byox_reference_jobs(
            self.database,
            self.jobs,
            warehouse=self.warehouse,
        )

    def _expected_identity(self) -> tuple[str, str, str]:
        baseline = derive_byox_baseline(self._snapshot())
        builder_id = byox_s2_builder_job_id(baseline.baseline_sha256)
        reviewer_id = byox_s2_reviewer_job_id(
            baseline.baseline_sha256,
            builder_id,
            review_contract_version=BYOX_REVIEW_CONTRACT_VERSION,
        )
        return baseline.baseline_sha256, builder_id, reviewer_id

    def _dependencies(self, job_id: str) -> set[str]:
        with self.database.connect() as connection:
            return {
                str(row["depends_on_job_id"])
                for row in connection.execute(
                    """
                    SELECT depends_on_job_id FROM job_dependencies
                    WHERE job_id=?
                    """,
                    (job_id,),
                )
            }

    def _database_dump(self) -> str:
        with self.database.connect() as connection:
            return "\n".join(connection.iterdump())

    def _dispatchable_legacy_jobs(self) -> list[str]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT job_id,state,payload_json FROM jobs ORDER BY job_id"
            ).fetchall()
        result: list[str] = []
        for row in rows:
            if row["state"] not in DISPATCHABLE_STATES:
                continue
            identifier = str(row["job_id"])
            legacy_identifier = identifier.startswith(
                ("job_byox_build_v", "job_byox_review_v")
            )
            try:
                payload = json.loads(row["payload_json"])
            except (TypeError, ValueError, json.JSONDecodeError):
                payload = None
            policy = payload.get("seed_policy") if isinstance(payload, dict) else None
            legacy_policy = bool(
                isinstance(policy, dict)
                and policy.get("kind")
                in {"byox_reference_build", "byox_reference_review"}
            )
            if legacy_identifier or legacy_policy:
                result.append(identifier)
        return result

    def _legacy_spec(self) -> ByoxBuildJobSpec:
        return build_byox_job_spec(self._snapshot())

    def _legacy_payload(self, validator_count: int) -> dict[str, Any]:
        payload = copy.deepcopy(self._legacy_spec().payload)
        if validator_count == 6:
            payload["validators"] = [
                item
                for item in payload["validators"]
                if item.get("type") != "byox_code_presence"
            ]
        elif validator_count == 4:
            payload["validators"] = [
                item
                for item in payload["validators"]
                if item.get("type")
                not in {
                    "regular_files",
                    "forbidden_tree_names",
                    "byox_code_presence",
                }
            ]
            payload["retry_validation"] = False
        elif validator_count != 7:
            raise AssertionError("fixture supports only released 4/6/7 profiles")
        self.assertEqual(validator_count, len(payload["validators"]))
        return payload

    def _create_legacy_builder(
        self,
        payload: dict[str, Any],
        *,
        state: str,
        attempted: bool,
        max_attempts: int | None = None,
    ) -> str:
        spec = self._legacy_spec()
        job_id = self.jobs.create(
            spec.job_type,
            spec.worker_type,
            payload,
            priority=spec.priority,
            score_components=spec.score_components,
            dependencies=[CODEX_BACKEND_GATE_JOB_ID],
            max_attempts=spec.max_attempts if max_attempts is None else max_attempts,
            job_id=spec.job_id,
            model=spec.model,
            reasoning_effort=spec.reasoning_effort,
        )
        if not attempted:
            with self.database.transaction(immediate=True) as connection:
                connection.execute(
                    "UPDATE jobs SET state=? WHERE job_id=?",
                    (state, job_id),
                )
            return job_id

        workspace = self.warehouse / "workspaces" / job_id / "attempt-001"
        workspace.mkdir(parents=True)
        stdout = workspace / "stdout.log"
        stderr = workspace / "stderr.log"
        stdout.write_text("historical stdout\n", encoding="utf-8")
        stderr.write_text("historical stderr\n", encoding="utf-8")
        artifact_path = workspace / "attempt-artifact"
        artifact_path.mkdir()
        (artifact_path / "evidence.txt").write_text(
            "preserve this attempted artifact\n", encoding="utf-8"
        )
        digest = hashlib.sha256(job_id.encode("utf-8")).hexdigest()[:24]
        with self.database.transaction(immediate=True) as connection:
            created_at = float(
                connection.execute(
                    "SELECT created_at FROM jobs WHERE job_id=?", (job_id,)
                ).fetchone()["created_at"]
            )
            started_at = created_at + 1.0
            heartbeat_at = created_at + 2.0
            connection.execute(
                """
                UPDATE jobs
                SET state=?,attempt_count=1,started_at=?,heartbeat_at=?,workspace=?,
                    error=?,failure_kind=?
                WHERE job_id=?
                """,
                (
                    state,
                    started_at,
                    heartbeat_at,
                    str(workspace),
                    "historical blocked failure" if state == "BLOCKED" else None,
                    "validation_failure" if state == "BLOCKED" else None,
                    job_id,
                ),
            )
            connection.execute(
                """
                INSERT INTO job_runs(
                    run_id,job_id,attempt_number,backend,model,reasoning_effort,
                    session_id,started_at,finished_at,exit_code,stdout_path,
                    stderr_path,usage_json
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    f"run_{digest}",
                    job_id,
                    1,
                    "exec",
                    spec.model,
                    spec.reasoning_effort,
                    f"session-{digest}",
                    started_at,
                    heartbeat_at,
                    1,
                    str(stdout),
                    str(stderr),
                    '{"output_tokens":17}',
                ),
            )
            connection.execute(
                """
                INSERT INTO artifacts(
                    artifact_id,job_id,type,path,checksum,metadata_json,created_at,
                    validation_status,attempt_number,checksum_algorithm,
                    integrity_status
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    f"artifact_{digest}",
                    job_id,
                    "attempt-evidence",
                    str(artifact_path),
                    tree_sha256(artifact_path),
                    '{"classification":"historical-attempt-evidence"}',
                    heartbeat_at,
                    "GENERATED+PARTIAL",
                    1,
                    "tree-sha256-v2",
                    "VERIFIED_V2",
                ),
            )
        return job_id

    def _create_legacy_reviewer(
        self,
        builder_spec: ByoxBuildJobSpec,
        builder_payload: dict[str, Any],
    ) -> str:
        # The released base reviewer used policy v1 while its deterministic
        # verdict validator carries the independently versioned contract v2.
        version = 1
        reviewer_id = _byox_review_job_id(PROJECT_ID, policy_version=version)
        payload = _byox_reviewer_payload(
            project_id=PROJECT_ID,
            builder_job_id=builder_spec.job_id,
            builder_payload=builder_payload,
            specialized=False,
            policy_version=version,
        )
        return self.jobs.create(
            "codex_task",
            "examiner",
            payload,
            priority=round(max(35.0, min(94.0, builder_spec.priority - 1)), 4),
            score_components=builder_spec.score_components,
            dependencies=[CODEX_BACKEND_GATE_JOB_ID, builder_spec.job_id],
            max_attempts=2,
            job_id=reviewer_id,
            model="gpt-5.6-sol",
            reasoning_effort="ultra",
        )

    def _attempt_evidence(self, job_id: str) -> dict[str, Any]:
        with self.database.connect() as connection:
            job = connection.execute(
                """
                SELECT attempt_count,started_at,heartbeat_at,workspace
                FROM jobs WHERE job_id=?
                """,
                (job_id,),
            ).fetchone()
            runs = [
                dict(row)
                for row in connection.execute(
                    "SELECT * FROM job_runs WHERE job_id=? ORDER BY run_id", (job_id,)
                )
            ]
            artifacts = [
                dict(row)
                for row in connection.execute(
                    "SELECT * FROM artifacts WHERE job_id=? ORDER BY artifact_id",
                    (job_id,),
                )
            ]
        assert job is not None
        workspace = Path(str(job["workspace"]))
        return {
            "attempt_count": job["attempt_count"],
            "started_at": job["started_at"],
            "heartbeat_at": job["heartbeat_at"],
            "workspace": job["workspace"],
            "runs": runs,
            "artifacts": artifacts,
            "stdout": (workspace / "stdout.log").read_bytes(),
            "stderr": (workspace / "stderr.log").read_bytes(),
            "artifact_bytes": (
                workspace / "attempt-artifact" / "evidence.txt"
            ).read_bytes(),
        }

    def _make_legacy_builder_running(self, job_id: str) -> None:
        with self.database.transaction(immediate=True) as connection:
            created_at = float(
                connection.execute(
                    "SELECT created_at FROM jobs WHERE job_id=?", (job_id,)
                ).fetchone()["created_at"]
            )
            started_at = created_at + 1.0
            heartbeat_at = created_at + 2.0
            workspace = self.warehouse / "workspaces" / job_id / "attempt-001"
            workspace.mkdir(parents=True)
            connection.execute(
                "UPDATE jobs SET state='READY' WHERE job_id=?", (job_id,)
            )
            connection.execute(
                """
                UPDATE jobs
                SET state='CLAIMED',attempt_count=1,owner='legacy-worker',
                    lease_token='legacy-lease',lease_expires_at=?,heartbeat_at=?
                WHERE job_id=?
                """,
                (heartbeat_at + 1000.0, started_at, job_id),
            )
            connection.execute(
                """
                UPDATE jobs
                SET state='RUNNING',started_at=?,heartbeat_at=?,workspace=?
                WHERE job_id=?
                """,
                (started_at, heartbeat_at, str(workspace), job_id),
            )

    def test_fresh_publication_has_exact_bound_sol_ultra_graph(self) -> None:
        baseline_sha256, builder_id, reviewer_id = self._expected_identity()

        result = self._seed()

        self.assertEqual(1, result["active_catalog_entries"])
        self.assertEqual(1, result["covered_entries"])
        self.assertEqual(2, result["created_jobs"])
        self.assertEqual(
            {
                "mode": "seeded_generic_s2",
                "baseline_sha256": baseline_sha256,
                "builder": builder_id,
                "reviewer": reviewer_id,
                "review_policy_version": BYOX_REVIEW_CONTRACT_VERSION,
                "recognized_specialized_job_ids": [],
            },
            result["projects"][PROJECT_ID],
        )
        self.assertEqual({CODEX_BACKEND_GATE_JOB_ID}, self._dependencies(builder_id))
        self.assertEqual(
            {CODEX_BACKEND_GATE_JOB_ID, builder_id},
            self._dependencies(reviewer_id),
        )

        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT binding.*,job.state,job.attempt_count,job.model,
                       job.reasoning_effort,job.payload_json,job.created_at,
                       baseline.first_observed_at
                FROM byox_baseline_job_bindings binding
                JOIN jobs job ON job.job_id=binding.job_id
                JOIN byox_baseline_snapshots baseline
                  ON baseline.baseline_sha256=binding.baseline_sha256
                ORDER BY binding.role
                """
            ).fetchall()
            bindings = {str(row["role"]): row for row in rows}
            self.assertEqual({"builder", "reviewer"}, set(bindings))
            for row in rows:
                self.assertEqual(baseline_sha256, row["baseline_sha256"])
                self.assertEqual("DISCOVERED", row["state"])
                self.assertEqual(0, row["attempt_count"])
                self.assertEqual("gpt-5.6-sol", row["model"])
                self.assertEqual("ultra", row["reasoning_effort"])
                self.assertLessEqual(row["first_observed_at"], row["created_at"])
                self.assertLessEqual(row["created_at"], row["bound_at"])
                self.assertIsNotNone(load_verified_binding(connection, row["job_id"]))
            self.assertEqual(
                BYOX_SNAPSHOT_JOB_SCHEME_VERSION,
                bindings["builder"]["policy_version"],
            )
            self.assertIsNone(bindings["builder"]["builder_job_id"])
            self.assertEqual(
                BYOX_REVIEW_CONTRACT_VERSION,
                bindings["reviewer"]["policy_version"],
            )
            self.assertEqual(builder_id, bindings["reviewer"]["builder_job_id"])

        builder_payload = json.loads(bindings["builder"]["payload_json"])
        reviewer_payload = json.loads(bindings["reviewer"]["payload_json"])
        self.assertEqual(
            BYOX_BUILD_S2_POLICY_KIND,
            builder_payload["seed_policy"]["kind"],
        )
        self.assertEqual(
            BYOX_REVIEW_S2_POLICY_KIND,
            reviewer_payload["seed_policy"]["kind"],
        )
        self.assertEqual(baseline_sha256, builder_payload["baseline_sha256"])
        self.assertEqual(baseline_sha256, reviewer_payload["baseline_sha256"])
        source_provenance = builder_payload["provenance"]["source"]
        self.assertNotIn("ingested_at", source_provenance)
        self.assertNotIn("active_at_factory_time", source_provenance)
        self.assertEqual(
            "immutable-material-baseline",
            source_provenance["snapshot_kind"],
        )

    def test_exact_repeat_is_a_logical_read_only_noop(self) -> None:
        first = self._seed()
        before = self._database_dump()
        before_sha256 = hashlib.sha256(self.database.path.read_bytes()).hexdigest()

        second = self._seed()

        self.assertEqual(0, second["created_jobs"])
        self.assertEqual(first["projects"], second["projects"])
        self.assertEqual(before, self._database_dump())
        self.assertEqual(
            before_sha256,
            hashlib.sha256(self.database.path.read_bytes()).hexdigest(),
        )

    def test_volatile_reingest_reuses_the_exact_lineage(self) -> None:
        first = self._seed()["projects"][PROJECT_ID]
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                """
                UPDATE sources SET ingested_at=?,metadata_json=?
                WHERE source_id=?
                """,
                (
                    999999.0,
                    json.dumps(self._source_metadata(observation=2), sort_keys=True),
                    SOURCE_ID,
                ),
            )

        second_result = self._seed()
        second = second_result["projects"][PROJECT_ID]

        self.assertEqual(0, second_result["created_jobs"])
        self.assertEqual(first, second)
        with self.database.connect() as connection:
            self.assertEqual(
                1,
                connection.execute(
                    "SELECT COUNT(*) FROM byox_baseline_snapshots"
                ).fetchone()[0],
            )
            self.assertEqual(
                2,
                connection.execute(
                    "SELECT COUNT(*) FROM byox_baseline_job_bindings"
                ).fetchone()[0],
            )

    def test_meaningful_catalog_drift_publishes_a_new_lineage(self) -> None:
        first = self._seed()["projects"][PROJECT_ID]
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                "UPDATE build_projects SET title=? WHERE project_id=?",
                ("Build a Durable Database", PROJECT_ID),
            )

        second_result = self._seed()
        second = second_result["projects"][PROJECT_ID]

        self.assertEqual(2, second_result["created_jobs"])
        self.assertNotEqual(first["baseline_sha256"], second["baseline_sha256"])
        self.assertNotEqual(first["builder"], second["builder"])
        self.assertNotEqual(first["reviewer"], second["reviewer"])
        with self.database.connect() as connection:
            self.assertEqual(
                (2, 4, 4),
                (
                    connection.execute(
                        "SELECT COUNT(*) FROM byox_baseline_snapshots"
                    ).fetchone()[0],
                    connection.execute(
                        "SELECT COUNT(*) FROM byox_baseline_job_bindings"
                    ).fetchone()[0],
                    connection.execute(
                        """
                        SELECT COUNT(*) FROM jobs
                        WHERE job_id LIKE 'job_byox_build_s2_%'
                           OR job_id LIKE 'job_byox_review_s2_%'
                        """
                    ).fetchone()[0],
                ),
            )

    def test_collision_rolls_back_legacy_retirement_and_partial_s2_graph(self) -> None:
        legacy_spec = self._legacy_spec()
        legacy_id = self._create_legacy_builder(
            self._legacy_payload(7), state="READY", attempted=False
        )
        baseline_sha256, builder_id, reviewer_id = self._expected_identity()
        self.jobs.create(
            "codex_task",
            "examiner",
            {"seed_policy": {"kind": "collision"}, "project_id": PROJECT_ID},
            job_id=reviewer_id,
            dependencies=[CODEX_BACKEND_GATE_JOB_ID],
            max_attempts=2,
            model="gpt-5.6-sol",
            reasoning_effort="ultra",
        )
        with self.database.connect() as connection:
            before_events = connection.execute(
                "SELECT COUNT(*) FROM events"
            ).fetchone()[0]

        with self.assertRaises(ByoxBaselineConflict):
            self._seed()

        with self.database.connect() as connection:
            legacy = connection.execute(
                "SELECT state,cancel_requested FROM jobs WHERE job_id=?", (legacy_id,)
            ).fetchone()
            self.assertEqual(("READY", 0), tuple(legacy))
            self.assertIsNone(
                connection.execute(
                    "SELECT 1 FROM jobs WHERE job_id=?", (builder_id,)
                ).fetchone()
            )
            self.assertEqual(
                0,
                connection.execute(
                    """
                    SELECT COUNT(*) FROM byox_baseline_snapshots
                    WHERE baseline_sha256=?
                    """,
                    (baseline_sha256,),
                ).fetchone()[0],
            )
            self.assertEqual(
                0,
                connection.execute(
                    "SELECT COUNT(*) FROM byox_baseline_job_bindings"
                ).fetchone()[0],
            )
            self.assertEqual(
                before_events,
                connection.execute("SELECT COUNT(*) FROM events").fetchone()[0],
            )
        self.assertEqual(legacy_spec.job_id, legacy_id)

    def test_concurrent_seeders_converge_on_one_lineage(self) -> None:
        barrier = threading.Barrier(2)
        results: list[dict[str, Any]] = []
        failures: list[BaseException] = []

        def seed() -> None:
            try:
                barrier.wait(timeout=5)
                database = Database(self.database.path, MIGRATIONS)
                results.append(
                    seed_all_byox_reference_jobs(
                        database,
                        JobRepository(database),
                        warehouse=self.warehouse,
                    )
                )
            except BaseException as error:  # pragma: no cover - asserted below
                failures.append(error)

        threads = [threading.Thread(target=seed) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)

        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertEqual([], failures)
        self.assertEqual([0, 2], sorted(result["created_jobs"] for result in results))
        with self.database.connect() as connection:
            self.assertEqual(
                (1, 2, 2),
                (
                    connection.execute(
                        "SELECT COUNT(*) FROM byox_baseline_snapshots"
                    ).fetchone()[0],
                    connection.execute(
                        "SELECT COUNT(*) FROM byox_baseline_job_bindings"
                    ).fetchone()[0],
                    connection.execute(
                        """
                        SELECT COUNT(*) FROM jobs
                        WHERE job_id LIKE 'job_byox_build_s2_%'
                           OR job_id LIKE 'job_byox_review_s2_%'
                        """
                    ).fetchone()[0],
                ),
            )

    def test_exact_four_validator_attempted_ready_is_retired_with_evidence(self) -> None:
        legacy_id = self._create_legacy_builder(
            self._legacy_payload(4), state="READY", attempted=True
        )
        before = self._attempt_evidence(legacy_id)

        result = self._seed()

        self.assertEqual(2, result["created_jobs"])
        self.assertEqual(before, self._attempt_evidence(legacy_id))
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT state,attempt_count,cancel_requested,finished_at,
                       started_at,heartbeat_at,workspace
                FROM jobs WHERE job_id=?
                """,
                (legacy_id,),
            ).fetchone()
        self.assertEqual("CANCELLED", row["state"])
        self.assertEqual(1, row["attempt_count"])
        self.assertEqual(1, row["cancel_requested"])
        self.assertIsNotNone(row["finished_at"])
        self.assertEqual(before["started_at"], row["started_at"])
        self.assertEqual(before["heartbeat_at"], row["heartbeat_at"])
        self.assertEqual(before["workspace"], row["workspace"])
        self.assertEqual([], self._dispatchable_legacy_jobs())

    def test_exact_six_validator_blocked_graph_is_fully_retired(self) -> None:
        builder_spec = self._legacy_spec()
        builder_payload = self._legacy_payload(6)
        builder_id = self._create_legacy_builder(
            builder_payload, state="BLOCKED", attempted=True
        )
        reviewer_id = self._create_legacy_reviewer(builder_spec, builder_payload)
        before = self._attempt_evidence(builder_id)

        result = self._seed()

        self.assertEqual(2, result["created_jobs"])
        self.assertEqual(before, self._attempt_evidence(builder_id))
        with self.database.connect() as connection:
            states = {
                str(row["job_id"]): str(row["state"])
                for row in connection.execute(
                    "SELECT job_id,state FROM jobs WHERE job_id IN (?,?)",
                    (builder_id, reviewer_id),
                )
            }
        self.assertEqual(
            {builder_id: "CANCELLED", reviewer_id: "CANCELLED"}, states
        )
        self.assertEqual([], self._dispatchable_legacy_jobs())

    def test_active_legacy_worker_defers_the_entire_project(self) -> None:
        builder_spec = self._legacy_spec()
        builder_payload = self._legacy_payload(6)
        builder_id = self._create_legacy_builder(
            builder_payload, state="DISCOVERED", attempted=False
        )
        reviewer_id = self._create_legacy_reviewer(builder_spec, builder_payload)
        self._make_legacy_builder_running(builder_id)

        result = self._seed()

        self.assertEqual(0, result["created_jobs"])
        self.assertEqual(1, result["deferred_active_legacy"])
        self.assertEqual(
            {
                "mode": "deferred_active_legacy",
                "baseline_sha256": self._expected_identity()[0],
                "builder": None,
                "reviewer": None,
                "review_policy_version": BYOX_REVIEW_CONTRACT_VERSION,
                "recognized_specialized_job_ids": [],
            },
            result["projects"][PROJECT_ID],
        )
        with self.database.connect() as connection:
            builder = connection.execute(
                "SELECT state,cancel_requested FROM jobs WHERE job_id=?",
                (builder_id,),
            ).fetchone()
            reviewer = connection.execute(
                "SELECT state,cancel_requested FROM jobs WHERE job_id=?",
                (reviewer_id,),
            ).fetchone()
            self.assertEqual(("RUNNING", 1), tuple(builder))
            self.assertEqual(("DISCOVERED", 0), tuple(reviewer))
            self.assertEqual(
                0,
                connection.execute(
                    "SELECT COUNT(*) FROM byox_baseline_snapshots"
                ).fetchone()[0],
            )
            self.assertEqual(
                0,
                connection.execute(
                    "SELECT COUNT(*) FROM byox_baseline_job_bindings"
                ).fetchone()[0],
            )

    def test_conflicting_legacy_definition_aborts_without_publication(self) -> None:
        legacy_id = self._create_legacy_builder(
            self._legacy_payload(7),
            state="READY",
            attempted=False,
            max_attempts=3,
        )

        with self.assertRaisesRegex(RuntimeError, "exact released definition"):
            self._seed()

        with self.database.connect() as connection:
            self.assertEqual(
                ("READY", 0),
                tuple(
                    connection.execute(
                        "SELECT state,cancel_requested FROM jobs WHERE job_id=?",
                        (legacy_id,),
                    ).fetchone()
                ),
            )
            self.assertEqual(
                0,
                connection.execute(
                    "SELECT COUNT(*) FROM byox_baseline_snapshots"
                ).fetchone()[0],
            )
            self.assertEqual(
                0,
                connection.execute(
                    "SELECT COUNT(*) FROM byox_baseline_job_bindings"
                ).fetchone()[0],
            )

    def test_malformed_dispatchable_payload_aborts_without_publication(self) -> None:
        malformed_id = "job_byox_build_v1_ffffffffffffffffffffffffffffffff"
        malformed = (
            '{"seed_policy":{"kind":"byox_reference_build","version":1},'
            f'"project_id":"{PROJECT_ID}"'
        )
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                """
                INSERT INTO jobs(
                    job_id,type,worker_type,state,priority,score_components_json,
                    payload_json,attempt_count,max_attempts,created_at,model,
                    reasoning_effort
                ) VALUES (?,?,?,'DISCOVERED',?,?,?,?,?,?,?,?)
                """,
                (
                    malformed_id,
                    "codex_task",
                    "reference_builder",
                    80.0,
                    "{}",
                    malformed,
                    0,
                    2,
                    1001.0,
                    "gpt-5.6-sol",
                    "ultra",
                ),
            )
            connection.execute(
                """
                INSERT INTO job_dependencies(job_id,depends_on_job_id)
                VALUES (?,?)
                """,
                (malformed_id, CODEX_BACKEND_GATE_JOB_ID),
            )
            connection.execute(
                "UPDATE jobs SET state='READY' WHERE job_id=?",
                (malformed_id,),
            )

        with self.assertRaisesRegex(RuntimeError, "ambiguous payload|invalid payload"):
            self._seed()

        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT state,payload_json FROM jobs WHERE job_id=?", (malformed_id,)
            ).fetchone()
            self.assertEqual(("READY", malformed), tuple(row))
            self.assertEqual(
                0,
                connection.execute(
                    "SELECT COUNT(*) FROM byox_baseline_snapshots"
                ).fetchone()[0],
            )
            self.assertEqual(
                0,
                connection.execute(
                    "SELECT COUNT(*) FROM byox_baseline_job_bindings"
                ).fetchone()[0],
            )

    def test_database_and_warehouse_boundaries_fail_before_writes(self) -> None:
        other_database = Database(self.root / "other-state" / "factory.db", MIGRATIONS)
        other_database.migrate()
        other_jobs = JobRepository(other_database)

        with self.assertRaisesRegex(ValueError, "same database"):
            seed_all_byox_reference_jobs(
                self.database,
                other_jobs,
                warehouse=self.warehouse,
            )
        with self.assertRaisesRegex(ValueError, "canonical absolute Path"):
            seed_all_byox_reference_jobs(
                self.database,
                self.jobs,
                warehouse=Path("relative-warehouse"),
            )

        with self.database.connect() as connection:
            self.assertEqual(
                (0, 0),
                (
                    connection.execute(
                        "SELECT COUNT(*) FROM byox_baseline_snapshots"
                    ).fetchone()[0],
                    connection.execute(
                        "SELECT COUNT(*) FROM byox_baseline_job_bindings"
                    ).fetchone()[0],
                ),
            )
        with other_database.connect() as connection:
            self.assertEqual(0, connection.execute("SELECT COUNT(*) FROM jobs").fetchone()[0])


if __name__ == "__main__":
    unittest.main()
