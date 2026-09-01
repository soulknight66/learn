from __future__ import annotations

import asyncio
import copy
import contextlib
import hashlib
import io
import json
import shutil
import tempfile
import threading
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from learnfactory.byox_jobs import build_byox_job_spec, load_active_byox_projects
from learnfactory.cli import build_parser, cmd_seed_byox_repairs
from learnfactory.byox_remediation import (
    BYOX_CANONICAL_CHALLENGE_ROOTS,
    BYOX_CANONICAL_DIRECTORY_ROOTS,
    BYOX_REPAIR_ARTIFACT_TYPE,
    BYOX_REPAIR_POLICY_KIND,
    DEFAULT_MAX_REPAIR_GENERATIONS,
    _validated_repair_inventory,
    repair_builder_job_id,
    repair_reviewer_job_id,
    seed_byox_remediation_jobs,
)
from learnfactory.config import load_settings
from learnfactory.db import Database
from learnfactory.handlers import (
    HandlerFailure,
    JobHandlers,
    _byox_repair_archive_selection,
    _enforce_byox_remediation_backend,
    _validate_byox_repair_outputs,
)
from learnfactory.jobs import JobRepository
from learnfactory.seeding import (
    CODEX_BACKEND_GATE_JOB_ID,
    _byox_reviewer_payload,
)
from learnfactory.scheduler import Scheduler
from learnfactory.util import canonical_json, now, tree_sha256
from learnfactory.workspace import WorkspaceManager


ROOT = Path(__file__).resolve().parents[1]


class ByoxRemediationTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="learnfactory-byox-repair-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.config_path = self.root / "factory.toml"
        self.config_path.write_text(
            "\n".join(
                [
                    "[factory]",
                    f'database = "{self.root / "factory.db"}"',
                    f'warehouse = "{self.root / "warehouse"}"',
                    "lease_seconds = 30",
                    "heartbeat_seconds = 1",
                    "poll_seconds = 0.01",
                    "max_concurrency = 2",
                    "shutdown_grace_seconds = 1",
                    "[backend]",
                    'name = "exec"',
                    'command = "codex"',
                    'permission_profile = "factory-isolated"',
                    'model = "gpt-5.6-sol"',
                    'reasoning_effort = "ultra"',
                    "timeout_seconds = 5",
                    "[retry]",
                    "base_seconds = 0.01",
                    "max_seconds = 0.02",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        self.settings = load_settings(self.config_path)
        self.database = Database(self.settings.database, self.settings.migrations)
        self.database.migrate()
        self.manager = WorkspaceManager(self.settings.warehouse, self.database)
        self.manager.initialize()
        self.jobs = JobRepository(self.database, retry_base=0.01, retry_max=0.02)
        self._insert_finished_job(
            CODEX_BACKEND_GATE_JOB_ID,
            {
                "seed_policy": {
                    "kind": "codex_backend_gate",
                    "version": 1,
                    "role": "gate",
                }
            },
            artifact_type="backend-capability-gate",
            files={"BACKEND_READY.txt": "ready\n"},
            worker_type="maintenance",
        )

    def _catalog_project(self, project_id: str) -> None:
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO sources(
                    source_id,type,name,path,upstream_url,commit_hash,license,
                    ingested_at,metadata_json,is_active
                ) VALUES (?,?,?,?,?,?,?,?,?,1)
                """,
                (
                    "source_byox",
                    "project_catalog",
                    "Build Your Own X",
                    "/public/build-your-own-x",
                    "https://example.invalid/byox",
                    "commit-byox",
                    "CC0-1.0",
                    1234.5,
                    canonical_json(
                        {"adapter": "build_your_own_x", "extractor_version": "test"}
                    ),
                ),
            )
            connection.execute(
                """
                INSERT INTO build_projects(
                    project_id,source_id,slug,title,category,implementation_language,
                    upstream_reference,concepts_json,difficulty,production_relevance,
                    source_format,priority_tier,metadata_json
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    project_id,
                    "source_byox",
                    f"project-{project_id}",
                    f"Project {project_id}",
                    "Systems",
                    "Python",
                    f"https://example.invalid/{project_id}",
                    '["systems","testing"]',
                    7.0,
                    8.0,
                    "repository",
                    1,
                    canonical_json({"linked_resource_license": "NOASSERTION"}),
                ),
            )

    def _canonical_pack(self, marker: str) -> dict[str, str]:
        files: dict[str, str] = {}
        directory_roots = {
            "starter",
            "public_tests",
            "environment",
            "sealed",
            "adversarial",
            "debugging",
            "review_exercises",
            "benchmarks",
        }
        for root in sorted(BYOX_CANONICAL_CHALLENGE_ROOTS):
            if root in directory_roots:
                files[f"{root}/README.md"] = f"{marker}: {root}\n"
            elif root in {"MANIFEST.yaml", "PROVENANCE.json"}:
                files[root] = "{}\n"
            else:
                files[root] = f"{marker}: {root}\n"
        files["implementation/src.py"] = f"print({marker!r})\n"
        return files

    def _artifact_tree(self, job_id: str, files: dict[str, str]) -> Path:
        path = self.settings.warehouse / "artifacts" / "tests" / job_id / "attempt-001"
        path.mkdir(parents=True)
        for relative, content in files.items():
            target = path / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        return path

    def _insert_finished_job(
        self,
        job_id: str,
        payload: dict[str, object],
        *,
        artifact_type: str,
        files: dict[str, str],
        metadata: dict[str, object] | None = None,
        dependencies: tuple[str, ...] = (),
        worker_type: str = "reference_builder",
        model: str = "gpt-5.6-sol",
        reasoning_effort: str = "ultra",
    ) -> dict[str, object]:
        artifact_path = self._artifact_tree(job_id, files)
        checksum = tree_sha256(artifact_path)
        artifact_id = f"artifact_{job_id.removeprefix('job_')}"
        timestamp = now()
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                """
                INSERT INTO jobs(
                    job_id,type,worker_type,state,priority,score_components_json,
                    payload_json,attempt_count,max_attempts,created_at,started_at,
                    finished_at,model,reasoning_effort
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    job_id,
                    "codex_task",
                    worker_type,
                    "SUCCEEDED",
                    50.0,
                    "{}",
                    canonical_json(payload),
                    1,
                    2,
                    timestamp,
                    timestamp,
                    timestamp,
                    model,
                    reasoning_effort,
                ),
            )
            for dependency in dependencies:
                connection.execute(
                    "INSERT INTO job_dependencies(job_id,depends_on_job_id) VALUES (?,?)",
                    (job_id, dependency),
                )
            connection.execute(
                """
                INSERT INTO artifacts(
                    artifact_id,job_id,type,path,checksum,metadata_json,created_at,
                    validation_status,attempt_number,checksum_algorithm,integrity_status
                ) VALUES (?,?,?,?,?,?,?,?,?,'tree-sha256-v2','VERIFIED_V2')
                """,
                (
                    artifact_id,
                    job_id,
                    artifact_type,
                    str(artifact_path),
                    checksum,
                    canonical_json(metadata or {}),
                    timestamp,
                    "GENERATED",
                    1,
                ),
            )
            connection.execute(
                """
                INSERT INTO artifact_validation_labels(
                    artifact_id,label,evidence_json,created_at
                ) VALUES (?,'GENERATED','{}',?)
                """,
                (artifact_id, timestamp),
            )
        return {
            "job_id": job_id,
            "artifact_id": artifact_id,
            "artifact_type": artifact_type,
            "artifact_checksum": checksum,
            "checksum_algorithm": "tree-sha256-v2",
            "artifact_attempt": 1,
        }

    def _complete_seeded_job(
        self,
        job_id: str,
        *,
        artifact_type: str,
        files: dict[str, str],
        metadata: dict[str, object] | None = None,
    ) -> dict[str, object]:
        artifact_path = self._artifact_tree(job_id, files)
        if artifact_type == BYOX_REPAIR_ARTIFACT_TYPE:
            metadata = self._repair_artifact_metadata(job_id, files)
        checksum = tree_sha256(artifact_path)
        artifact_id = f"artifact_{job_id.removeprefix('job_')}"
        timestamp = now()
        with self.database.transaction(immediate=True) as connection:
            row = connection.execute(
                "SELECT state FROM jobs WHERE job_id=?", (job_id,)
            ).fetchone()
            assert row is not None
            if row["state"] == "DISCOVERED":
                connection.execute(
                    "UPDATE jobs SET state='READY' WHERE job_id=?", (job_id,)
                )
            connection.execute(
                """
                UPDATE jobs SET state='CLAIMED',owner='test-owner',lease_token='test-lease',
                    lease_expires_at=?,attempt_count=1,started_at=?
                WHERE job_id=? AND state='READY'
                """,
                (timestamp + 60, timestamp, job_id),
            )
            connection.execute(
                "UPDATE jobs SET state='RUNNING' WHERE job_id=?", (job_id,)
            )
            connection.execute(
                """
                INSERT INTO artifacts(
                    artifact_id,job_id,type,path,checksum,metadata_json,created_at,
                    validation_status,attempt_number,checksum_algorithm,integrity_status
                ) VALUES (?,?,?,?,?,?,?,?,?,'tree-sha256-v2','VERIFIED_V2')
                """,
                (
                    artifact_id,
                    job_id,
                    artifact_type,
                    str(artifact_path),
                    checksum,
                    canonical_json(metadata or {}),
                    timestamp,
                    "GENERATED",
                    1,
                ),
            )
            connection.execute(
                """
                INSERT INTO artifact_validation_labels(
                    artifact_id,label,evidence_json,created_at
                ) VALUES (?,'GENERATED','{}',?)
                """,
                (artifact_id, timestamp),
            )
            connection.execute(
                """
                UPDATE jobs SET state='SUCCEEDED',owner=NULL,lease_token=NULL,
                    lease_expires_at=NULL,finished_at=? WHERE job_id=?
                """,
                (timestamp, job_id),
            )
        return {
            "job_id": job_id,
            "artifact_id": artifact_id,
            "artifact_type": artifact_type,
            "artifact_checksum": checksum,
            "checksum_algorithm": "tree-sha256-v2",
            "artifact_attempt": 1,
        }

    def _repair_artifact_metadata(
        self, job_id: str, files: dict[str, str]
    ) -> dict[str, object]:
        job = self.jobs.get(job_id)
        assert job is not None
        payload = job["payload"]
        profile = payload["artifact_profile"]
        trigger = payload["remediation_snapshot"]["trigger"]
        prior = trigger["builder"]
        source_root_kinds: dict[str, str] = {}
        for relative in files:
            parts = Path(relative).parts
            kind = "directory" if len(parts) > 1 else "file"
            existing = source_root_kinds.get(parts[0])
            if existing is not None and existing != kind:
                raise AssertionError(f"conflicting fixture root type: {parts[0]}")
            source_root_kinds[parts[0]] = kind
        source_paths = sorted(source_root_kinds)
        source_inventory = self._inventory_record(
            profile, prior["artifact_type"], source_paths, source_root_kinds
        )
        projected_paths = sorted(
            set(source_paths) | set(BYOX_CANONICAL_CHALLENGE_ROOTS)
        )
        projected_root_kinds = dict(source_root_kinds)
        for path in BYOX_CANONICAL_CHALLENGE_ROOTS:
            projected_root_kinds[path] = (
                "directory" if path in BYOX_CANONICAL_DIRECTORY_ROOTS else "file"
            )
        inventory = self._inventory_record(
            profile,
            BYOX_REPAIR_ARTIFACT_TYPE,
            projected_paths,
            projected_root_kinds,
        )
        added_paths = sorted(
            set(BYOX_CANONICAL_CHALLENGE_ROOTS) - set(source_paths)
        )
        added_root_kinds = {
            path: projected_root_kinds[path] for path in added_paths
        }
        return {
            "repair_archive_selection": {
                "schema_version": 1,
                "source": {
                    "job_id": prior["job_id"],
                    "artifact_id": prior["artifact_id"],
                    "artifact_type": prior["artifact_type"],
                    "artifact_checksum": prior["artifact_checksum"],
                    "artifact_checksum_algorithm": prior["checksum_algorithm"],
                    "artifact_attempt": prior["artifact_attempt"],
                },
                "source_artifact_inventory": source_inventory,
                "required_added_inventory": {
                    "schema_version": 1,
                    "paths": added_paths,
                    "root_kinds": added_root_kinds,
                    "paths_sha256": self._list_sha256(added_paths),
                    "root_kinds_sha256": hashlib.sha256(
                        canonical_json(added_root_kinds).encode("utf-8")
                    ).hexdigest(),
                },
                "artifact_inventory": inventory,
                "paths": projected_paths,
                "paths_sha256": self._list_sha256(projected_paths),
            }
        }

    def _inventory_record(
        self,
        profile: str,
        artifact_type: str,
        paths: list[str],
        root_kinds: dict[str, str],
    ) -> dict[str, object]:
        excluded: list[str] = []
        normalized_kinds = dict(sorted(root_kinds.items()))
        return {
            "schema_version": 1,
            "profile": profile,
            "source_artifact_type": artifact_type,
            "original_paths": paths,
            "selected_paths": paths,
            "excluded_paths": excluded,
            "root_kinds": normalized_kinds,
            "original_paths_sha256": self._list_sha256(paths),
            "selected_paths_sha256": self._list_sha256(paths),
            "excluded_paths_sha256": self._list_sha256(excluded),
            "root_kinds_sha256": hashlib.sha256(
                canonical_json(normalized_kinds).encode("utf-8")
            ).hexdigest(),
        }

    @staticmethod
    def _list_sha256(values: list[str]) -> str:
        return hashlib.sha256(canonical_json(values).encode("utf-8")).hexdigest()

    def _insert_review_validations(
        self, review_job_id: str, verdict: str, *, attempt: int = 1
    ) -> None:
        timestamp = now()
        records = (
            (
                "byox-independent-review-schema",
                {"error_count": 0, "errors": []},
            ),
            (
                "byox-independent-review-verdict",
                {
                    "path": "EVALUATION.json",
                    "verdict": verdict,
                    "reviewer_recommends_acceptance": verdict == "PASS",
                    "workflow_accepted": False,
                },
            ),
            (
                "byox-independent-review-concrete-evidence",
                {"expected_exit": 0},
            ),
        )
        with self.database.transaction(immediate=True) as connection:
            for index, (validator, evidence) in enumerate(records, start=1):
                connection.execute(
                    """
                    INSERT INTO validations(
                        validation_id,job_id,validator,status,evidence_json,
                        started_at,finished_at,attempt_number,claims_json
                    ) VALUES (?,?,?,'PASS',?,?,?,?, '[]')
                    """,
                    (
                        f"validation_{review_job_id}_{index}_{attempt}",
                        review_job_id,
                        validator,
                        canonical_json(evidence),
                        timestamp,
                        timestamp,
                        attempt,
                    ),
                )

    def _review_metadata(self, builder: dict[str, object]) -> dict[str, object]:
        return {
            "staged_inputs": [
                {
                    "origin": "dependency-artifact",
                    "path": "CANDIDATE/README.md",
                    "artifact_subpath": "README.md",
                    "artifact_checksum_algorithm": builder["checksum_algorithm"],
                    **builder,
                }
            ]
        }

    def _base_graph(
        self,
        project_id: str,
        verdict: str = "REVISE",
        *,
        validation_attempt: int | None = 1,
        valid_binding: bool = True,
        builder_artifact_type: str = "byox-challenge-pack",
        builder_files: dict[str, str] | None = None,
    ) -> tuple[str, str, dict[str, object], dict[str, object]]:
        self._catalog_project(project_id)
        snapshot = {
            item.project_id: item for item in load_active_byox_projects(self.database)
        }[project_id]
        template = build_byox_job_spec(snapshot)
        builder_id = template.job_id
        builder_payload = copy.deepcopy(template.payload)
        builder_payload["artifact_type"] = builder_artifact_type
        builder = self._insert_finished_job(
            builder_id,
            builder_payload,
            artifact_type=builder_artifact_type,
            files=builder_files or self._canonical_pack("base"),
            dependencies=(CODEX_BACKEND_GATE_JOB_ID,),
        )
        review_id = f"job_base_review_{project_id}"
        review_payload = _byox_reviewer_payload(
            project_id=project_id,
            builder_job_id=builder_id,
            builder_payload=builder_payload,
            specialized=False,
            policy_version=2,
        )
        metadata = self._review_metadata(builder)
        if not valid_binding:
            metadata["staged_inputs"][0]["artifact_checksum"] = "0" * 64
        review = self._insert_finished_job(
            review_id,
            review_payload,
            artifact_type="byox-independent-review",
            files={
                "EVALUATION.json": canonical_json(
                    {
                        "project_id": project_id,
                        "builder_job_id": builder_id,
                        "verdict": verdict,
                        "evidence": ["observed failure"],
                        "checks_run": ["bounded check"],
                        "limitations": [],
                    }
                )
                + "\n",
                "REVIEW.md": f"# {verdict}\nConcrete finding.\n",
                "VALIDATION.md": "# Independent checks\n",
            },
            metadata=metadata,
            dependencies=(CODEX_BACKEND_GATE_JOB_ID, builder_id),
            worker_type="examiner",
        )
        if validation_attempt is not None:
            self._insert_review_validations(
                review_id, verdict, attempt=validation_attempt
            )
        return builder_id, review_id, builder, review

    def _complete_repair_review(
        self, project_id: str, generation: int, verdict: str
    ) -> dict[str, object]:
        builder_id = repair_builder_job_id(project_id, generation)
        reviewer_id = repair_reviewer_job_id(project_id, generation)
        with self.database.connect() as connection:
            artifact = connection.execute(
                """
                SELECT artifact_id,type,checksum,checksum_algorithm,attempt_number
                FROM artifacts WHERE job_id=?
                """,
                (builder_id,),
            ).fetchone()
        assert artifact is not None
        builder = {
            "job_id": builder_id,
            "artifact_id": artifact["artifact_id"],
            "artifact_type": artifact["type"],
            "artifact_checksum": artifact["checksum"],
            "checksum_algorithm": artifact["checksum_algorithm"],
            "artifact_attempt": artifact["attempt_number"],
        }
        review = self._complete_seeded_job(
            reviewer_id,
            artifact_type="byox-independent-review",
            files={
                "EVALUATION.json": canonical_json(
                    {
                        "project_id": project_id,
                        "builder_job_id": builder_id,
                        "verdict": verdict,
                        "evidence": ["repair check"],
                        "checks_run": ["test"],
                        "limitations": [],
                    }
                )
                + "\n",
                "REVIEW.md": f"# {verdict}\n",
                "VALIDATION.md": "# Checks\n",
            },
            metadata=self._review_metadata(builder),
        )
        self._insert_review_validations(reviewer_id, verdict)
        return review

    def test_negative_review_seeds_immutable_exactly_bound_repair_builder(self) -> None:
        project_id = "project-negative"
        builder_id, review_id, builder, review = self._base_graph(project_id, "REVISE")
        with self.database.connect() as connection:
            original = {
                row["job_id"]: row["payload_json"]
                for row in connection.execute(
                    "SELECT job_id,payload_json FROM jobs WHERE job_id IN (?,?)",
                    (builder_id, review_id),
                )
            }

        result = seed_byox_remediation_jobs(
            self.database, self.jobs, project_ids=[project_id]
        )

        self.assertEqual(DEFAULT_MAX_REPAIR_GENERATIONS, result["max_repair_generations"])
        self.assertEqual(1, result["created_repair_builders"])
        project = result["projects"][project_id]
        self.assertEqual("REPAIR_BUILDER_SEEDED", project["status"])
        repair_id = repair_builder_job_id(project_id, 1)
        repair = self.jobs.get(repair_id)
        assert repair is not None
        self.assertEqual("DISCOVERED", repair["state"])
        self.assertEqual("codex_task", repair["type"])
        self.assertEqual("reference_builder", repair["worker_type"])
        self.assertEqual("gpt-5.6-sol", repair["model"])
        self.assertEqual("ultra", repair["reasoning_effort"])
        self.assertEqual(BYOX_REPAIR_ARTIFACT_TYPE, repair["payload"]["artifact_type"])
        self.assertEqual(["GENERATED", "PARTIAL"], repair["payload"]["validation_status"])
        self.assertTrue(repair["payload"]["independent_validation_required"])
        self.assertFalse(repair["payload"]["productionized"])
        self.assertEqual(
            {"name": "exec", "permission_profile": "factory-isolated"},
            repair["payload"]["required_backend"],
        )
        self.assertEqual(["PRIOR_BUILD", "PRIOR_REVIEW"], repair["payload"]["protected_input_roots"])
        inputs = repair["payload"]["inputs_from_dependencies"]
        self.assertEqual(4, len(inputs))
        self.assertTrue(inputs[0]["artifact_root"])
        self.assertEqual("PRIOR_BUILD", inputs[0]["destination"])
        self.assertEqual(builder, {key: inputs[0][key] for key in builder})
        self.assertEqual(
            {"EVALUATION.json", "REVIEW.md", "VALIDATION.md"},
            {item["subpath"] for item in inputs[1:]},
        )
        for item in inputs[1:]:
            self.assertEqual(review, {key: item[key] for key in review})
        self.assertEqual(
            {CODEX_BACKEND_GATE_JOB_ID, builder_id, review_id},
            self._dependencies(repair_id),
        )
        self.assertIn("repair-v1", repair["payload"]["artifact_path"])
        self.assertNotIn("student_id", repair["payload"])

        again = seed_byox_remediation_jobs(
            self.database, self.jobs, project_ids=[project_id]
        )
        self.assertEqual(0, again["created_jobs"])
        self.assertEqual(
            "WAITING_FOR_REPAIR_BUILDER", again["projects"][project_id]["status"]
        )
        with self.database.connect() as connection:
            after = {
                row["job_id"]: row["payload_json"]
                for row in connection.execute(
                    "SELECT job_id,payload_json FROM jobs WHERE job_id IN (?,?)",
                    (builder_id, review_id),
                )
            }
        self.assertEqual(original, after)

    def test_repair_artifact_then_seeds_fresh_exactly_bound_reviewer(self) -> None:
        project_id = "project-reviewer"
        self._base_graph(project_id, "FAIL")
        seed_byox_remediation_jobs(self.database, self.jobs, project_ids=[project_id])
        repair_id = repair_builder_job_id(project_id, 1)
        repaired = self._complete_seeded_job(
            repair_id,
            artifact_type=BYOX_REPAIR_ARTIFACT_TYPE,
            files=self._canonical_pack("repaired"),
            metadata={"repair_archive_selection": {"paths": sorted(BYOX_CANONICAL_CHALLENGE_ROOTS)}},
        )

        result = seed_byox_remediation_jobs(
            self.database, self.jobs, project_ids=[project_id]
        )

        self.assertEqual(1, result["created_reviewers"])
        self.assertEqual("REVIEWER_SEEDED", result["projects"][project_id]["status"])
        reviewer_id = repair_reviewer_job_id(project_id, 1)
        reviewer = self.jobs.get(reviewer_id)
        assert reviewer is not None
        self.assertEqual("examiner", reviewer["worker_type"])
        self.assertEqual("gpt-5.6-sol", reviewer["model"])
        self.assertEqual("ultra", reviewer["reasoning_effort"])
        self.assertEqual(["CANDIDATE"], reviewer["payload"]["protected_input_roots"])
        [candidate] = reviewer["payload"]["inputs_from_dependencies"]
        self.assertTrue(candidate["artifact_root"])
        self.assertEqual("CANDIDATE", candidate["destination"])
        self.assertEqual(repaired, {key: candidate[key] for key in repaired})
        self.assertEqual(
            {CODEX_BACKEND_GATE_JOB_ID, repair_id}, self._dependencies(reviewer_id)
        )
        self.assertIn("repair-v1/review-v1", reviewer["payload"]["artifact_path"])
        acceptance = [
            item
            for item in reviewer["payload"]["validators"]
            if item["type"] == "review_acceptance"
        ]
        self.assertEqual([{"type": "review_acceptance", "name": "byox-independent-review-acceptance", "mode": "closed"}], acceptance)

    def test_finite_cap_and_second_generation_chain(self) -> None:
        project_id = "project-cap"
        self._base_graph(project_id, "REVISE")
        seed_byox_remediation_jobs(self.database, self.jobs, project_ids=[project_id])
        first_builder = repair_builder_job_id(project_id, 1)
        self._complete_seeded_job(
            first_builder,
            artifact_type=BYOX_REPAIR_ARTIFACT_TYPE,
            files=self._canonical_pack("repair-one"),
        )
        seed_byox_remediation_jobs(self.database, self.jobs, project_ids=[project_id])
        first_reviewer = repair_reviewer_job_id(project_id, 1)
        first_review = self._complete_repair_review(project_id, 1, "FAIL")

        capped = seed_byox_remediation_jobs(
            self.database,
            self.jobs,
            project_ids=[project_id],
            max_repair_generations=1,
        )
        self.assertEqual("REPAIR_LIMIT_EXHAUSTED", capped["projects"][project_id]["status"])
        self.assertIsNone(self.jobs.get(repair_builder_job_id(project_id, 2)))

        second = seed_byox_remediation_jobs(
            self.database,
            self.jobs,
            project_ids=[project_id],
            max_repair_generations=2,
        )
        self.assertEqual("REPAIR_BUILDER_SEEDED", second["projects"][project_id]["status"])
        second_builder = self.jobs.get(repair_builder_job_id(project_id, 2))
        assert second_builder is not None
        self.assertEqual(
            2, second_builder["payload"]["seed_policy"]["generation"]
        )
        review_inputs = second_builder["payload"]["inputs_from_dependencies"][1:]
        self.assertEqual({first_reviewer}, {item["job_id"] for item in review_inputs})
        for item in review_inputs:
            self.assertEqual(first_review, {key: item[key] for key in first_review})
        self.assertEqual(
            {CODEX_BACKEND_GATE_JOB_ID, first_builder, first_reviewer},
            self._dependencies(repair_builder_job_id(project_id, 2)),
        )

    def test_validated_pass_stops_without_claiming_workflow_completion(self) -> None:
        project_id = "project-pass"
        self._base_graph(project_id, "REVISE")
        seed_byox_remediation_jobs(self.database, self.jobs, project_ids=[project_id])
        self._complete_seeded_job(
            repair_builder_job_id(project_id, 1),
            artifact_type=BYOX_REPAIR_ARTIFACT_TYPE,
            files=self._canonical_pack("pass-repair"),
        )
        seed_byox_remediation_jobs(self.database, self.jobs, project_ids=[project_id])
        self._complete_repair_review(project_id, 1, "PASS")

        result = seed_byox_remediation_jobs(
            self.database, self.jobs, project_ids=[project_id]
        )

        project = result["projects"][project_id]
        self.assertEqual("VALIDATED_PASS_NO_REPAIR", project["status"])
        self.assertFalse(project["workflow_completion_claimed"])
        self.assertEqual(0, result["created_jobs"])
        self.assertIsNone(self.jobs.get(repair_builder_job_id(project_id, 2)))

    def test_prose_or_wrong_attempt_or_unbound_review_never_triggers_repair(self) -> None:
        cases = (
            ("project-prose", None, True),
            ("project-wrong-attempt", 0, True),
            ("project-unbound", 1, False),
        )
        for project_id, validation_attempt, valid_binding in cases:
            with self.subTest(project_id=project_id):
                self._base_graph(
                    project_id,
                    "FAIL",
                    validation_attempt=validation_attempt,
                    valid_binding=valid_binding,
                )
                result = seed_byox_remediation_jobs(
                    self.database, self.jobs, project_ids=[project_id]
                )
                self.assertEqual(
                    "REMEDIATION_EVIDENCE_INVALID",
                    result["projects"][project_id]["status"],
                )
                self.assertIsNone(self.jobs.get(repair_builder_job_id(project_id, 1)))

    def test_exact_binding_full_root_projection_and_hardened_backend(self) -> None:
        project_id = "project-handler"
        self._base_graph(project_id, "REVISE")
        seed_byox_remediation_jobs(self.database, self.jobs, project_ids=[project_id])
        repair_id = repair_builder_job_id(project_id, 1)
        self.jobs.promote_eligible()
        claim = self.jobs.claim_next(
            "handler-test", 30, max_total=1, type_limits={}
        )
        assert claim is not None
        self.assertEqual(repair_id, claim.job_id)
        workspace = self.manager.allocate(repair_id, claim.attempt_count)
        handlers = JobHandlers(self.settings, self.database, self.manager)

        bad_payload = copy.deepcopy(claim.payload)
        bad_payload["inputs_from_dependencies"][0]["artifact_checksum"] = "0" * 64
        with self.assertRaisesRegex(HandlerFailure, "artifact_checksum mismatch"):
            handlers._stage_declared_inputs(
                replace(claim, payload=bad_payload), workspace
            )

        integrity, provenance = handlers._stage_declared_inputs(claim, workspace)
        self.assertEqual({"PRIOR_BUILD", "PRIOR_REVIEW"}, {item["path"] for item in integrity})
        self.assertTrue((workspace / "PRIOR_BUILD/implementation/src.py").is_file())
        self.assertEqual(
            0, (workspace / "PRIOR_BUILD/implementation/src.py").stat().st_mode & 0o222
        )
        archive_paths, selection = _byox_repair_archive_selection(
            claim, workspace, provenance
        )
        assert archive_paths is not None and selection is not None
        self.assertTrue(BYOX_CANONICAL_CHALLENGE_ROOTS <= set(archive_paths))
        self.assertIn("implementation", archive_paths)
        self.assertNotIn("PRIOR_BUILD", archive_paths)
        self.assertEqual(list(archive_paths), selection["paths"])
        _enforce_byox_remediation_backend(claim, self.settings)
        unsafe_settings = replace(
            self.settings,
            backend=replace(self.settings.backend, permission_profile="workspace-write"),
        )
        with self.assertRaisesRegex(HandlerFailure, "factory-isolated"):
            _enforce_byox_remediation_backend(claim, unsafe_settings)

    def test_legacy_specialized_profile_excludes_only_controller_root(self) -> None:
        project_id = "project-specialized"
        specialized_files = {
            ".factory-workspace": "legacy controller metadata\n",
            "README.md": "specialized challenge\n",
            "MANIFEST.yaml": "{}\n",
            "PROVENANCE.json": "{}\n",
            "REQUIREMENTS.md": "requirements\n",
            "starter/main.py": "print('starter')\n",
            "sealed/reference.py": "print('reference')\n",
            "reports/analysis.md": "specialized report\n",
        }
        self._base_graph(
            project_id,
            "FAIL",
            builder_artifact_type="bytecode_vm_challenge_pack",
            builder_files=specialized_files,
        )
        seed_byox_remediation_jobs(self.database, self.jobs, project_ids=[project_id])
        repair_id = repair_builder_job_id(project_id, 1)
        repair = self.jobs.get(repair_id)
        assert repair is not None
        self.assertEqual(
            "byox-legacy-bytecode-v1", repair["payload"]["artifact_profile"]
        )
        self.jobs.promote_eligible()
        claim = self.jobs.claim_next(
            "specialized-handler", 30, max_total=1, type_limits={}
        )
        assert claim is not None
        workspace = self.manager.allocate(repair_id, claim.attempt_count)
        _, provenance = JobHandlers(
            self.settings, self.database, self.manager
        )._stage_declared_inputs(claim, workspace)

        self.assertFalse((workspace / "PRIOR_BUILD/.factory-workspace").exists())
        self.assertTrue((workspace / "PRIOR_BUILD/reports/analysis.md").is_file())
        [prior] = [item for item in provenance if item["path"] == "PRIOR_BUILD"]
        inventory = prior["artifact_inventory"]
        self.assertEqual([".factory-workspace"], inventory["excluded_paths"])
        self.assertIn(".factory-workspace", inventory["original_paths"])
        self.assertNotIn(".factory-workspace", inventory["selected_paths"])
        self.assertIn("reports", inventory["selected_paths"])
        archive_paths, selection = _byox_repair_archive_selection(
            claim, workspace, provenance
        )
        assert archive_paths is not None and selection is not None
        self.assertEqual(inventory, selection["source_artifact_inventory"])
        projected_inventory = selection["artifact_inventory"]
        self.assertEqual(
            projected_inventory,
            _validated_repair_inventory(
                {"repair_archive_selection": selection}, claim.payload
            ),
        )
        self.assertEqual(
            set(projected_inventory["selected_paths"]), set(archive_paths)
        )
        self.assertTrue(BYOX_CANONICAL_CHALLENGE_ROOTS <= set(archive_paths))
        self.assertIn("reports", archive_paths)
        required_added = selection["required_added_inventory"]
        self.assertIn("AGENTS.md", required_added["paths"])
        self.assertIn("VALIDATION.md", required_added["paths"])

        for name, kind in projected_inventory["root_kinds"].items():
            target = workspace / name
            if name in inventory["selected_paths"]:
                source = workspace / "PRIOR_BUILD" / name
                if source.is_dir():
                    shutil.copytree(source, target)
                else:
                    shutil.copy2(source, target)
            elif kind == "directory":
                target.mkdir()
            else:
                target.write_text(f"generated {name}\n", encoding="utf-8")
        self.manager.discard_root_metadata(workspace, ".factory-workspace")
        _validate_byox_repair_outputs(
            workspace, archive_paths, selection, provenance
        )
        self.assertTrue((workspace / "AGENTS.md").is_file())
        self.assertTrue((workspace / "VALIDATION.md").is_file())

        (workspace / "UNDECLARED.txt").write_text("unexpected\n", encoding="utf-8")
        with self.assertRaisesRegex(HandlerFailure, "undeclared top-level roots"):
            _validate_byox_repair_outputs(
                workspace, archive_paths, selection, provenance
            )

    def test_unsupported_builder_artifact_type_fails_closed(self) -> None:
        project_id = "project-unsupported-profile"
        self._base_graph(
            project_id,
            "REVISE",
            builder_artifact_type="unrecognized_challenge_pack",
        )

        result = seed_byox_remediation_jobs(
            self.database, self.jobs, project_ids=[project_id]
        )

        self.assertEqual(0, result["created_jobs"])
        project = result["projects"][project_id]
        self.assertEqual("REMEDIATION_EVIDENCE_INVALID", project["status"])
        self.assertIn("unsupported BYOX remediation artifact type", project["reason"])
        self.assertIsNone(self.jobs.get(repair_builder_job_id(project_id, 1)))

    def test_cli_command_is_bounded_explicit_and_idempotent(self) -> None:
        project_id = "project-cli"
        self._base_graph(project_id, "REVISE")
        defaults = build_parser().parse_args(["seed-byox-repairs"])
        self.assertIs(cmd_seed_byox_repairs, defaults.func)
        self.assertEqual(DEFAULT_MAX_REPAIR_GENERATIONS, defaults.max_generations)
        self.assertIsNone(defaults.max_projects)

        arguments = [
            "--config",
            str(self.config_path),
            "seed-byox-repairs",
            "--project-id",
            project_id,
            "--max-generations",
            "1",
            "--max-projects",
            "1",
        ]
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            self.assertEqual(0, cmd_seed_byox_repairs(build_parser().parse_args(arguments)))
        first = json.loads(stdout.getvalue())
        self.assertEqual(1, first["created_jobs"])
        self.assertEqual(1, first["max_repair_generations"])
        self.assertEqual(1, first["max_projects"])
        self.assertEqual(1, first["promoted_ready"])

        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            self.assertEqual(0, cmd_seed_byox_repairs(build_parser().parse_args(arguments)))
        second = json.loads(stdout.getvalue())
        self.assertEqual(0, second["created_jobs"])
        self.assertEqual(
            "WAITING_FOR_REPAIR_BUILDER",
            second["projects"][project_id]["status"],
        )

    def test_scheduler_refill_advances_builder_to_exact_reviewer_after_restart(self) -> None:
        project_id = "project-scheduler"
        self._base_graph(project_id, "FAIL")

        self.assertEqual(
            0,
            asyncio.run(
                Scheduler(self.settings, self.database).run(max_jobs=0)
            ),
        )
        repair_id = repair_builder_job_id(project_id, 1)
        self.assertIsNotNone(self.jobs.get(repair_id))

        self.assertEqual(
            0,
            asyncio.run(
                Scheduler(self.settings, self.database).run(max_jobs=0)
            ),
        )
        self._complete_seeded_job(
            repair_id,
            artifact_type=BYOX_REPAIR_ARTIFACT_TYPE,
            files=self._canonical_pack("scheduler-repair"),
        )

        self.assertEqual(
            0,
            asyncio.run(
                Scheduler(self.settings, self.database).run(max_jobs=0)
            ),
        )
        reviewer_id = repair_reviewer_job_id(project_id, 1)
        reviewer = self.jobs.get(reviewer_id)
        assert reviewer is not None
        self.assertEqual({CODEX_BACKEND_GATE_JOB_ID, repair_id}, self._dependencies(reviewer_id))
        [candidate] = reviewer["payload"]["inputs_from_dependencies"]
        self.assertEqual(repair_id, candidate["job_id"])

        self.assertEqual(
            0,
            asyncio.run(
                Scheduler(self.settings, self.database).run(max_jobs=0)
            ),
        )
        with self.database.connect() as connection:
            refill_events = connection.execute(
                "SELECT COUNT(*) AS n FROM events WHERE type='BYOX_REMEDIATION_REFILLED'"
            ).fetchone()["n"]
        self.assertEqual(2, refill_events)

    def test_scheduler_refill_rotates_its_bounded_candidate_page(self) -> None:
        project_ids = ("project-page-a", "project-page-b")
        for project_id in project_ids:
            self._base_graph(project_id, "REVISE")
        scheduler = Scheduler(self.settings, self.database)

        with patch(
            "learnfactory.scheduler.AUTO_BYOX_REPAIR_REFILL_MAX_PROJECTS", 1
        ):
            first = scheduler._auto_refill_byox_remediation()
            second = scheduler._auto_refill_byox_remediation()
            repeated = scheduler._auto_refill_byox_remediation()

        assert first is not None and second is not None and repeated is not None
        self.assertEqual(1, first["active_projects"])
        self.assertEqual(1, first["created_jobs"])
        self.assertEqual(1, second["created_jobs"])
        self.assertEqual(0, repeated["created_jobs"])
        for project_id in project_ids:
            self.assertIsNotNone(self.jobs.get(repair_builder_job_id(project_id, 1)))

    def test_concurrent_reseeding_is_idempotent_and_event_failure_is_atomic(self) -> None:
        project_id = "project-concurrent"
        self._base_graph(project_id, "REVISE")
        barrier = threading.Barrier(4)
        results: list[dict[str, object]] = []
        errors: list[BaseException] = []

        def invoke() -> None:
            try:
                barrier.wait()
                results.append(
                    seed_byox_remediation_jobs(
                        self.database, self.jobs, project_ids=[project_id]
                    )
                )
            except BaseException as error:  # pragma: no cover - asserted below
                errors.append(error)

        threads = [threading.Thread(target=invoke) for _ in range(4)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=20)
        self.assertFalse(errors)
        self.assertEqual(4, len(results))
        self.assertEqual(1, sum(int(item["created_jobs"]) for item in results))
        with self.database.connect() as connection:
            count = connection.execute(
                "SELECT COUNT(*) AS n FROM jobs WHERE job_id=?",
                (repair_builder_job_id(project_id, 1),),
            ).fetchone()["n"]
        self.assertEqual(1, count)

        rollback_project = "project-rollback"
        self._base_graph(rollback_project, "FAIL")
        with patch.object(
            self.database, "emit_event", side_effect=RuntimeError("event failure")
        ):
            with self.assertRaisesRegex(RuntimeError, "event failure"):
                seed_byox_remediation_jobs(
                    self.database, self.jobs, project_ids=[rollback_project]
                )
        self.assertIsNone(
            self.jobs.get(repair_builder_job_id(rollback_project, 1))
        )

    def _dependencies(self, job_id: str) -> set[str]:
        with self.database.connect() as connection:
            return {
                row["depends_on_job_id"]
                for row in connection.execute(
                    "SELECT depends_on_job_id FROM job_dependencies WHERE job_id=?",
                    (job_id,),
                )
            }


if __name__ == "__main__":
    unittest.main()
