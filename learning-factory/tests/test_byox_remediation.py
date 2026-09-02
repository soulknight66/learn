from __future__ import annotations

import asyncio
import copy
import contextlib
import hashlib
import io
import json
import os
import shutil
import sqlite3
import tempfile
import threading
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import learnfactory.byox_remediation as remediation_module
import learnfactory.handlers as handlers_module
from learnfactory.backend_policy import with_mass_seed_backend_policy
from learnfactory.byox_jobs import (
    build_byox_job_spec,
    byox_runtime_safety_validators,
    load_active_byox_projects,
)
from learnfactory.capability_gate import (
    CODEX_BACKEND_GATE_CONTENT_VALIDATOR,
    CODEX_BACKEND_GATE_OUTPUT,
    CODEX_BACKEND_GATE_REQUIRED_PATHS_VALIDATOR,
    build_codex_backend_gate_job_spec,
)
from learnfactory.cli import build_parser, cmd_seed_byox_repairs
from learnfactory.byox_remediation import (
    BYOX_CANONICAL_CHALLENGE_ROOTS,
    BYOX_CANONICAL_DIRECTORY_ROOTS,
    BYOX_REPAIR_ARTIFACT_TYPE,
    BYOX_REPAIR_POLICY_KIND,
    BYOX_REPAIR_QUARANTINE_MAX_DEPTH,
    BYOX_REPAIR_QUARANTINE_MAX_ENTRIES,
    BYOX_REPAIR_QUARANTINE_MAX_FILE_BYTES,
    BYOX_REPAIR_QUARANTINE_MAX_FILES,
    BYOX_REPAIR_QUARANTINE_MAX_ROOTS,
    BYOX_REPAIR_QUARANTINE_MAX_TOTAL_BYTES,
    ByoxRemediationError,
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
from learnfactory.review_contract import (
    MAX_REVIEW_DOCUMENT_BYTES,
    MAX_REVIEW_EVALUATION_BYTES,
    parse_deterministic_review_evaluation,
)
from learnfactory.seeding import (
    CODEX_BACKEND_GATE_JOB_ID,
    _byox_review_job_id,
    _byox_reviewer_payload,
)
from learnfactory.specialized_byox_jobs import (
    ALLOCATOR_JOB_ID,
    ALLOCATOR_PROJECT_ID,
    BYTECODE_JOB_ID,
    BYTECODE_PROJECT_ID,
    CATALOG_SYNTHESIS_JOB_ID,
    HTTP_SERVICE_JOB_ID,
    KVSTORE_JOB_ID,
    KVSTORE_REVISION_JOB_ID,
    SpecializedByoxJobSpec,
    specialized_byox_job_specs_by_id,
    specialized_reviewer_payload,
)
from learnfactory.scheduler import Scheduler
from learnfactory.util import canonical_json, file_sha256, now, tree_sha256
from learnfactory.validation import Validator, evaluate_byox_code_presence
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
                    f'database = "{self.root / "warehouse" / "factory.db"}"',
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
        self._insert_capability_gate_fixture()

    def _catalog_project(
        self,
        project_id: str,
        *,
        title: str | None = None,
        category: str = "Systems",
        language: str | None = "Python",
        upstream_reference: str | None = None,
    ) -> None:
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
                INSERT OR IGNORE INTO build_projects(
                    project_id,source_id,slug,title,category,implementation_language,
                    upstream_reference,concepts_json,difficulty,production_relevance,
                    source_format,priority_tier,metadata_json
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    project_id,
                    "source_byox",
                    f"project-{project_id}",
                    title or f"Project {project_id}",
                    category,
                    language,
                    upstream_reference or f"https://example.invalid/{project_id}",
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
        files["starter/main.py"] = f"print({marker!r})\n"
        files["public_tests/test_main.py"] = "assert True\n"
        files["sealed/reference/main.py"] = f"print({marker!r})\n"
        files["sealed/reference_tests/test_main.py"] = "assert True\n"
        return files

    def _artifact_tree(
        self,
        job_id: str,
        files: dict[str, str],
        *,
        attempt: int = 1,
        semantic_path: str | None = None,
    ) -> Path:
        path = (
            self.settings.warehouse
            / "artifacts"
            / (semantic_path or f"codex/{job_id}")
            / job_id
            / f"attempt-{attempt:03d}"
        )
        path.mkdir(parents=True)
        for relative, content in files.items():
            target = path / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        return path

    def _materialize_builder_fixture_files(
        self,
        files: dict[str, str],
        payload: dict[str, object],
    ) -> dict[str, str]:
        """Fill controller-declared pure inputs for an otherwise terse pack."""

        materialized = dict(files)
        raw_validators = payload.get("validators")
        if not isinstance(raw_validators, list):
            return materialized
        for specification in raw_validators:
            if not isinstance(specification, dict):
                continue
            kind = specification.get("type")
            if kind in {"required_paths", "regular_files"}:
                paths = specification.get("paths", [])
                if isinstance(paths, list):
                    for path in paths:
                        if isinstance(path, str):
                            materialized.setdefault(path, f"fixture: {path}\n")
            elif kind == "json_schema":
                path = specification.get("path")
                schema = specification.get("schema")
                enum = schema.get("enum") if isinstance(schema, dict) else None
                if (
                    isinstance(path, str)
                    and isinstance(enum, list)
                    and len(enum) == 1
                ):
                    materialized[path] = canonical_json(enum[0]) + "\n"
        return materialized

    def _exact_builder_validation_fixture(
        self,
        *,
        payload: dict[str, object],
        artifact_type: str,
        artifact_path: Path,
        artifact_metadata: dict[str, object],
        artifact_id: str,
        job_id: str,
        checksum: str,
        attempt: int,
    ) -> list[tuple[str, str, dict[str, object], list[str]]] | None:
        """Replay controller validators for builder fixtures.

        Tests intentionally use real validation envelopes.  A synthetic
        ``fixture-external-validation`` PASS would turn unrelated evidence into
        publication authority and mask the exact-history fences under test.
        """

        if artifact_type not in {
            "byox-challenge-pack",
            BYOX_REPAIR_ARTIFACT_TYPE,
        }:
            return None
        raw_validators = payload.get("validators")
        if not isinstance(raw_validators, list):
            raise AssertionError("builder fixture lacks validators")
        required_file_limits = {
            str(specification["path"]): int(
                specification.get(
                    "max_bytes", remediation_module._ARTIFACT_TREE_MAX_FILE_BYTES
                )
            )
            for specification in raw_validators
            if isinstance(specification, dict)
            and specification.get("type") in {"json_schema", "json_fields"}
        }
        snapshot = remediation_module._descriptor_tree_snapshot(
            artifact_path,
            managed_artifact_root=self.settings.warehouse / "artifacts",
            required_file_limits=required_file_limits,
        )
        policy = payload.get("seed_policy")
        policy_kind = policy.get("kind") if isinstance(policy, dict) else None
        if policy_kind in {
            remediation_module.BYOX_BUILD_POLICY_KIND,
            BYOX_REPAIR_POLICY_KIND,
        }:
            profiles = remediation_module._legacy_byox_validation_profiles(
                payload,
                snapshot,
                artifact_metadata,
                {
                    "artifact_id": artifact_id,
                    "job_id": job_id,
                    "checksum": checksum,
                    "attempt_number": attempt,
                },
            )
            # Generic six-validator fixtures model the released no-code row-six
            # history. Repair fixtures have exactly one current profile.
            expected = profiles[0]
        elif policy_kind in {
            "byox_reference_build_s2",
            remediation_module.BYOX_REPAIR_S2_POLICY_KIND,
        }:
            expected = tuple(
                remediation_module._expected_s2_builder_validations(
                    payload, snapshot, artifact_metadata
                )
            )
        else:
            raise AssertionError("builder fixture has no admitted policy")
        return [
            (
                f"validation_{job_id}_fixture_{attempt}_{index:02d}",
                name,
                evidence,
                claims,
            )
            for index, (name, evidence, claims) in enumerate(expected, start=1)
        ]

    def _insert_finished_job(
        self,
        job_id: str,
        payload: dict[str, object],
        *,
        artifact_type: str,
        files: dict[str, str],
        metadata: dict[str, object] | None = None,
        dependencies: tuple[str, ...] = (),
        job_type: str = "codex_task",
        worker_type: str = "reference_builder",
        priority: float = 50.0,
        score_components: dict[str, float] | None = None,
        max_attempts: int = 2,
        model: str | None = "gpt-5.6-sol",
        reasoning_effort: str | None = "ultra",
        attempt: int = 1,
        semantic_path: str | None = None,
    ) -> dict[str, object]:
        semantic_path = semantic_path or str(
            payload.get("artifact_path", f"codex/{job_id}")
        )
        if artifact_type in {"byox-challenge-pack", BYOX_REPAIR_ARTIFACT_TYPE}:
            files = self._materialize_builder_fixture_files(files, payload)
        artifact_path = self._artifact_tree(
            job_id,
            files,
            attempt=attempt,
            semantic_path=semantic_path,
        )
        checksum = tree_sha256(artifact_path)
        artifact_id = f"artifact_{job_id.removeprefix('job_')}"
        timestamp = now()
        workspace = (
            self.settings.warehouse
            / "workspaces"
            / job_id
            / f"attempt-{attempt:03d}"
        )
        workspace.mkdir(parents=True, exist_ok=True)
        labels = (
            ("GENERATED", "PARTIAL")
            if artifact_type in {"byox-challenge-pack", BYOX_REPAIR_ARTIFACT_TYPE}
            else ("GENERATED",)
        )
        metadata_base = dict(metadata or {})
        validation_records = self._exact_builder_validation_fixture(
            payload=payload,
            artifact_type=artifact_type,
            artifact_path=artifact_path,
            artifact_metadata=metadata_base,
            artifact_id=artifact_id,
            job_id=job_id,
            checksum=checksum,
            attempt=attempt,
        )
        if validation_records is None:
            claims = ["PARTIAL"] if "PARTIAL" in labels else []
            validation_records = [
                (
                    f"validation_{job_id}_fixture_{attempt}",
                    "fixture-external-validation",
                    {"fixture": "external-pass"},
                    claims,
                )
            ]
        artifact_metadata = {
            **metadata_base,
            "job_id": job_id,
            "attempt": attempt,
            "validated_tree_sha256": checksum,
            "validation_labels": list(labels),
            "validation_evidence": [
                {
                    "validator": validator,
                    "status": "PASS",
                    "evidence": evidence,
                }
                for _validation_id, validator, evidence, _claims in validation_records
            ],
        }
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
                    job_type,
                    worker_type,
                    "DISCOVERED",
                    priority,
                    canonical_json(score_components or {}),
                    canonical_json(payload),
                    0,
                    max_attempts,
                    timestamp,
                    None,
                    None,
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
                "UPDATE jobs SET state='READY' WHERE job_id=?",
                (job_id,),
            )
            connection.execute(
                """
                UPDATE jobs SET state='CLAIMED',owner='test-owner',
                    lease_token='test-lease',lease_expires_at=?,
                    attempt_count=?,started_at=?,heartbeat_at=?,workspace=?
                WHERE job_id=?
                """,
                (
                    timestamp + 60,
                    attempt,
                    timestamp,
                    timestamp,
                    str(workspace),
                    job_id,
                ),
            )
            connection.execute(
                "UPDATE jobs SET state='RUNNING' WHERE job_id=?",
                (job_id,),
            )
            for validation_id, validator, evidence, claims in validation_records:
                connection.execute(
                    """
                    INSERT INTO validations(
                        validation_id,job_id,validator,status,evidence_json,
                        started_at,finished_at,attempt_number,claims_json
                    ) VALUES (?,?,?,'PASS',?,?,?,?,?)
                    """,
                    (
                        validation_id,
                        job_id,
                        validator,
                        canonical_json(evidence),
                        timestamp,
                        timestamp,
                        attempt,
                        canonical_json(claims),
                    ),
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
                    canonical_json(artifact_metadata),
                    timestamp,
                    "GENERATED",
                    attempt,
                ),
            )
            connection.execute(
                "UPDATE artifacts SET validation_status=? WHERE artifact_id=?",
                ("+".join(labels), artifact_id),
            )
            support = [
                {
                    "validation_id": validation_id,
                    "validator": validator,
                    "claims": claims,
                }
                for validation_id, validator, _evidence, claims in validation_records
            ]
            for label in labels:
                label_support = [
                    item
                    for item in support
                    if label == "GENERATED" or label in item["claims"]
                ]
                connection.execute(
                    """
                    INSERT INTO artifact_validation_labels(
                        artifact_id,label,evidence_json,created_at
                    ) VALUES (?,?,?,?)
                    """,
                    (
                        artifact_id,
                        label,
                        canonical_json(
                            {
                                "job_id": job_id,
                                "attempt": attempt,
                                "support": label_support,
                            }
                        ),
                        timestamp,
                    ),
                )
            connection.execute(
                """
                UPDATE jobs SET state='SUCCEEDED',owner=NULL,lease_token=NULL,
                    lease_expires_at=NULL,finished_at=?,heartbeat_at=? WHERE job_id=?
                """,
                (timestamp, timestamp, job_id),
            )
        return {
            "job_id": job_id,
            "artifact_id": artifact_id,
            "artifact_type": artifact_type,
            "artifact_checksum": checksum,
            "checksum_algorithm": "tree-sha256-v2",
            "artifact_attempt": attempt,
        }

    def _insert_capability_gate_fixture(self) -> None:
        spec = build_codex_backend_gate_job_spec()
        binding = self._insert_finished_job(
            spec.job_id,
            copy.deepcopy(spec.payload),
            artifact_type="backend-capability-gate",
            files={"BACKEND_READY.txt": CODEX_BACKEND_GATE_OUTPUT},
            worker_type=spec.worker_type,
            priority=spec.priority,
            score_components=spec.score_components,
            max_attempts=spec.max_attempts,
            model=spec.model,
            reasoning_effort=spec.reasoning_effort,
        )
        records = (
            (
                f"validation_{spec.job_id}_1",
                CODEX_BACKEND_GATE_REQUIRED_PATHS_VALIDATOR,
                {"checked": ["BACKEND_READY.txt"], "missing": []},
            ),
            (
                f"validation_{spec.job_id}_2",
                CODEX_BACKEND_GATE_CONTENT_VALIDATOR,
                {"checked": ["BACKEND_READY.txt"], "mismatches": []},
            ),
        )
        with self.database.transaction(immediate=True) as connection:
            job = connection.execute(
                "SELECT finished_at FROM jobs WHERE job_id=?", (spec.job_id,)
            ).fetchone()
            artifact = connection.execute(
                "SELECT checksum FROM artifacts WHERE artifact_id=?",
                (binding["artifact_id"],),
            ).fetchone()
            assert job is not None and artifact is not None
            timestamp = job["finished_at"]
            connection.execute(
                "DELETE FROM validations WHERE job_id=?", (spec.job_id,)
            )
            for validation_id, validator, evidence in records:
                connection.execute(
                    """
                    INSERT INTO validations(
                        validation_id,job_id,validator,status,evidence_json,
                        started_at,finished_at,attempt_number,claims_json
                    ) VALUES (?,?,?,'PASS',?,?,?,?, '[]')
                    """,
                    (
                        validation_id,
                        spec.job_id,
                        validator,
                        canonical_json(evidence),
                        timestamp,
                        timestamp,
                        1,
                    ),
                )
            validation_evidence = [
                {
                    "validator": validator,
                    "status": "PASS",
                    "evidence": evidence,
                }
                for _, validator, evidence in records
            ]
            metadata = {
                "job_id": spec.job_id,
                "attempt": 1,
                "classification": "deterministic control-plane capability probe",
                "policy_version": 1,
                "codex_api_transport_required": True,
                "external_resource_network_allowed": False,
                "validated_tree_sha256": artifact["checksum"],
                "validation_labels": ["GENERATED"],
                "validation_evidence": validation_evidence,
            }
            connection.execute(
                "UPDATE artifacts SET metadata_json=? WHERE artifact_id=?",
                (canonical_json(metadata), binding["artifact_id"]),
            )
            support = [
                {
                    "validation_id": validation_id,
                    "validator": validator,
                    "claims": [],
                }
                for validation_id, validator, _ in records
            ]
            connection.execute(
                """
                UPDATE artifact_validation_labels
                SET evidence_json=?,created_at=?
                WHERE artifact_id=? AND label='GENERATED'
                """,
                (
                    canonical_json(
                        {"job_id": spec.job_id, "attempt": 1, "support": support}
                    ),
                    timestamp,
                    binding["artifact_id"],
                ),
            )

    def _complete_seeded_job(
        self,
        job_id: str,
        *,
        artifact_type: str,
        files: dict[str, str],
        metadata: dict[str, object] | None = None,
    ) -> dict[str, object]:
        seeded = self.jobs.get(job_id)
        assert seeded is not None
        if artifact_type in {"byox-challenge-pack", BYOX_REPAIR_ARTIFACT_TYPE}:
            files = self._materialize_builder_fixture_files(files, seeded["payload"])
        semantic_path = str(
            seeded["payload"].get("artifact_path", f"codex/{job_id}")
        )
        artifact_path = self._artifact_tree(
            job_id, files, semantic_path=semantic_path
        )
        checksum = tree_sha256(artifact_path)
        if artifact_type == BYOX_REPAIR_ARTIFACT_TYPE:
            metadata = self._repair_artifact_metadata(
                job_id,
                files,
                artifact_checksum=checksum,
                artifact_path=artifact_path,
            )
        artifact_id = f"artifact_{job_id.removeprefix('job_')}"
        timestamp = now()
        workspace = self.settings.warehouse / "workspaces" / job_id / "attempt-001"
        workspace.mkdir(parents=True, exist_ok=True)
        labels = (
            ("GENERATED", "PARTIAL")
            if artifact_type in {"byox-challenge-pack", BYOX_REPAIR_ARTIFACT_TYPE}
            else ("GENERATED",)
        )
        metadata_base = dict(metadata or {})
        validation_records = self._exact_builder_validation_fixture(
            payload=seeded["payload"],
            artifact_type=artifact_type,
            artifact_path=artifact_path,
            artifact_metadata=metadata_base,
            artifact_id=artifact_id,
            job_id=job_id,
            checksum=checksum,
            attempt=1,
        )
        if validation_records is None:
            claims = ["PARTIAL"] if "PARTIAL" in labels else []
            validation_records = [
                (
                    f"validation_{job_id}_fixture_1",
                    "fixture-external-validation",
                    {"fixture": "external-pass"},
                    claims,
                )
            ]
        artifact_metadata = {
            **metadata_base,
            "job_id": job_id,
            "attempt": 1,
            "validated_tree_sha256": checksum,
            "validation_labels": list(labels),
            "validation_evidence": [
                {
                    "validator": validator,
                    "status": "PASS",
                    "evidence": evidence,
                }
                for _validation_id, validator, evidence, _claims in validation_records
            ],
        }
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
                    lease_expires_at=?,attempt_count=1,started_at=?,heartbeat_at=?,workspace=?
                WHERE job_id=? AND state='READY'
                """,
                (timestamp + 60, timestamp, timestamp, str(workspace), job_id),
            )
            connection.execute(
                "UPDATE jobs SET state='RUNNING' WHERE job_id=?", (job_id,)
            )
            for validation_id, validator, evidence, claims in validation_records:
                connection.execute(
                    """
                    INSERT INTO validations(
                        validation_id,job_id,validator,status,evidence_json,
                        started_at,finished_at,attempt_number,claims_json
                    ) VALUES (?,?,?,'PASS',?,?,?,?,?)
                    """,
                    (
                        validation_id,
                        job_id,
                        validator,
                        canonical_json(evidence),
                        timestamp,
                        timestamp,
                        1,
                        canonical_json(claims),
                    ),
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
                    canonical_json(artifact_metadata),
                    timestamp,
                    "GENERATED",
                    1,
                ),
            )
            connection.execute(
                "UPDATE artifacts SET validation_status=? WHERE artifact_id=?",
                ("+".join(labels), artifact_id),
            )
            support = [
                {
                    "validation_id": validation_id,
                    "validator": validator,
                    "claims": claims,
                }
                for validation_id, validator, _evidence, claims in validation_records
            ]
            for label in labels:
                label_support = [
                    item
                    for item in support
                    if label == "GENERATED" or label in item["claims"]
                ]
                connection.execute(
                    """
                    INSERT INTO artifact_validation_labels(
                        artifact_id,label,evidence_json,created_at
                    ) VALUES (?,?,?,?)
                    """,
                    (
                        artifact_id,
                        label,
                        canonical_json(
                            {
                                "job_id": job_id,
                                "attempt": 1,
                                "support": label_support,
                            }
                        ),
                        timestamp,
                    ),
                )
            connection.execute(
                """
                UPDATE jobs SET state='SUCCEEDED',owner=NULL,lease_token=NULL,
                    lease_expires_at=NULL,finished_at=?,heartbeat_at=? WHERE job_id=?
                """,
                (timestamp, timestamp, job_id),
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
        self,
        job_id: str,
        files: dict[str, str],
        *,
        artifact_checksum: str,
        artifact_path: Path,
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
        quarantine_body = {
            "schema_version": 1,
            "policy": remediation_module.BYOX_REPAIR_QUARANTINE_POLICY,
            "classification": "excluded-non-artifact-quarantine",
            "excluded_from_archive_projection": True,
            "evidence_scope": "capture-time-retired-source-only",
            "limits": {
                "max_roots": BYOX_REPAIR_QUARANTINE_MAX_ROOTS,
                "max_entries": BYOX_REPAIR_QUARANTINE_MAX_ENTRIES,
                "max_files": BYOX_REPAIR_QUARANTINE_MAX_FILES,
                "max_total_bytes": BYOX_REPAIR_QUARANTINE_MAX_TOTAL_BYTES,
                "max_file_bytes": BYOX_REPAIR_QUARANTINE_MAX_FILE_BYTES,
                "max_depth": BYOX_REPAIR_QUARANTINE_MAX_DEPTH,
            },
            "roots": [],
            "entries": [],
            "summary": {
                "roots": 0,
                "entries": 0,
                "files": 0,
                "directories": 0,
                "total_bytes": 0,
                "max_depth": 0,
            },
        }
        quarantine = {
            **quarantine_body,
            "manifest_sha256": hashlib.sha256(
                canonical_json(quarantine_body).encode("utf-8")
            ).hexdigest(),
        }
        output_snapshot = remediation_module._descriptor_tree_snapshot(
            artifact_path,
            managed_artifact_root=self.settings.warehouse / "artifacts",
        )
        with self.database.connect() as connection:
            staged_inputs, validation_checksum = (
                remediation_module._expected_repair_staged_provenance(
                    builder_payload=payload,
                    source_inventory=source_inventory,
                    output_snapshot=output_snapshot,
                    connection=connection,
                    managed_artifact_root=self.settings.warehouse / "artifacts",
                    observed_staged=[],
                )
            )
        assert validation_checksum is not None
        staged_bindings = sorted(
            [
                {
                    key: item[key]
                    for key in ("path", "kind", "checksum_algorithm", "checksum")
                }
                for item in staged_inputs
            ],
            key=lambda item: item["path"],
        )
        cutover_body = {
            "schema_version": 1,
            "policy": remediation_module.BYOX_REPAIR_CUTOVER_POLICY,
            "classification": "factory-authoritative-validation-snapshot",
            "source_disposition": "retired-and-discarded",
            "quarantine_evidence_scope": "capture-time-retired-source-only",
            "quarantine_manifest_sha256": quarantine["manifest_sha256"],
            "archive_paths": projected_paths,
            "archive_paths_sha256": self._list_sha256(projected_paths),
            "snapshot_roots": sorted(
                set(projected_paths) | {"PRIOR_BUILD", "PRIOR_REVIEW"}
            ),
            "staged_inputs": staged_bindings,
            "limits": {
                "max_entries": remediation_module.BYOX_REPAIR_CUTOVER_MAX_ENTRIES,
                "max_total_bytes": remediation_module.BYOX_REPAIR_CUTOVER_MAX_TOTAL_BYTES,
                "max_file_bytes": remediation_module.BYOX_REPAIR_CUTOVER_MAX_FILE_BYTES,
                "max_depth": remediation_module.BYOX_REPAIR_CUTOVER_MAX_DEPTH,
            },
            "validation_snapshot_checksum_algorithm": "tree-sha256-v2",
            "validation_snapshot_checksum": validation_checksum,
            "selected_output_checksum_algorithm": "tree-sha256-v2",
            "selected_output_checksum": artifact_checksum,
        }
        cutover = {
            **cutover_body,
            "manifest_sha256": hashlib.sha256(
                canonical_json(cutover_body).encode("utf-8")
            ).hexdigest(),
        }
        selection = {
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
                "quarantined_outputs": quarantine,
                "authoritative_cutover": cutover,
        }
        return {
            "repair_archive_selection": selection,
            "byox_validation_cutover": cutover,
            "staged_inputs": staged_inputs,
            "validation_workspace_tree_sha256": validation_checksum,
            "archive_projection": {
                "schema_version": 1,
                "mode": "declared-worker-outputs",
                "paths": projected_paths,
                "staged_inputs_excluded": True,
                "source_workspace_checksum_algorithm": "tree-sha256-v2",
                "source_workspace_checksum": validation_checksum,
                "projected_tree_checksum_algorithm": "tree-sha256-v2",
                "projected_tree_checksum": artifact_checksum,
            },
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

    def _publication_counts(self) -> tuple[int, int, int]:
        with self.database.connect() as connection:
            return tuple(
                int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
                for table in ("jobs", "job_dependencies", "events")
            )

    def _assert_invalid_without_publication(
        self,
        project_id: str,
        before: tuple[int, int, int],
    ) -> None:
        result = seed_byox_remediation_jobs(
            self.database,
            self.jobs,
            warehouse=self.settings.warehouse,
            project_ids=[project_id],
        )
        self.assertEqual(0, result["created_jobs"])
        self.assertEqual(
            "REMEDIATION_EVIDENCE_INVALID",
            result["projects"][project_id]["status"],
        )
        self.assertEqual(before, self._publication_counts())
        self.assertIsNone(self.jobs.get(repair_builder_job_id(project_id, 1)))

    def _insert_review_validations(
        self, review_job_id: str, verdict: str, *, attempt: int = 1
    ) -> None:
        timestamp = now()
        with self.database.connect() as connection:
            artifact = connection.execute(
                """
                SELECT path FROM artifacts
                WHERE job_id=? ORDER BY attempt_number DESC LIMIT 1
                """,
                (review_job_id,),
            ).fetchone()
        assert artifact is not None
        evaluation = parse_deterministic_review_evaluation(
            (Path(str(artifact["path"])) / "EVALUATION.json").read_bytes()
        )
        self.assertEqual(verdict, evaluation.verdict)
        records = (
            (
                "byox-independent-review-files",
                {
                    "missing": [],
                    "checked": [
                        "EVALUATION.json",
                        "REVIEW.md",
                        "VALIDATION.md",
                    ],
                },
            ),
            (
                "byox-independent-review-schema",
                {"error_count": 0, "errors": []},
            ),
            (
                "byox-independent-review-verdict",
                evaluation.validation_evidence(),
            ),
            (
                "byox-independent-review-acceptance",
                {
                    "mode": "closed",
                    "acceptance_authority": "orchestrator",
                    "workflow_accepted": False,
                    "reason": "no independent acceptance command configured",
                },
            ),
            (
                "declared-inputs-remained-immutable",
                {"checked": ["CANDIDATE"], "mismatches": []},
            ),
        )
        with self.database.transaction(immediate=True) as connection:
            job = connection.execute(
                "SELECT finished_at FROM jobs WHERE job_id=?", (review_job_id,)
            ).fetchone()
            artifact_row = connection.execute(
                """
                SELECT artifact_id,checksum,metadata_json FROM artifacts
                WHERE job_id=? ORDER BY attempt_number DESC LIMIT 1
                """,
                (review_job_id,),
            ).fetchone()
            assert job is not None and artifact_row is not None
            timestamp = job["finished_at"]
            connection.execute(
                "DELETE FROM validations WHERE job_id=?", (review_job_id,)
            )
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
            validation_evidence = [
                {"validator": validator, "status": "PASS", "evidence": evidence}
                for validator, evidence in records
            ]
            metadata = json.loads(artifact_row["metadata_json"])
            metadata.update(
                {
                    "job_id": review_job_id,
                    "attempt": attempt,
                    "validated_tree_sha256": artifact_row["checksum"],
                    "validation_labels": ["GENERATED"],
                    "validation_evidence": validation_evidence,
                }
            )
            connection.execute(
                "UPDATE artifacts SET metadata_json=? WHERE artifact_id=?",
                (canonical_json(metadata), artifact_row["artifact_id"]),
            )
            support = [
                {
                    "validation_id": f"validation_{review_job_id}_{index}_{attempt}",
                    "validator": validator,
                    "claims": [],
                }
                for index, (validator, _) in enumerate(records, start=1)
            ]
            connection.execute(
                """
                UPDATE artifact_validation_labels
                SET evidence_json=?,created_at=?
                WHERE artifact_id=? AND label='GENERATED'
                """,
                (
                    canonical_json(
                        {
                            "job_id": review_job_id,
                            "attempt": attempt,
                            "support": support,
                        }
                    ),
                    timestamp,
                    artifact_row["artifact_id"],
                ),
            )

    def _review_metadata(
        self,
        builder: dict[str, object],
        review_payload: dict[str, object],
    ) -> dict[str, object]:
        declarations = review_payload["inputs_from_dependencies"]
        assert isinstance(declarations, list)
        with self.database.connect() as connection:
            artifact = connection.execute(
                "SELECT path,metadata_json FROM artifacts WHERE artifact_id=?",
                (builder["artifact_id"],),
            ).fetchone()
        assert artifact is not None
        root = Path(str(artifact["path"]))
        artifact_metadata = json.loads(str(artifact["metadata_json"]))
        snapshot = remediation_module._descriptor_tree_snapshot(
            root,
            managed_artifact_root=self.settings.warehouse / "artifacts",
        )
        staged: list[dict[str, object]] = []
        for declaration in declarations:
            assert isinstance(declaration, dict)
            artifact_root = declaration.get("artifact_root") is True
            subpath = "." if artifact_root else str(declaration["subpath"])
            own = remediation_module._snapshot_staged_record(
                snapshot,
                destination=str(declaration["destination"]),
                subpath=subpath,
            )
            record = {
                **own,
                "origin": "dependency-artifact",
                "job_id": builder["job_id"],
                "artifact_id": builder["artifact_id"],
                "artifact_type": builder["artifact_type"],
                "artifact_checksum": builder["artifact_checksum"],
                "artifact_checksum_algorithm": builder["checksum_algorithm"],
                "artifact_attempt": builder["artifact_attempt"],
                "artifact_subpath": subpath,
            }
            if artifact_root:
                record["artifact_inventory"] = artifact_metadata[
                    "repair_archive_selection"
                ]["artifact_inventory"]
            staged.append(record)
        return {
            "staged_inputs": staged
        }

    def _insert_specialized_fixture_builder(
        self,
        spec: SpecializedByoxJobSpec,
        specs: dict[str, SpecializedByoxJobSpec],
        *,
        files: dict[str, str] | None = None,
        attempt: int = 1,
    ) -> dict[str, object]:
        """Materialize one exact released specialized row and its real parents."""

        for dependency in spec.dependencies:
            if self.jobs.get(dependency) is not None:
                continue
            if dependency == CATALOG_SYNTHESIS_JOB_ID:
                self._insert_finished_job(
                    dependency,
                    {"fixture": "catalog synthesis"},
                    artifact_type="catalog-synthesis",
                    files={"CATALOG.md": "fixture catalog\n"},
                    worker_type="synthesizer",
                    model=None,
                    reasoning_effort=None,
                )
                continue
            prerequisite = specs.get(dependency)
            assert prerequisite is not None
            self._insert_specialized_fixture_builder(
                prerequisite,
                specs,
            )
        # KV v1 predates external validation and is retained only as dependency
        # history. It is deliberately never an authorized remediation source.
        if spec.job_id == KVSTORE_JOB_ID:
            return self._insert_finished_job(
                spec.job_id,
                copy.deepcopy(spec.payload),
                artifact_type=spec.artifact_type,
                files=files or self._canonical_pack(f"specialized-{spec.job_id}"),
                dependencies=spec.dependencies,
                job_type=spec.job_type,
                worker_type=spec.worker_type,
                priority=spec.priority,
                score_components=spec.score_components,
                max_attempts=spec.max_attempts,
                model=spec.model,
                reasoning_effort=spec.reasoning_effort,
                attempt=attempt,
                semantic_path=spec.semantic_path,
            )
        return self._insert_validated_specialized_fixture(
            spec,
            files=files,
            attempt=attempt,
        )

    def _insert_validated_specialized_fixture(
        self,
        spec: SpecializedByoxJobSpec,
        *,
        files: dict[str, str] | None,
        attempt: int,
    ) -> dict[str, object]:
        """Run a released deterministic generator and its real validators."""

        if spec.job_type == "project_vertical_slice":
            from learnfactory.vertical_slices import generate_project_slice as generator
        elif spec.job_type == "http_service_vertical_slice":
            from learnfactory.http_service_slice import generate_http_service_slice as generator
        elif spec.job_type == "allocator_vertical_slice":
            from learnfactory.allocator_slice import generate_allocator_slice as generator
        elif spec.job_type == "bytecode_vertical_slice":
            from learnfactory.bytecode_slice import generate_bytecode_slice as generator
        else:  # pragma: no cover - the released specialized mapping is exhaustive.
            raise AssertionError(spec.job_type)

        timestamp = now()
        workspace = (
            self.settings.warehouse
            / "workspaces"
            / spec.job_id
            / f"attempt-{attempt:03d}"
        )
        workspace.mkdir(parents=True, exist_ok=True)
        artifact_path = (
            self.settings.warehouse
            / "artifacts"
            / spec.semantic_path
            / spec.job_id
            / f"attempt-{attempt:03d}"
        )
        artifact_path.mkdir(parents=True)
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                """
                INSERT INTO jobs(
                    job_id,type,worker_type,state,priority,score_components_json,
                    payload_json,attempt_count,max_attempts,created_at,started_at,
                    heartbeat_at,workspace,owner,lease_token,lease_expires_at,
                    model,reasoning_effort
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    spec.job_id,
                    spec.job_type,
                    spec.worker_type,
                    "DISCOVERED",
                    spec.priority,
                    canonical_json(spec.score_components),
                    canonical_json(spec.payload),
                    attempt,
                    spec.max_attempts,
                    timestamp,
                    timestamp,
                    timestamp,
                    str(workspace),
                    "test-owner",
                    "test-lease",
                    timestamp + 60,
                    spec.model,
                    spec.reasoning_effort,
                ),
            )
            for dependency in spec.dependencies:
                connection.execute(
                    """
                    INSERT INTO job_dependencies(job_id,depends_on_job_id)
                    VALUES (?,?)
                    """,
                    (spec.job_id, dependency),
                )
            # Dependency definitions are frozen after discovery.  Build the
            # historical graph first, then replay its legal runtime state
            # transitions instead of bypassing the scheduler's edge guard.
            connection.execute(
                "UPDATE jobs SET state='READY' WHERE job_id=?",
                (spec.job_id,),
            )
            connection.execute(
                "UPDATE jobs SET state='CLAIMED' WHERE job_id=?",
                (spec.job_id,),
            )
            connection.execute(
                "UPDATE jobs SET state='RUNNING' WHERE job_id=?",
                (spec.job_id,),
            )

        generated = generator(artifact_path, copy.deepcopy(spec.payload), self.database)
        self.assertEqual(spec.artifact_type, generated.artifact_type)
        if files:
            for relative, content in files.items():
                target = artifact_path / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
        log_dir = (
            self.settings.warehouse
            / "logs"
            / spec.job_id
            / f"attempt-{attempt:03d}"
        )
        results = Validator(self.database).run(
            spec.job_id,
            artifact_path,
            generated.validators,
            log_dir,
            attempt_number=attempt,
        )
        self.assertTrue(
            all(result.passed for result in results),
            [(result.name, result.status, result.evidence) for result in results],
        )
        if spec.job_id == KVSTORE_REVISION_JOB_ID:
            with self.database.transaction(immediate=True) as connection:
                rows = connection.execute(
                    """
                    SELECT validation_id,evidence_json FROM validations
                    WHERE job_id=? AND command_json IS NOT NULL
                    """,
                    (spec.job_id,),
                ).fetchall()
                for row in rows:
                    evidence = json.loads(row["evidence_json"])
                    evidence.pop("stdout_bytes", None)
                    evidence.pop("stderr_bytes", None)
                    evidence.pop("retained_log_limit_bytes", None)
                    connection.execute(
                        "UPDATE validations SET evidence_json=? WHERE validation_id=?",
                        (canonical_json(evidence), row["validation_id"]),
                    )

        checksum = tree_sha256(artifact_path)
        artifact_id = f"artifact_{spec.job_id.removeprefix('job_')}"
        finished = now()
        with self.database.transaction(immediate=True) as connection:
            validations = connection.execute(
                """
                SELECT validation_id,validator,evidence_json,claims_json
                FROM validations WHERE job_id=? AND attempt_number=?
                ORDER BY started_at,validation_id
                """,
                (spec.job_id, attempt),
            ).fetchall()
            support = [
                {
                    "validation_id": row["validation_id"],
                    "validator": row["validator"],
                    "claims": json.loads(row["claims_json"]),
                }
                for row in validations
            ]
            evidence = [
                {
                    "validator": row["validator"],
                    "status": "PASS",
                    "evidence": json.loads(row["evidence_json"]),
                }
                for row in validations
            ]
            claimed = {
                claim for item in support for claim in item["claims"]
            }
            labels = tuple(
                label
                for label in remediation_module._ARTIFACT_STATUS_ORDER
                if label == "GENERATED" or label in claimed
            )
            metadata = {
                **dict(generated.metadata),
                "job_id": spec.job_id,
                "attempt": attempt,
                "validated_tree_sha256": checksum,
                "validation_labels": list(labels),
                "validation_evidence": evidence,
            }
            connection.execute(
                """
                INSERT INTO artifacts(
                    artifact_id,job_id,type,path,checksum,metadata_json,created_at,
                    validation_status,attempt_number,checksum_algorithm,integrity_status
                ) VALUES (?,?,?,?,?,?,?,?,?,'tree-sha256-v2','VERIFIED_V2')
                """,
                (
                    artifact_id,
                    spec.job_id,
                    spec.artifact_type,
                    str(artifact_path),
                    checksum,
                    canonical_json(metadata),
                    finished,
                    "+".join(labels),
                    attempt,
                ),
            )
            for label in labels:
                label_support = [
                    item
                    for item in support
                    if label == "GENERATED" or label in item["claims"]
                ]
                connection.execute(
                    """
                    INSERT INTO artifact_validation_labels(
                        artifact_id,label,evidence_json,created_at
                    ) VALUES (?,?,?,?)
                    """,
                    (
                        artifact_id,
                        label,
                        canonical_json(
                            {
                                "job_id": spec.job_id,
                                "attempt": attempt,
                                "support": label_support,
                            }
                        ),
                        finished,
                    ),
                )
            connection.execute(
                """
                UPDATE jobs SET state='SUCCEEDED',owner=NULL,lease_token=NULL,
                    lease_expires_at=NULL,heartbeat_at=?,finished_at=?
                WHERE job_id=?
                """,
                (finished, finished, spec.job_id),
            )
        return {
            "job_id": spec.job_id,
            "artifact_id": artifact_id,
            "artifact_type": spec.artifact_type,
            "artifact_checksum": checksum,
            "checksum_algorithm": "tree-sha256-v2",
            "artifact_attempt": attempt,
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
        specialized_builder_job_id: str | None = None,
        builder_attempt: int = 1,
    ) -> tuple[str, str, dict[str, object], dict[str, object]]:
        specialized_job_types = {
            "bytecode_vm_challenge_pack": "bytecode_vertical_slice",
            "project_challenge_pack": "project_vertical_slice",
            "allocator_challenge_pack": "allocator_vertical_slice",
            "http_service_challenge_pack": "http_service_vertical_slice",
        }
        builder_job_type = specialized_job_types.get(
            builder_artifact_type, "codex_task"
        )
        specialized_builder_ids = {
            "bytecode_vm_challenge_pack": "job_project_bytecode_vertical_v1",
            "allocator_challenge_pack": "job_project_allocator_vertical_v1",
            "project_challenge_pack": "job_project_kvstore_vertical",
            "http_service_challenge_pack": "job_project_http_service_vertical_v1",
        }
        builder_id = (
            specialized_builder_job_id
            or specialized_builder_ids.get(builder_artifact_type)
        )
        category = {
            "project_challenge_pack": "Database",
            "http_service_challenge_pack": "Web Server",
        }.get(builder_artifact_type, "Systems")
        title = (
            "A Simple Web Server"
            if builder_artifact_type == "http_service_challenge_pack"
            else None
        )
        self._catalog_project(project_id, category=category, title=title)
        snapshots = load_active_byox_projects(self.database)
        snapshot = {item.project_id: item for item in snapshots}[project_id]
        template = build_byox_job_spec(snapshot)
        if builder_job_type == "codex_task":
            builder_id = template.job_id
            builder_payload = copy.deepcopy(template.payload)
            # Model the released six-validator payload. The handler of that
            # release could append the code gate, but this fixture deliberately
            # exercises its admitted six-row no-code validation history.
            builder_payload["validators"] = [
                item
                for item in builder_payload["validators"]
                if item.get("name")
                != "byox-authoritative-code-bearing-tree"
            ]
            builder_payload["artifact_type"] = builder_artifact_type
            review_builder_payload = builder_payload
            builder = self._insert_finished_job(
                builder_id,
                builder_payload,
                artifact_type=builder_artifact_type,
                files=builder_files or self._canonical_pack("base"),
                dependencies=(CODEX_BACKEND_GATE_JOB_ID,),
                job_type=builder_job_type,
                priority=template.priority,
                score_components=template.score_components,
                max_attempts=template.max_attempts,
                model=template.model,
                reasoning_effort=template.reasoning_effort,
            )
        else:
            assert builder_id is not None
            specialized_specs = specialized_byox_job_specs_by_id(snapshots)
            specialized_spec = specialized_specs.get(builder_id)
            if specialized_spec is None:
                builder_payload = copy.deepcopy(template.payload)
                builder_payload.pop("seed_policy", None)
                builder_payload["artifact_type"] = builder_artifact_type
                builder_payload["job_id"] = builder_id
                review_builder_payload = builder_payload
                builder = self._insert_finished_job(
                    builder_id,
                    builder_payload,
                    artifact_type=builder_artifact_type,
                    files=builder_files or self._canonical_pack("base"),
                    dependencies=(CODEX_BACKEND_GATE_JOB_ID,),
                    job_type=builder_job_type,
                    priority=template.priority,
                    score_components=template.score_components,
                    max_attempts=template.max_attempts,
                    model=template.model,
                    reasoning_effort=template.reasoning_effort,
                )
            else:
                builder_payload = copy.deepcopy(specialized_spec.payload)
                review_builder_payload = specialized_reviewer_payload(
                    specialized_spec
                )
                builder = self._insert_specialized_fixture_builder(
                    specialized_spec,
                    specialized_specs,
                    files=builder_files,
                    attempt=builder_attempt,
                )
        review_policy_version = 1
        review_id = _byox_review_job_id(
            project_id, policy_version=review_policy_version
        )
        review_payload = _byox_reviewer_payload(
            project_id=project_id,
            builder_job_id=builder_id,
            builder_payload=review_builder_payload,
            specialized=builder_artifact_type != "byox-challenge-pack",
            policy_version=review_policy_version,
        )
        metadata = self._review_metadata(builder, review_payload)
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
            priority=round(max(35.0, min(94.0, template.priority - 1)), 4),
            score_components=template.score_components,
        )
        if validation_attempt is not None:
            self._insert_review_validations(
                review_id, verdict, attempt=validation_attempt
            )
        return builder_id, review_id, builder, review

    def _rewrite_generic_base_contract(
        self,
        *,
        project_id: str,
        builder_id: str,
        review_id: str,
        builder: dict[str, object],
        review: dict[str, object],
        builder_payload: dict[str, object],
    ) -> None:
        """Coherently rewrite both sides of a base review for adversarial tests."""

        reviewer_payload = _byox_reviewer_payload(
            project_id=project_id,
            builder_job_id=builder_id,
            builder_payload=builder_payload,
            specialized=False,
            policy_version=1,
        )
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                "UPDATE jobs SET payload_json=? WHERE job_id=?",
                (canonical_json(builder_payload), builder_id),
            )
            connection.execute(
                "UPDATE jobs SET payload_json=? WHERE job_id=?",
                (canonical_json(reviewer_payload), review_id),
            )
            row = connection.execute(
                "SELECT metadata_json FROM artifacts WHERE artifact_id=?",
                (review["artifact_id"],),
            ).fetchone()
            assert row is not None
            metadata = json.loads(row["metadata_json"])
            metadata.update(self._review_metadata(builder, reviewer_payload))
            connection.execute(
                "UPDATE artifacts SET metadata_json=? WHERE artifact_id=?",
                (canonical_json(metadata), review["artifact_id"]),
            )

    def _rewrite_specialized_base_contract(
        self,
        *,
        project_id: str,
        builder_id: str,
        review_id: str,
        builder: dict[str, object],
        review: dict[str, object],
        builder_payload: dict[str, object],
        artifact_type: str,
    ) -> None:
        """Coherently rebind a review while forging a specialized row payload."""

        review_builder_payload = copy.deepcopy(builder_payload)
        review_builder_payload["artifact_type"] = artifact_type
        reviewer_payload = _byox_reviewer_payload(
            project_id=project_id,
            builder_job_id=builder_id,
            builder_payload=review_builder_payload,
            specialized=True,
            policy_version=1,
        )
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                "UPDATE jobs SET payload_json=? WHERE job_id=?",
                (canonical_json(builder_payload), builder_id),
            )
            connection.execute(
                "UPDATE jobs SET payload_json=? WHERE job_id=?",
                (canonical_json(reviewer_payload), review_id),
            )
            row = connection.execute(
                "SELECT metadata_json FROM artifacts WHERE artifact_id=?",
                (review["artifact_id"],),
            ).fetchone()
            assert row is not None
            metadata = json.loads(row["metadata_json"])
            metadata.update(self._review_metadata(builder, reviewer_payload))
            connection.execute(
                "UPDATE artifacts SET metadata_json=? WHERE artifact_id=?",
                (canonical_json(metadata), review["artifact_id"]),
            )

    def _rewrite_builder_attempt_binding(
        self,
        *,
        builder_id: str,
        builder: dict[str, object],
        review: dict[str, object],
        attempt: int | float,
    ) -> None:
        """Make stored artifact and reviewer evidence agree with a forged attempt."""

        self._rewrite_job_artifact_attempt(
            job_id=builder_id,
            artifact=builder,
            attempt=attempt,
        )
        with self.database.transaction(immediate=True) as connection:
            metadata_row = connection.execute(
                "SELECT metadata_json FROM artifacts WHERE artifact_id=?",
                (review["artifact_id"],),
            ).fetchone()
            assert metadata_row is not None
            metadata = json.loads(metadata_row["metadata_json"])
            for staged in metadata["staged_inputs"]:
                if staged.get("job_id") == builder_id:
                    staged["artifact_attempt"] = attempt
            connection.execute(
                "UPDATE artifacts SET metadata_json=? WHERE artifact_id=?",
                (canonical_json(metadata), review["artifact_id"]),
            )

    def _rewrite_job_artifact_attempt(
        self,
        *,
        job_id: str,
        artifact: dict[str, object],
        attempt: int | float,
    ) -> None:
        """Coherently rewrite a job, current artifact, and label evidence attempt."""

        with self.database.transaction(immediate=True) as connection:
            artifact_row = connection.execute(
                "SELECT path,metadata_json FROM artifacts WHERE artifact_id=?",
                (artifact["artifact_id"],),
            ).fetchone()
            assert artifact_row is not None
            if type(attempt) is int:
                old_path = Path(str(artifact_row["path"]))
                new_path = old_path.parent / f"attempt-{attempt:03d}"
                if old_path != new_path:
                    old_path.rename(new_path)
                workspace = (
                    self.settings.warehouse
                    / "workspaces"
                    / job_id
                    / f"attempt-{attempt:03d}"
                )
                workspace.mkdir(parents=True, exist_ok=True)
                connection.execute(
                    "UPDATE jobs SET workspace=?,heartbeat_at=finished_at WHERE job_id=?",
                    (str(workspace), job_id),
                )
                connection.execute(
                    "UPDATE artifacts SET path=? WHERE artifact_id=?",
                    (str(new_path), artifact["artifact_id"]),
                )
            connection.execute(
                "UPDATE jobs SET attempt_count=? WHERE job_id=?",
                (attempt, job_id),
            )
            connection.execute(
                "UPDATE artifacts SET attempt_number=? WHERE artifact_id=?",
                (attempt, artifact["artifact_id"]),
            )
            connection.execute(
                "UPDATE validations SET attempt_number=? WHERE job_id=?",
                (attempt, job_id),
            )
            metadata = json.loads(artifact_row["metadata_json"])
            metadata["attempt"] = attempt
            connection.execute(
                "UPDATE artifacts SET metadata_json=? WHERE artifact_id=?",
                (canonical_json(metadata), artifact["artifact_id"]),
            )
            validations = connection.execute(
                "SELECT validation_id,validator,claims_json FROM validations WHERE job_id=? ORDER BY started_at,validation_id",
                (job_id,),
            ).fetchall()
            support = [
                {
                    "validation_id": row["validation_id"],
                    "validator": row["validator"],
                    "claims": json.loads(row["claims_json"]),
                }
                for row in validations
            ]
            labels = connection.execute(
                "SELECT label FROM artifact_validation_labels WHERE artifact_id=?",
                (artifact["artifact_id"],),
            ).fetchall()
            for label_row in labels:
                label = str(label_row["label"])
                label_support = [
                    item
                    for item in support
                    if label == "GENERATED" or label in item["claims"]
                ]
                connection.execute(
                    """
                    UPDATE artifact_validation_labels SET evidence_json=?
                    WHERE artifact_id=? AND label=?
                    """,
                    (
                        canonical_json(
                            {
                                "job_id": job_id,
                                "attempt": attempt,
                                "support": label_support,
                            }
                        ),
                        artifact["artifact_id"],
                        label,
                    ),
                )

    def _rewrite_review_attempt_binding(
        self,
        *,
        review_id: str,
        review: dict[str, object],
        attempt: int | float,
        max_attempts: int | float = 2,
    ) -> None:
        """Make a review artifact and all validation evidence use one attempt."""

        self._rewrite_job_artifact_attempt(
            job_id=review_id,
            artifact=review,
            attempt=attempt,
        )
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                "UPDATE jobs SET max_attempts=? WHERE job_id=?",
                (max_attempts, review_id),
            )

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
        reviewer = self.jobs.get(reviewer_id)
        assert reviewer is not None
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
            metadata=self._review_metadata(builder, reviewer["payload"]),
        )
        self._insert_review_validations(reviewer_id, verdict)
        return review

    def _completed_first_repair_builder(
        self,
        project_id: str,
    ) -> tuple[str, dict[str, object]]:
        self._base_graph(project_id, "FAIL")
        seed_byox_remediation_jobs(
            self.database,
            self.jobs,
            warehouse=self.settings.warehouse,
            project_ids=[project_id],
        )
        builder_id = repair_builder_job_id(project_id, 1)
        artifact = self._complete_seeded_job(
            builder_id,
            artifact_type=BYOX_REPAIR_ARTIFACT_TYPE,
            files=self._canonical_pack(f"repair-{project_id}"),
        )
        return builder_id, artifact

    def _rebind_first_repair_reviewer_to_current_builder(
        self,
        *,
        project_id: str,
        review_artifact: dict[str, object],
    ) -> None:
        """Rewrite a completed generation-1 reviewer to the current artifact."""

        builder_id = repair_builder_job_id(project_id, 1)
        reviewer_id = repair_reviewer_job_id(project_id, 1)
        managed_root = Path(
            os.path.abspath(str(self.database.path.parent / "artifacts"))
        )
        with self.database.transaction(immediate=True) as connection:
            builder_row = connection.execute(
                """
                SELECT priority,score_components_json,payload_json
                FROM jobs WHERE job_id=?
                """,
                (builder_id,),
            ).fetchone()
            assert builder_row is not None
            repaired = remediation_module._current_artifact(
                connection,
                builder_id,
                expected_type=BYOX_REPAIR_ARTIFACT_TYPE,
                managed_artifact_root=managed_root,
            )
            expected = remediation_module._repair_reviewer_spec(
                project_id=project_id,
                generation=1,
                builder_payload=json.loads(builder_row["payload_json"]),
                repaired_artifact=repaired,
                gate_job_id=CODEX_BACKEND_GATE_JOB_ID,
                priority=builder_row["priority"],
                score_components=json.loads(builder_row["score_components_json"]),
            )
            connection.execute(
                "UPDATE jobs SET payload_json=? WHERE job_id=?",
                (canonical_json(expected.payload), reviewer_id),
            )
            connection.execute(
                "UPDATE artifacts SET metadata_json=? WHERE artifact_id=?",
                (
                    canonical_json(
                        self._review_metadata(
                            repaired.staged_input(),
                            expected.payload,
                        )
                    ),
                    review_artifact["artifact_id"],
                ),
            )

    def _materialized_repair_workspace(
        self, project_id: str
    ) -> tuple[object, Path, list[dict[str, object]], tuple[str, ...], dict[str, object]]:
        self._base_graph(project_id, "REVISE")
        seed_byox_remediation_jobs(self.database, self.jobs, warehouse=self.settings.warehouse, project_ids=[project_id])
        repair_id = repair_builder_job_id(project_id, 1)
        self.jobs.promote_eligible()
        claim = self.jobs.claim_next(
            f"compatibility-{project_id}", 30, max_total=1, type_limits={}
        )
        assert claim is not None and claim.job_id == repair_id
        workspace = self.manager.allocate(repair_id, claim.attempt_count)
        _, staged = JobHandlers(
            self.settings, self.database, self.manager
        )._stage_declared_inputs(claim, workspace)
        archive_paths, selection = _byox_repair_archive_selection(
            claim, workspace, staged
        )
        assert archive_paths is not None and selection is not None
        inventory = selection["artifact_inventory"]
        assert isinstance(inventory, dict)
        root_kinds = inventory["root_kinds"]
        assert isinstance(root_kinds, dict)
        source_paths = selection["source_artifact_inventory"]["selected_paths"]
        for name in archive_paths:
            target = workspace / name
            if name in source_paths:
                source = workspace / "PRIOR_BUILD" / name
                if source.is_dir():
                    shutil.copytree(source, target)
                else:
                    shutil.copy2(source, target)
            elif root_kinds[name] == "directory":
                target.mkdir()
            else:
                target.write_text(f"generated {name}\n", encoding="utf-8")
        self.manager.discard_root_metadata(workspace, ".factory-workspace")
        return claim, workspace, staged, archive_paths, selection

    @staticmethod
    def _replace_with_same_bytes_and_mode(path: Path) -> None:
        original = path.read_bytes()
        original_mode = path.stat().st_mode & 0o777
        original_identity = (path.stat().st_dev, path.stat().st_ino)
        parent = path.parent
        parent_mode = parent.stat().st_mode & 0o777
        parent.chmod(parent_mode | 0o200)
        replacement = parent / f".{path.name}.same-bytes-replacement"
        try:
            replacement.write_bytes(original)
            replacement.chmod(original_mode)
            replacement_identity = (
                replacement.stat().st_dev,
                replacement.stat().st_ino,
            )
            if replacement_identity == original_identity:
                raise AssertionError("replacement must use a distinct inode")
            os.replace(replacement, path)
        finally:
            if replacement.exists() or replacement.is_symlink():
                replacement.unlink()
            parent.chmod(parent_mode)

    def _published_repair_metadata(
        self,
        selection: dict[str, object],
        payload: dict[str, object],
    ) -> dict[str, object]:
        cutover = selection["authoritative_cutover"]
        assert isinstance(cutover, dict)
        selected_checksum = cutover["selected_output_checksum"]
        validation_checksum = cutover["validation_snapshot_checksum"]
        paths = cutover["archive_paths"]
        declarations = payload["inputs_from_dependencies"]
        assert isinstance(declarations, list)
        own_by_path = {
            item["path"]: item for item in cutover["staged_inputs"]
        }
        staged_inputs = []
        for declaration in declarations:
            destination = declaration["destination"]
            staged_inputs.append({
                **own_by_path[destination],
                "origin": "dependency-artifact",
                "job_id": declaration["job_id"],
                "artifact_id": declaration["artifact_id"],
                "artifact_type": declaration["artifact_type"],
                "artifact_checksum": declaration["artifact_checksum"],
                "artifact_checksum_algorithm": declaration["checksum_algorithm"],
                "artifact_attempt": declaration["artifact_attempt"],
                "artifact_subpath": (
                    "." if declaration.get("artifact_root") is True
                    else declaration["subpath"]
                ),
                **(
                    {"artifact_inventory": selection["source_artifact_inventory"]}
                    if declaration.get("artifact_root") is True
                    else {}
                ),
            })
        return {
            "repair_archive_selection": selection,
            "byox_validation_cutover": cutover,
            "staged_inputs": staged_inputs,
            "validation_workspace_tree_sha256": validation_checksum,
            "validated_tree_sha256": selected_checksum,
            "archive_projection": {
                "schema_version": 1,
                "mode": "declared-worker-outputs",
                "paths": paths,
                "staged_inputs_excluded": True,
                "source_workspace_checksum_algorithm": "tree-sha256-v2",
                "source_workspace_checksum": validation_checksum,
                "projected_tree_checksum_algorithm": "tree-sha256-v2",
                "projected_tree_checksum": selected_checksum,
            },
        }

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
            self.database, self.jobs, warehouse=self.settings.warehouse, project_ids=[project_id]
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
        repair_prompt = repair["payload"]["prompt"]
        self.assertIn("Do not create any new top-level root", repair_prompt)
        self.assertIn("Record licensing information in LICENSE_BOUNDARY.md", repair_prompt)
        self.assertIn("Do not create ARTIFACT_INVENTORY.sha256", repair_prompt)

        again = seed_byox_remediation_jobs(
            self.database, self.jobs, warehouse=self.settings.warehouse, project_ids=[project_id]
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
        seed_byox_remediation_jobs(self.database, self.jobs, warehouse=self.settings.warehouse, project_ids=[project_id])
        repair_id = repair_builder_job_id(project_id, 1)
        repaired = self._complete_seeded_job(
            repair_id,
            artifact_type=BYOX_REPAIR_ARTIFACT_TYPE,
            files=self._canonical_pack("repaired"),
            metadata={"repair_archive_selection": {"paths": sorted(BYOX_CANONICAL_CHALLENGE_ROOTS)}},
        )

        result = seed_byox_remediation_jobs(
            self.database, self.jobs, warehouse=self.settings.warehouse, project_ids=[project_id]
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

    def test_completed_repair_builder_requires_canonical_success_state(self) -> None:
        attacks = (
            "attempt-zero",
            "attempt-over-bound",
            "attempt-boolean",
            "attempt-float",
            "max-attempts-mismatch",
            "owner-residue",
            "lease-residue",
            "expiry-residue",
            "retry-residue",
            "error-residue",
            "failure-residue",
            "cancel-residue",
            "missing-created",
            "missing-started",
            "missing-finished",
            "nonfinite-created",
            "nonfinite-started",
            "nonfinite-finished",
            "reversed-created",
            "reversed-started",
            "reversed-finished",
        )
        real_load = remediation_module._load_policy_jobs
        for index, attack in enumerate(attacks):
            with self.subTest(attack=attack):
                project_id = f"project-repair-terminal-{index}"
                builder_id, artifact = self._completed_first_repair_builder(
                    project_id
                )
                load_context = contextlib.nullcontext()
                if attack == "attempt-zero":
                    self._rewrite_job_artifact_attempt(
                        job_id=builder_id,
                        artifact=artifact,
                        attempt=0,
                    )
                elif attack == "attempt-over-bound":
                    self._rewrite_job_artifact_attempt(
                        job_id=builder_id,
                        artifact=artifact,
                        attempt=3,
                    )
                elif attack in {"attempt-boolean", "missing-created"}:
                    field, forged_value = (
                        ("attempt_count", True)
                        if attack == "attempt-boolean"
                        else ("created_at", None)
                    )

                    def impossible_loaded_value(
                        connection: sqlite3.Connection,
                        *,
                        field: str = field,
                        forged_value: object = forged_value,
                    ):
                        records = real_load(connection)
                        for record in records:
                            if record["job_id"] == builder_id:
                                record[field] = forged_value
                        return records

                    load_context = patch.object(
                        remediation_module,
                        "_load_policy_jobs",
                        side_effect=impossible_loaded_value,
                    )
                elif attack == "attempt-float":
                    self._rewrite_job_artifact_attempt(
                        job_id=builder_id,
                        artifact=artifact,
                        attempt=1.5,
                    )
                else:
                    statement, parameters = {
                        "max-attempts-mismatch": (
                            "UPDATE jobs SET max_attempts=3 WHERE job_id=?",
                            (),
                        ),
                        "owner-residue": (
                            "UPDATE jobs SET owner='forged-owner' WHERE job_id=?",
                            (),
                        ),
                        "lease-residue": (
                            "UPDATE jobs SET lease_token='forged-lease' WHERE job_id=?",
                            (),
                        ),
                        "expiry-residue": (
                            "UPDATE jobs SET lease_expires_at=9999999999 WHERE job_id=?",
                            (),
                        ),
                        "retry-residue": (
                            "UPDATE jobs SET retry_at=9999999999 WHERE job_id=?",
                            (),
                        ),
                        "error-residue": (
                            "UPDATE jobs SET error='forged error' WHERE job_id=?",
                            (),
                        ),
                        "failure-residue": (
                            "UPDATE jobs SET failure_kind='agent_failure' WHERE job_id=?",
                            (),
                        ),
                        "cancel-residue": (
                            "UPDATE jobs SET cancel_requested=1 WHERE job_id=?",
                            (),
                        ),
                        "missing-started": (
                            "UPDATE jobs SET started_at=NULL WHERE job_id=?",
                            (),
                        ),
                        "missing-finished": (
                            "UPDATE jobs SET finished_at=NULL WHERE job_id=?",
                            (),
                        ),
                        "nonfinite-created": (
                            "UPDATE jobs SET created_at=? WHERE job_id=?",
                            (float("inf"),),
                        ),
                        "nonfinite-started": (
                            "UPDATE jobs SET started_at=? WHERE job_id=?",
                            (float("inf"),),
                        ),
                        "nonfinite-finished": (
                            "UPDATE jobs SET finished_at=? WHERE job_id=?",
                            (float("inf"),),
                        ),
                        "reversed-created": (
                            "UPDATE jobs SET created_at=started_at+1 WHERE job_id=?",
                            (),
                        ),
                        "reversed-started": (
                            "UPDATE jobs SET started_at=finished_at+1 WHERE job_id=?",
                            (),
                        ),
                        "reversed-finished": (
                            "UPDATE jobs SET finished_at=started_at-1 WHERE job_id=?",
                            (),
                        ),
                    }[attack]
                    with self.database.transaction(immediate=True) as connection:
                        connection.execute(statement, (*parameters, builder_id))

                before = self._publication_counts()
                with load_context:
                    result = seed_byox_remediation_jobs(
                        self.database,
                        self.jobs,
                        warehouse=self.settings.warehouse,
                        project_ids=[project_id],
                    )
                self.assertEqual(0, result["created_jobs"])
                self.assertIn(
                    result["projects"][project_id]["status"],
                    {"REMEDIATION_EVIDENCE_INVALID", "REMEDIATION_GRAPH_INVALID"},
                )
                self.assertEqual(before, self._publication_counts())
                self.assertIsNone(
                    self.jobs.get(repair_reviewer_job_id(project_id, 1))
                )

    def test_completed_repair_builder_accepts_bounded_attempts(self) -> None:
        for attempt in (1, 2):
            with self.subTest(attempt=attempt):
                project_id = f"project-valid-repair-attempt-{attempt}"
                builder_id, artifact = self._completed_first_repair_builder(
                    project_id
                )
                if attempt == 2:
                    self._rewrite_job_artifact_attempt(
                        job_id=builder_id,
                        artifact=artifact,
                        attempt=attempt,
                    )

                result = seed_byox_remediation_jobs(
                    self.database,
                    self.jobs,
                    warehouse=self.settings.warehouse,
                    project_ids=[project_id],
                )

                self.assertEqual(1, result["created_jobs"])
                self.assertEqual(
                    "REVIEWER_SEEDED",
                    result["projects"][project_id]["status"],
                )
                reviewer = self.jobs.get(repair_reviewer_job_id(project_id, 1))
                assert reviewer is not None
                [candidate] = reviewer["payload"]["inputs_from_dependencies"]
                self.assertEqual(attempt, candidate["artifact_attempt"])

    def test_modern_repair_rejects_self_consistent_empty_staging(self) -> None:
        project_id = "project-empty-modern-cutover-staging"
        _, artifact = self._completed_first_repair_builder(project_id)
        with self.database.transaction(immediate=True) as connection:
            row = connection.execute(
                "SELECT metadata_json FROM artifacts WHERE artifact_id=?",
                (artifact["artifact_id"],),
            ).fetchone()
            assert row is not None
            metadata = json.loads(row["metadata_json"])
            cutover = metadata["repair_archive_selection"]["authoritative_cutover"]
            cutover["staged_inputs"] = []
            cutover["snapshot_roots"] = list(cutover["archive_paths"])
            cutover["validation_snapshot_checksum"] = cutover[
                "selected_output_checksum"
            ]
            cutover_body = {
                key: value for key, value in cutover.items()
                if key != "manifest_sha256"
            }
            cutover["manifest_sha256"] = hashlib.sha256(
                canonical_json(cutover_body).encode("utf-8")
            ).hexdigest()
            metadata["byox_validation_cutover"] = copy.deepcopy(cutover)
            metadata["staged_inputs"] = []
            metadata["validation_workspace_tree_sha256"] = cutover[
                "validation_snapshot_checksum"
            ]
            metadata["archive_projection"]["source_workspace_checksum"] = cutover[
                "validation_snapshot_checksum"
            ]
            connection.execute(
                "UPDATE artifacts SET metadata_json=? WHERE artifact_id=?",
                (canonical_json(metadata), artifact["artifact_id"]),
            )
        before = self._publication_counts()
        result = seed_byox_remediation_jobs(
            self.database, self.jobs, warehouse=self.settings.warehouse, project_ids=[project_id]
        )
        self.assertEqual(0, result["created_jobs"])
        self.assertEqual(
            "REMEDIATION_EVIDENCE_INVALID",
            result["projects"][project_id]["status"],
        )
        self.assertEqual(before, self._publication_counts())
        self.assertIsNone(self.jobs.get(repair_reviewer_job_id(project_id, 1)))

    def test_forged_completed_repair_builder_cannot_seed_next_generation(self) -> None:
        project_id = "project-forged-repair-chain"
        builder_id, artifact = self._completed_first_repair_builder(project_id)
        seed_byox_remediation_jobs(
            self.database,
            self.jobs,
            warehouse=self.settings.warehouse,
            project_ids=[project_id],
        )
        review_artifact = self._complete_repair_review(project_id, 1, "FAIL")
        self._rewrite_job_artifact_attempt(
            job_id=builder_id,
            artifact=artifact,
            attempt=3,
        )
        self._rebind_first_repair_reviewer_to_current_builder(
            project_id=project_id,
            review_artifact=review_artifact,
        )
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                """
                UPDATE jobs
                SET owner='forged-owner',lease_token='forged-lease',
                    lease_expires_at=9999999999,retry_at=9999999999,
                    error='forged error',failure_kind='agent_failure',
                    cancel_requested=1
                WHERE job_id=?
                """,
                (builder_id,),
            )

        before = self._publication_counts()
        result = seed_byox_remediation_jobs(
            self.database,
            self.jobs,
            warehouse=self.settings.warehouse,
            project_ids=[project_id],
            max_repair_generations=2,
        )

        self.assertEqual(0, result["created_jobs"])
        self.assertEqual(
            "REMEDIATION_EVIDENCE_INVALID",
            result["projects"][project_id]["status"],
        )
        self.assertEqual(before, self._publication_counts())
        self.assertIsNone(self.jobs.get(repair_builder_job_id(project_id, 2)))

    def test_repair_review_validation_defends_against_forged_builder_state(
        self,
    ) -> None:
        project_id = "project-repair-review-defense"
        builder_id, artifact = self._completed_first_repair_builder(project_id)
        seed_byox_remediation_jobs(
            self.database,
            self.jobs,
            warehouse=self.settings.warehouse,
            project_ids=[project_id],
        )
        review_artifact = self._complete_repair_review(project_id, 1, "FAIL")
        self._rewrite_job_artifact_attempt(
            job_id=builder_id,
            artifact=artifact,
            attempt=3,
        )
        self._rebind_first_repair_reviewer_to_current_builder(
            project_id=project_id,
            review_artifact=review_artifact,
        )

        with self.database.transaction(immediate=True) as connection:
            records = remediation_module._load_policy_jobs(connection)
            review_record = next(
                record
                for record in records
                if record["job_id"] == repair_reviewer_job_id(project_id, 1)
            )
            snapshot = next(
                item
                for item in remediation_module.load_active_byox_projects_from_connection(
                    connection
                )
                if item.project_id == project_id
            )
            template = build_byox_job_spec(snapshot)
            with self.assertRaisesRegex(
                ByoxRemediationError,
                "repair review builder has an impossible successful execution state",
            ):
                remediation_module._validated_review(
                    connection,
                    review_record,
                    project_id,
                    CODEX_BACKEND_GATE_JOB_ID,
                    Path(
                        os.path.abspath(
                            str(self.database.path.parent / "artifacts")
                        )
                    ),
                    template,
                    specialized_byox_job_specs_by_id(
                        remediation_module.load_active_byox_projects_from_connection(
                            connection
                        )
                    ),
                )

    def test_finite_cap_and_second_generation_chain(self) -> None:
        project_id = "project-cap"
        self._base_graph(project_id, "REVISE")
        seed_byox_remediation_jobs(self.database, self.jobs, warehouse=self.settings.warehouse, project_ids=[project_id])
        first_builder = repair_builder_job_id(project_id, 1)
        self._complete_seeded_job(
            first_builder,
            artifact_type=BYOX_REPAIR_ARTIFACT_TYPE,
            files=self._canonical_pack("repair-one"),
        )
        seed_byox_remediation_jobs(self.database, self.jobs, warehouse=self.settings.warehouse, project_ids=[project_id])
        first_reviewer = repair_reviewer_job_id(project_id, 1)
        first_review = self._complete_repair_review(project_id, 1, "FAIL")

        capped = seed_byox_remediation_jobs(
            self.database,
            self.jobs,
            warehouse=self.settings.warehouse,
            project_ids=[project_id],
            max_repair_generations=1,
        )
        self.assertEqual("REPAIR_LIMIT_EXHAUSTED", capped["projects"][project_id]["status"])
        self.assertIsNone(self.jobs.get(repair_builder_job_id(project_id, 2)))

        second = seed_byox_remediation_jobs(
            self.database,
            self.jobs,
            warehouse=self.settings.warehouse,
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
        seed_byox_remediation_jobs(self.database, self.jobs, warehouse=self.settings.warehouse, project_ids=[project_id])
        self._complete_seeded_job(
            repair_builder_job_id(project_id, 1),
            artifact_type=BYOX_REPAIR_ARTIFACT_TYPE,
            files=self._canonical_pack("pass-repair"),
        )
        seed_byox_remediation_jobs(self.database, self.jobs, warehouse=self.settings.warehouse, project_ids=[project_id])
        self._complete_repair_review(project_id, 1, "PASS")

        result = seed_byox_remediation_jobs(
            self.database, self.jobs, warehouse=self.settings.warehouse, project_ids=[project_id]
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
                    self.database, self.jobs, warehouse=self.settings.warehouse, project_ids=[project_id]
                )
                self.assertEqual(
                    "REMEDIATION_EVIDENCE_INVALID",
                    result["projects"][project_id]["status"],
                )
                self.assertIsNone(self.jobs.get(repair_builder_job_id(project_id, 1)))

    def test_remediation_rejects_legacy_or_incomplete_review_contract_evidence(self) -> None:
        cases = (
            "legacy-command",
            "wrong-contract-version",
            "float-contract-version",
            "forged-evidence-count",
            "float-evidence-contract-version",
            "mismatched-evaluation-digest",
            "row-verdict-mismatch",
            "verdict-extra-evidence",
            "verdict-claims",
            "verdict-command-fields",
            "schema-extra-evidence",
            "schema-claims",
            "schema-command-fields",
            "required-files-extra-evidence",
            "required-files-claims",
            "required-files-command-fields",
            "duplicate-verdict-row",
            "duplicate-schema-row",
            "duplicate-required-files-row",
            "acceptance-extra-evidence",
            "acceptance-claims",
            "acceptance-command-fields",
            "schema-wrong-identity",
            "failed-required-files",
            "missing-required-files",
            "missing-closed-acceptance",
        )
        for suffix in cases:
            project_id = f"project-contract-{suffix}"
            with self.subTest(suffix=suffix):
                _, review_id, _, _ = self._base_graph(project_id, "FAIL")
                with self.database.transaction(immediate=True) as connection:
                    if suffix in {
                        "legacy-command",
                        "wrong-contract-version",
                        "float-contract-version",
                    }:
                        row = connection.execute(
                            "SELECT payload_json FROM jobs WHERE job_id=?",
                            (review_id,),
                        ).fetchone()
                        payload = json.loads(row["payload_json"])
                        verdict = next(
                            item
                            for item in payload["validators"]
                            if item.get("type") == "review_verdict"
                        )
                        if suffix == "legacy-command":
                            payload["validators"].insert(
                                -1,
                                {
                                    "type": "command",
                                    "name": "byox-independent-review-concrete-evidence",
                                    "argv": ["python3", "-c", "raise SystemExit(0)"],
                                },
                            )
                        else:
                            verdict["contract_version"] = (
                                2.0 if suffix == "float-contract-version" else 1
                            )
                        connection.execute(
                            "UPDATE jobs SET payload_json=? WHERE job_id=?",
                            (canonical_json(payload), review_id),
                        )
                    elif suffix in {
                        "forged-evidence-count",
                        "float-evidence-contract-version",
                        "mismatched-evaluation-digest",
                        "row-verdict-mismatch",
                        "verdict-extra-evidence",
                    }:
                        row = connection.execute(
                            """
                            SELECT validation_id,evidence_json FROM validations
                            WHERE job_id=? AND validator=?
                            """,
                            (review_id, "byox-independent-review-verdict"),
                        ).fetchone()
                        evidence = json.loads(row["evidence_json"])
                        if suffix == "forged-evidence-count":
                            evidence["entry_counts"]["evidence"] = 2
                        elif suffix == "float-evidence-contract-version":
                            evidence["contract_version"] = 2.0
                        elif suffix == "mismatched-evaluation-digest":
                            evidence["evaluation_sha256"] = "0" * 64
                        elif suffix == "row-verdict-mismatch":
                            evidence["verdict"] = "PASS"
                            evidence["reviewer_recommends_acceptance"] = True
                        else:
                            evidence["forged"] = True
                        connection.execute(
                            "UPDATE validations SET evidence_json=? WHERE validation_id=?",
                            (canonical_json(evidence), row["validation_id"]),
                        )
                    elif suffix in {
                        "verdict-claims",
                        "schema-claims",
                        "required-files-claims",
                        "acceptance-claims",
                    }:
                        validator = (
                            "byox-independent-review-verdict"
                            if suffix == "verdict-claims"
                            else (
                                "byox-independent-review-schema"
                                if suffix == "schema-claims"
                                else (
                                    "byox-independent-review-files"
                                    if suffix == "required-files-claims"
                                    else "byox-independent-review-acceptance"
                                )
                            )
                        )
                        connection.execute(
                            """
                            UPDATE validations SET claims_json='["TESTED"]'
                            WHERE job_id=? AND validator=?
                            """,
                            (review_id, validator),
                        )
                    elif suffix in {
                        "verdict-command-fields",
                        "schema-command-fields",
                        "required-files-command-fields",
                        "acceptance-command-fields",
                    }:
                        validator = (
                            "byox-independent-review-verdict"
                            if suffix == "verdict-command-fields"
                            else (
                                "byox-independent-review-schema"
                                if suffix == "schema-command-fields"
                                else (
                                    "byox-independent-review-files"
                                    if suffix == "required-files-command-fields"
                                    else "byox-independent-review-acceptance"
                                )
                            )
                        )
                        connection.execute(
                            """
                            UPDATE validations
                            SET command_json='["true"]',exit_code=0,
                                stdout_path='/tmp/forged-out',
                                stderr_path='/tmp/forged-err'
                            WHERE job_id=? AND validator=?
                            """,
                            (review_id, validator),
                        )
                    elif suffix in {
                        "schema-extra-evidence",
                        "required-files-extra-evidence",
                        "acceptance-extra-evidence",
                    }:
                        validator = (
                            "byox-independent-review-schema"
                            if suffix == "schema-extra-evidence"
                            else (
                                "byox-independent-review-files"
                                if suffix == "required-files-extra-evidence"
                                else "byox-independent-review-acceptance"
                            )
                        )
                        row = connection.execute(
                            """
                            SELECT validation_id,evidence_json FROM validations
                            WHERE job_id=? AND validator=?
                            """,
                            (review_id, validator),
                        ).fetchone()
                        evidence = json.loads(row["evidence_json"])
                        evidence["forged"] = True
                        connection.execute(
                            "UPDATE validations SET evidence_json=? WHERE validation_id=?",
                            (canonical_json(evidence), row["validation_id"]),
                        )
                    elif suffix in {
                        "duplicate-verdict-row",
                        "duplicate-schema-row",
                        "duplicate-required-files-row",
                    }:
                        validator = (
                            "byox-independent-review-verdict"
                            if suffix == "duplicate-verdict-row"
                            else (
                                "byox-independent-review-schema"
                                if suffix == "duplicate-schema-row"
                                else "byox-independent-review-files"
                            )
                        )
                        connection.execute(
                            """
                            INSERT INTO validations(
                                validation_id,job_id,validator,status,command_json,
                                exit_code,stdout_path,stderr_path,evidence_json,
                                started_at,finished_at,attempt_number,claims_json
                            )
                            SELECT validation_id || '-duplicate',job_id,validator,
                                   status,command_json,exit_code,stdout_path,
                                   stderr_path,evidence_json,started_at,finished_at,
                                   attempt_number,claims_json
                            FROM validations WHERE job_id=? AND validator=?
                            """,
                            (review_id, validator),
                        )
                    elif suffix == "schema-wrong-identity":
                        artifact = connection.execute(
                            "SELECT path FROM artifacts WHERE job_id=?",
                            (review_id,),
                        ).fetchone()
                        evaluation_path = Path(artifact["path"]) / "EVALUATION.json"
                        evaluation = json.loads(evaluation_path.read_text(encoding="utf-8"))
                        evaluation["project_id"] = "project-forged-identity"
                        evaluation_path.write_text(
                            canonical_json(evaluation) + "\n", encoding="utf-8"
                        )
                    elif suffix == "failed-required-files":
                        connection.execute(
                            """
                            UPDATE validations SET status='FAIL'
                            WHERE job_id=? AND validator=?
                            """,
                            (review_id, "byox-independent-review-files"),
                        )
                    else:
                        validator = (
                            "byox-independent-review-files"
                            if suffix == "missing-required-files"
                            else "byox-independent-review-acceptance"
                        )
                        connection.execute(
                            """
                            DELETE FROM validations
                            WHERE job_id=? AND validator=?
                            """,
                            (review_id, validator),
                        )

                result = seed_byox_remediation_jobs(
                    self.database, self.jobs, warehouse=self.settings.warehouse, project_ids=[project_id]
                )
                self.assertEqual(
                    "REMEDIATION_EVIDENCE_INVALID",
                    result["projects"][project_id]["status"],
                )
                self.assertIsNone(
                    self.jobs.get(repair_builder_job_id(project_id, 1))
                )

    def test_remediation_rejects_missing_mutated_or_aliased_review_files(self) -> None:
        cases = (
            "deleted-review",
            "mutated-validation",
            "symlinked-review",
            "hardlinked-validation",
        )
        for suffix in cases:
            project_id = f"project-review-tree-{suffix}"
            with self.subTest(suffix=suffix):
                _, review_id, _, _ = self._base_graph(project_id, "FAIL")
                with self.database.connect() as connection:
                    artifact_path = Path(
                        connection.execute(
                            "SELECT path FROM artifacts WHERE job_id=?",
                            (review_id,),
                        ).fetchone()["path"]
                    )
                review_path = artifact_path / "REVIEW.md"
                validation_path = artifact_path / "VALIDATION.md"
                if suffix == "deleted-review":
                    review_path.unlink()
                elif suffix == "mutated-validation":
                    validation_path.write_text(
                        "# Independent checks\nmutated after publication\n",
                        encoding="utf-8",
                    )
                elif suffix == "symlinked-review":
                    review_path.unlink()
                    review_path.symlink_to("EVALUATION.json")
                else:
                    validation_path.unlink()
                    os.link(review_path, validation_path)

                result = seed_byox_remediation_jobs(
                    self.database, self.jobs, warehouse=self.settings.warehouse, project_ids=[project_id]
                )
                self.assertEqual(
                    "REMEDIATION_EVIDENCE_INVALID",
                    result["projects"][project_id]["status"],
                )
                self.assertIsNone(
                    self.jobs.get(repair_builder_job_id(project_id, 1))
                )

    def test_remediation_rejects_noninteger_staged_artifact_attempts(self) -> None:
        for suffix, attacked_attempt in (("boolean", True), ("float", 1.0)):
            project_id = f"project-attempt-type-{suffix}"
            with self.subTest(suffix=suffix):
                _, review_id, _, review = self._base_graph(project_id, "FAIL")
                with self.database.transaction(immediate=True) as connection:
                    metadata = json.loads(
                        connection.execute(
                            "SELECT metadata_json FROM artifacts WHERE artifact_id=?",
                            (review["artifact_id"],),
                        ).fetchone()["metadata_json"]
                    )
                    metadata["staged_inputs"][0]["artifact_attempt"] = attacked_attempt
                    connection.execute(
                        "UPDATE artifacts SET metadata_json=? WHERE artifact_id=?",
                        (canonical_json(metadata), review["artifact_id"]),
                    )
                result = seed_byox_remediation_jobs(
                    self.database, self.jobs, warehouse=self.settings.warehouse, project_ids=[project_id]
                )
                self.assertEqual(
                    "REMEDIATION_EVIDENCE_INVALID",
                    result["projects"][project_id]["status"],
                )
                self.assertIsNone(
                    self.jobs.get(repair_builder_job_id(project_id, 1))
                )

    def test_remediation_rejects_ambiguous_stored_payloads_without_rewrite(self) -> None:
        project_id = "project-ambiguous-stored-contract"
        _, review_id, _, _ = self._base_graph(project_id, "FAIL")
        with self.database.connect() as connection:
            original = connection.execute(
                "SELECT payload_json FROM jobs WHERE job_id=?", (review_id,)
            ).fetchone()["payload_json"]
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
                with self.database.transaction(immediate=True) as connection:
                    connection.execute(
                        "UPDATE jobs SET payload_json=? WHERE job_id=?",
                        (attacked, review_id),
                    )
                with self.assertRaises(ByoxRemediationError):
                    seed_byox_remediation_jobs(
                        self.database, self.jobs, warehouse=self.settings.warehouse, project_ids=[project_id]
                    )
                with self.database.connect() as connection:
                    persisted = connection.execute(
                        "SELECT payload_json FROM jobs WHERE job_id=?", (review_id,)
                    ).fetchone()["payload_json"]
                self.assertEqual(attacked, persisted)
                with self.database.transaction(immediate=True) as connection:
                    connection.execute(
                        "UPDATE jobs SET payload_json=? WHERE job_id=?",
                        (original, review_id),
                    )

    def test_remediation_rejects_symlinked_or_oversized_review_archives(self) -> None:
        for suffix in (
            "parent-symlink",
            "oversized-evaluation",
            "oversized-review",
            "deeply-nested-evaluation",
            "integer-digit-limit",
        ):
            project_id = f"project-archive-{suffix}"
            with self.subTest(suffix=suffix):
                _, review_id, _, _ = self._base_graph(project_id, "FAIL")
                with self.database.connect() as connection:
                    artifact_path = Path(
                        connection.execute(
                            "SELECT path FROM artifacts WHERE job_id=?",
                            (review_id,),
                        ).fetchone()["path"]
                    )
                if suffix == "parent-symlink":
                    job_directory = artifact_path.parent
                    real_directory = job_directory.with_name(
                        f"{job_directory.name}-real"
                    )
                    job_directory.rename(real_directory)
                    job_directory.symlink_to(real_directory, target_is_directory=True)
                elif suffix == "oversized-evaluation":
                    (artifact_path / "EVALUATION.json").write_bytes(
                        b" " * (MAX_REVIEW_EVALUATION_BYTES + 1)
                    )
                elif suffix == "oversized-review":
                    (artifact_path / "REVIEW.md").write_bytes(
                        b" " * (MAX_REVIEW_DOCUMENT_BYTES + 1)
                    )
                elif suffix == "deeply-nested-evaluation":
                    (artifact_path / "EVALUATION.json").write_text(
                        "[" * 1_100 + "0" + "]" * 1_100,
                        encoding="utf-8",
                    )
                else:
                    (artifact_path / "EVALUATION.json").write_text(
                        "9" * 5_000,
                        encoding="utf-8",
                    )

                result = seed_byox_remediation_jobs(
                    self.database, self.jobs, warehouse=self.settings.warehouse, project_ids=[project_id]
                )
                self.assertEqual(
                    "REMEDIATION_EVIDENCE_INVALID",
                    result["projects"][project_id]["status"],
                )
                self.assertIsNone(
                    self.jobs.get(repair_builder_job_id(project_id, 1))
                )

    def test_remediation_rejects_component_and_evaluation_path_races(self) -> None:
        for suffix in (
            "component-replacement",
            "parent-replacement-during-read",
            "evaluation-replacement",
        ):
            project_id = f"project-race-{suffix}"
            with self.subTest(suffix=suffix):
                _, review_id, _, _ = self._base_graph(project_id, "FAIL")
                with self.database.connect() as connection:
                    artifact_path = Path(
                        connection.execute(
                            "SELECT path FROM artifacts WHERE job_id=?",
                            (review_id,),
                        ).fetchone()["path"]
                    )
                raced = False
                if suffix == "component-replacement":
                    real_open = os.open

                    def racing_open(path, flags, *args, **kwargs):
                        nonlocal raced
                        if (
                            not raced
                            and path == artifact_path.name
                            and kwargs.get("dir_fd") is not None
                        ):
                            raced = True
                            displaced = artifact_path.with_name(
                                f"{artifact_path.name}-displaced"
                            )
                            artifact_path.rename(displaced)
                            artifact_path.mkdir()
                        return real_open(path, flags, *args, **kwargs)

                    patcher = patch(
                        "learnfactory.byox_remediation.os.open",
                        side_effect=racing_open,
                    )
                else:
                    real_read = os.read

                    def racing_read(descriptor, size):
                        nonlocal raced
                        if not raced:
                            raced = True
                            if suffix == "evaluation-replacement":
                                evaluation_path = artifact_path / "EVALUATION.json"
                                displaced = artifact_path / "EVALUATION.displaced.json"
                                evaluation_path.rename(displaced)
                                evaluation_path.write_text("{}\n", encoding="utf-8")
                            else:
                                job_directory = artifact_path.parent
                                displaced = job_directory.with_name(
                                    f"{job_directory.name}-displaced"
                                )
                                job_directory.rename(displaced)
                                job_directory.mkdir()
                        return real_read(descriptor, size)

                    patcher = patch(
                        "learnfactory.byox_remediation.os.read",
                        side_effect=racing_read,
                    )
                with patcher:
                    result = seed_byox_remediation_jobs(
                        self.database, self.jobs, warehouse=self.settings.warehouse, project_ids=[project_id]
                    )
                self.assertTrue(raced)
                self.assertEqual(
                    "REMEDIATION_EVIDENCE_INVALID",
                    result["projects"][project_id]["status"],
                )

    def test_review_snapshot_rejects_document_and_namespace_sandwiches(self) -> None:
        for file_name, namespace_swap in (
            (file_name, namespace_swap)
            for file_name in ("EVALUATION.json", "REVIEW.md", "VALIDATION.md")
            for namespace_swap in (False, True)
        ):
            mode = "namespace" if namespace_swap else "content"
            project_id = (
                f"project-review-sandwich-{file_name.split('.')[0].lower()}-{mode}"
            )
            with self.subTest(file_name=file_name, namespace_swap=namespace_swap):
                _, review_id, _, _ = self._base_graph(project_id, "FAIL")
                with self.database.connect() as connection:
                    root = Path(
                        connection.execute(
                            "SELECT path FROM artifacts WHERE job_id=?",
                            (review_id,),
                        ).fetchone()["path"]
                    )
                target = root / file_name
                original = target.read_bytes()
                forged = b"X" * len(original)
                real_read = os.read
                raced = False

                def sandwich_read(descriptor: int, size: int) -> bytes:
                    nonlocal raced
                    try:
                        opened = Path(os.readlink(f"/proc/self/fd/{descriptor}"))
                    except OSError:
                        opened = Path("/")
                    if not raced and opened == target:
                        raced = True
                        if namespace_swap:
                            displaced = target.with_name(f"{target.name}.displaced")
                            target.rename(displaced)
                            target.write_bytes(forged)
                            chunk = real_read(descriptor, size)
                            target.unlink()
                            displaced.rename(target)
                            return chunk
                        target.write_bytes(forged)
                        chunk = real_read(descriptor, size)
                        target.write_bytes(original)
                        return chunk
                    return real_read(descriptor, size)

                before = self._publication_counts()
                with patch(
                    "learnfactory.byox_remediation.os.read",
                    side_effect=sandwich_read,
                ):
                    self._assert_invalid_without_publication(project_id, before)
                self.assertTrue(raced)

    def test_transient_shared_ancestor_rename_preserves_pinned_evidence(self) -> None:
        project_id = "project-transient-shared-ancestor"
        _, review_id, _, _ = self._base_graph(project_id, "FAIL")
        with self.database.connect() as connection:
            review_root = Path(
                connection.execute(
                    "SELECT path FROM artifacts WHERE job_id=?",
                    (review_id,),
                ).fetchone()["path"]
            )
        managed_root = self.database.path.parent / "artifacts"
        target = review_root / "EVALUATION.json"
        target_relative = target.relative_to(managed_root)
        displaced = managed_root.with_name(f"{managed_root.name}-displaced")
        real_read = os.read
        raced = False

        def rename_restore_read(descriptor: int, size: int) -> bytes:
            nonlocal raced
            try:
                opened = Path(os.readlink(f"/proc/self/fd/{descriptor}"))
            except OSError:
                opened = Path("/")
            if not raced and opened == target:
                raced = True
                managed_root.rename(displaced)
                try:
                    forged = managed_root / target_relative
                    forged.parent.mkdir(parents=True)
                    forged.write_text("outside pinned descriptor\n", encoding="utf-8")
                    return real_read(descriptor, size)
                finally:
                    shutil.rmtree(managed_root)
                    displaced.rename(managed_root)
            return real_read(descriptor, size)

        with patch(
            "learnfactory.byox_remediation.os.read",
            side_effect=rename_restore_read,
        ):
            result = seed_byox_remediation_jobs(
                self.database,
                self.jobs,
                warehouse=self.settings.warehouse,
                project_ids=[project_id],
            )
        self.assertTrue(raced)
        self.assertEqual(
            "REPAIR_BUILDER_SEEDED",
            result["projects"][project_id]["status"],
        )
        self.assertFalse(displaced.exists())

    def test_unrelated_ancestor_directory_churn_does_not_invalidate_snapshot(self) -> None:
        shared = self.root / "shared-ancestor"
        managed = shared / "warehouse" / "artifacts"
        artifact = managed / "job" / "attempt-001"
        artifact.mkdir(parents=True)
        (artifact / "README.md").write_text("stable\n", encoding="utf-8")
        baseline = remediation_module._descriptor_tree_snapshot(
            artifact,
            managed_artifact_root=managed,
        )
        marker = shared / "unrelated-worker"
        real_open = os.open
        mutated = False

        def mutate_ancestor(path, flags, *args, **kwargs):
            nonlocal mutated
            if (
                not mutated
                and path == shared.name
                and kwargs.get("dir_fd") is not None
            ):
                marker.mkdir()
                mutated = True
            return real_open(path, flags, *args, **kwargs)

        with patch(
            "learnfactory.byox_remediation.os.open",
            side_effect=mutate_ancestor,
        ):
            snapshot = remediation_module._descriptor_tree_snapshot(
                artifact,
                managed_artifact_root=managed,
            )

        self.assertTrue(mutated)
        self.assertEqual(1, snapshot.files)
        self.assertIn("README.md", snapshot.paths)
        self.assertEqual(baseline.checksum, snapshot.checksum)

    def test_descriptor_directory_discovery_and_revalidation_stop_at_bound(self) -> None:
        class Entry:
            def __init__(self, name: str):
                self.name = name

        class BombScan:
            def __init__(self, allowed_yields: int):
                self.allowed_yields = allowed_yields
                self.yields = 0

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def __iter__(self):
                return self

            def __next__(self):
                self.yields += 1
                if self.yields > self.allowed_yields:
                    raise AssertionError(
                        f"scandir consumed entry {self.yields} past its sentinel"
                    )
                return Entry(f"entry-{self.yields:08d}")

        managed = self.root / "bounded-artifacts"
        candidate = managed / "candidate"
        candidate.mkdir(parents=True)
        discovery = BombScan(
            remediation_module._ARTIFACT_TREE_MAX_ENTRIES + 1
        )
        with patch(
            "learnfactory.byox_remediation.os.scandir", return_value=discovery
        ):
            with self.assertRaisesRegex(
                ByoxRemediationError, "maximum entry count"
            ):
                remediation_module._descriptor_tree_snapshot(
                    candidate,
                    managed_artifact_root=managed,
                )
        self.assertEqual(
            remediation_module._ARTIFACT_TREE_MAX_ENTRIES + 1,
            discovery.yields,
        )

        (candidate / "only-entry").write_text("bounded\n", encoding="utf-8")
        real_scandir = os.scandir
        revalidation = BombScan(2)
        calls = 0

        def scan_once_then_bomb(descriptor):
            nonlocal calls
            calls += 1
            return real_scandir(descriptor) if calls == 1 else revalidation

        with patch(
            "learnfactory.byox_remediation.os.scandir",
            side_effect=scan_once_then_bomb,
        ):
            with self.assertRaisesRegex(
                ByoxRemediationError, "names changed after read"
            ):
                remediation_module._descriptor_tree_snapshot(
                    candidate,
                    managed_artifact_root=managed,
                )
        self.assertEqual(2, revalidation.yields)

    def test_artifact_status_and_label_contradictions_publish_nothing(self) -> None:
        for owner, coherent_blocked in (
            ("builder", False),
            ("review", False),
            ("builder", True),
            ("review", True),
        ):
            suffix = f"{owner}-{'blocked' if coherent_blocked else 'mismatch'}"
            project_id = f"project-artifact-status-{suffix}"
            with self.subTest(owner=owner, coherent_blocked=coherent_blocked):
                builder_id, review_id, _, _ = self._base_graph(
                    project_id, "FAIL"
                )
                target = builder_id if owner == "builder" else review_id
                with self.database.transaction(immediate=True) as connection:
                    artifact = connection.execute(
                        "SELECT artifact_id FROM artifacts WHERE job_id=?",
                        (target,),
                    ).fetchone()
                    assert artifact is not None
                    if coherent_blocked:
                        connection.execute(
                            """
                            INSERT INTO artifact_validation_labels(
                                artifact_id,label,evidence_json,created_at
                            ) VALUES (?,'BLOCKED','{}',?)
                            """,
                            (artifact["artifact_id"], now()),
                        )
                        attacked_status = "GENERATED+BLOCKED"
                    else:
                        attacked_status = "FAILED+BLOCKED"
                    connection.execute(
                        "UPDATE artifacts SET validation_status=? WHERE artifact_id=?",
                        (attacked_status, artifact["artifact_id"]),
                    )
                before = self._publication_counts()
                self._assert_invalid_without_publication(project_id, before)

    def test_capability_gate_requires_exact_generated_status(self) -> None:
        project_id = "project-gate-status"
        self._base_graph(project_id, "FAIL")
        with self.database.transaction(immediate=True) as connection:
            artifact = connection.execute(
                "SELECT artifact_id FROM artifacts WHERE job_id=?",
                (CODEX_BACKEND_GATE_JOB_ID,),
            ).fetchone()
            assert artifact is not None
            connection.execute(
                """
                INSERT INTO artifact_validation_labels(
                    artifact_id,label,evidence_json,created_at
                ) VALUES (?,'PARTIAL','{}',?)
                """,
                (artifact["artifact_id"], now()),
            )
            connection.execute(
                "UPDATE artifacts SET validation_status='GENERATED+PARTIAL' WHERE artifact_id=?",
                (artifact["artifact_id"],),
            )
        before = self._publication_counts()
        with self.assertRaisesRegex(
            ByoxRemediationError, "conflicts with its BYOX profile"
        ):
            seed_byox_remediation_jobs(
                self.database, self.jobs, warehouse=self.settings.warehouse, project_ids=[project_id]
            )
        self.assertEqual(before, self._publication_counts())

    def test_capability_gate_rejects_coherently_rebound_extra_file(self) -> None:
        project_id = "project-gate-extra-file"
        self._base_graph(project_id, "FAIL")
        with self.database.transaction(immediate=True) as connection:
            artifact = connection.execute(
                "SELECT artifact_id,path,metadata_json FROM artifacts WHERE job_id=?",
                (CODEX_BACKEND_GATE_JOB_ID,),
            ).fetchone()
            assert artifact is not None
            root = Path(str(artifact["path"]))
            (root / "UNDECLARED.txt").write_text("not authority\n", encoding="utf-8")
            checksum = tree_sha256(root)
            metadata = json.loads(artifact["metadata_json"])
            metadata["validated_tree_sha256"] = checksum
            connection.execute(
                "UPDATE artifacts SET checksum=?,metadata_json=? WHERE artifact_id=?",
                (checksum, canonical_json(metadata), artifact["artifact_id"]),
            )
        before = self._publication_counts()
        with self.assertRaisesRegex(ByoxRemediationError, "sentinel content"):
            seed_byox_remediation_jobs(
                self.database, self.jobs, warehouse=self.settings.warehouse, project_ids=[project_id]
            )
        self.assertEqual(before, self._publication_counts())

    def test_coherent_builder_artifact_type_switch_publishes_nothing(self) -> None:
        project_id = "project-coherent-artifact-type-switch"
        builder_id, review_id, builder, review = self._base_graph(
            project_id, "FAIL"
        )
        with self.database.transaction(immediate=True) as connection:
            row = connection.execute(
                "SELECT payload_json FROM jobs WHERE job_id=?", (builder_id,)
            ).fetchone()
            assert row is not None
            builder_payload = json.loads(row["payload_json"])
            builder_payload["artifact_type"] = "project_challenge_pack"
            connection.execute(
                "UPDATE jobs SET payload_json=? WHERE job_id=?",
                (canonical_json(builder_payload), builder_id),
            )
            connection.execute(
                "UPDATE artifacts SET type='project_challenge_pack' WHERE job_id=?",
                (builder_id,),
            )
            switched_builder = {
                **builder,
                "artifact_type": "project_challenge_pack",
            }
            reviewer_payload = _byox_reviewer_payload(
                project_id=project_id,
                builder_job_id=builder_id,
                builder_payload=builder_payload,
                specialized=True,
                policy_version=1,
            )
            connection.execute(
                "UPDATE jobs SET payload_json=? WHERE job_id=?",
                (canonical_json(reviewer_payload), review_id),
            )
            connection.execute(
                "UPDATE artifacts SET metadata_json=? WHERE artifact_id=?",
                (
                    canonical_json(
                        self._review_metadata(switched_builder, reviewer_payload)
                    ),
                    review["artifact_id"],
                ),
            )
        before = self._publication_counts()
        self._assert_invalid_without_publication(project_id, before)

    def test_generic_builder_requires_complete_canonical_payload(self) -> None:
        attacks = (
            "source-provenance",
            "project-provenance",
            "prompt",
            "validators",
            "artifact-path",
            "seed-policy",
            "execution-policy",
            "artifact-profile-extra",
            "timeout",
            "unexpected-field",
            "removed-field",
            "type-change",
            "value-change",
        )
        for index, attack in enumerate(attacks):
            with self.subTest(attack=attack):
                project_id = f"project-complete-generic-payload-{index}"
                builder_id, review_id, builder, review = self._base_graph(
                    project_id, "FAIL"
                )
                with self.database.connect() as connection:
                    row = connection.execute(
                        "SELECT payload_json FROM jobs WHERE job_id=?",
                        (builder_id,),
                    ).fetchone()
                assert row is not None
                builder_payload = json.loads(row["payload_json"])
                snapshot_sha256 = builder_payload["provenance"]["snapshot_sha256"]
                if attack == "source-provenance":
                    builder_payload["provenance"]["source"].update(
                        {
                            "source_id": "forged-source",
                            "commit_hash": "forged-commit",
                            "name": "forged-name",
                        }
                    )
                elif attack == "project-provenance":
                    builder_payload["provenance"]["project"].update(
                        {"project_id": "forged-project", "title": "forged-title"}
                    )
                elif attack == "prompt":
                    builder_payload["prompt"] = "forged prompt"
                elif attack == "validators":
                    builder_payload["validators"] = []
                elif attack == "artifact-path":
                    builder_payload["artifact_path"] = "forged/path"
                elif attack == "seed-policy":
                    builder_payload["seed_policy"].update(
                        {"version": 999, "role": "forged", "extra": True}
                    )
                elif attack == "execution-policy":
                    builder_payload["execution_policy"] = {
                        "model": "gpt-5.6-terra",
                        "reasoning_effort": "low",
                    }
                elif attack == "artifact-profile-extra":
                    builder_payload["artifact_profile"] = "byox-generic-v1"
                elif attack == "timeout":
                    builder_payload["timeout_seconds"] = 1
                elif attack == "unexpected-field":
                    builder_payload["unexpected"] = {"accepted": False}
                elif attack == "removed-field":
                    builder_payload.pop("independent_validation_required")
                elif attack == "type-change":
                    builder_payload["productionized"] = 0
                elif attack == "value-change":
                    builder_payload["retry_validation"] = False
                else:  # pragma: no cover - exhaustive tuple above
                    raise AssertionError(attack)
                self.assertEqual(
                    snapshot_sha256,
                    builder_payload["provenance"]["snapshot_sha256"],
                )
                self._rewrite_generic_base_contract(
                    project_id=project_id,
                    builder_id=builder_id,
                    review_id=review_id,
                    builder=builder,
                    review=review,
                    builder_payload=builder_payload,
                )
                before = self._publication_counts()
                self._assert_invalid_without_publication(project_id, before)

    def test_generic_builder_accepts_only_complete_released_payload_variants(self) -> None:
        project_id = "project-current-backend-payload"
        builder_id, review_id, builder, review = self._base_graph(
            project_id, "FAIL"
        )
        snapshot = {
            item.project_id: item for item in load_active_byox_projects(self.database)
        }[project_id]
        canonical = build_byox_job_spec(snapshot)
        released_payload = copy.deepcopy(canonical.payload)
        released_payload["validators"] = [
            item
            for item in released_payload["validators"]
            if item.get("name") != "byox-authoritative-code-bearing-tree"
        ]
        current_payload = with_mass_seed_backend_policy(released_payload)
        self._rewrite_generic_base_contract(
            project_id=project_id,
            builder_id=builder_id,
            review_id=review_id,
            builder=builder,
            review=review,
            builder_payload=current_payload,
        )
        result = seed_byox_remediation_jobs(
            self.database, self.jobs, warehouse=self.settings.warehouse, project_ids=[project_id]
        )
        self.assertEqual(
            "REPAIR_BUILDER_SEEDED", result["projects"][project_id]["status"]
        )

        hybrid_project = "project-partial-backend-payload"
        builder_id, review_id, builder, review = self._base_graph(
            hybrid_project, "FAIL"
        )
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM jobs WHERE job_id=?", (builder_id,)
            ).fetchone()
        assert row is not None
        hybrid_payload = json.loads(row["payload_json"])
        hybrid_payload["required_backend"] = current_payload["required_backend"]
        self._rewrite_generic_base_contract(
            project_id=hybrid_project,
            builder_id=builder_id,
            review_id=review_id,
            builder=builder,
            review=review,
            builder_payload=hybrid_payload,
        )
        before = self._publication_counts()
        self._assert_invalid_without_publication(hybrid_project, before)

    def test_generic_builder_requires_complete_canonical_job_record(self) -> None:
        attacks = (
            "job-type",
            "worker-type",
            "priority",
            "score-components",
            "max-attempts",
            "model",
            "reasoning-effort",
            "missing-dependency",
            "extra-dependency",
            "active-lease-residue",
            "retry-residue",
            "missing-started",
            "missing-finished",
            "reversed-timestamps",
            "cancel-requested",
            "failure-residue",
        )
        for index, attack in enumerate(attacks):
            with self.subTest(attack=attack):
                project_id = f"project-complete-generic-record-{index}"
                builder_id, review_id, _, _ = self._base_graph(project_id, "FAIL")
                before_tamper = self._publication_counts()
                try:
                    with self.database.transaction(immediate=True) as connection:
                        if attack == "job-type":
                            connection.execute(
                                "UPDATE jobs SET type='project_vertical_slice' WHERE job_id=?",
                                (builder_id,),
                            )
                        elif attack == "worker-type":
                            connection.execute(
                                "UPDATE jobs SET worker_type='productionizer' WHERE job_id=?",
                                (builder_id,),
                            )
                        elif attack == "priority":
                            connection.execute(
                                "UPDATE jobs SET priority=priority+1 WHERE job_id=?",
                                (builder_id,),
                            )
                        elif attack == "score-components":
                            connection.execute(
                                "UPDATE jobs SET score_components_json='{}' WHERE job_id=?",
                                (builder_id,),
                            )
                        elif attack == "max-attempts":
                            connection.execute(
                                "UPDATE jobs SET max_attempts=max_attempts+1 WHERE job_id=?",
                                (builder_id,),
                            )
                        elif attack == "model":
                            connection.execute(
                                "UPDATE jobs SET model='gpt-5.6-terra' WHERE job_id=?",
                                (builder_id,),
                            )
                        elif attack == "reasoning-effort":
                            connection.execute(
                                "UPDATE jobs SET reasoning_effort='high' WHERE job_id=?",
                                (builder_id,),
                            )
                        elif attack == "missing-dependency":
                            connection.execute(
                                "DELETE FROM job_dependencies WHERE job_id=?",
                                (builder_id,),
                            )
                        elif attack == "extra-dependency":
                            connection.execute(
                                """
                                INSERT INTO job_dependencies(job_id,depends_on_job_id)
                                VALUES (?,?)
                                """,
                                (builder_id, review_id),
                            )
                        elif attack == "active-lease-residue":
                            connection.execute(
                                """
                                UPDATE jobs
                                SET owner='forged-owner',lease_token='forged-lease',
                                    lease_expires_at=9999999999
                                WHERE job_id=?
                                """,
                                (builder_id,),
                            )
                        elif attack == "retry-residue":
                            connection.execute(
                                "UPDATE jobs SET retry_at=9999999999 WHERE job_id=?",
                                (builder_id,),
                            )
                        elif attack == "missing-started":
                            connection.execute(
                                "UPDATE jobs SET started_at=NULL WHERE job_id=?",
                                (builder_id,),
                            )
                        elif attack == "missing-finished":
                            connection.execute(
                                "UPDATE jobs SET finished_at=NULL WHERE job_id=?",
                                (builder_id,),
                            )
                        elif attack == "reversed-timestamps":
                            connection.execute(
                                "UPDATE jobs SET started_at=finished_at+1 WHERE job_id=?",
                                (builder_id,),
                            )
                        elif attack == "cancel-requested":
                            connection.execute(
                                "UPDATE jobs SET cancel_requested=1 WHERE job_id=?",
                                (builder_id,),
                            )
                        elif attack == "failure-residue":
                            connection.execute(
                                """
                                UPDATE jobs
                                SET error='forged failure',failure_kind='agent_failure'
                                WHERE job_id=?
                                """,
                                (builder_id,),
                            )
                        else:  # pragma: no cover - exhaustive tuple above
                            raise AssertionError(attack)
                except sqlite3.IntegrityError as error:
                    if attack not in {"missing-dependency", "extra-dependency"}:
                        raise
                    self.assertIn(
                        str(error),
                        {
                            "dependencies may only be added to DISCOVERED jobs",
                            "dependencies may only be removed from DISCOVERED jobs",
                        },
                    )
                    self.assertEqual(before_tamper, self._publication_counts())
                    continue
                before = self._publication_counts()
                self._assert_invalid_without_publication(project_id, before)

    def test_generic_builder_rejects_coherently_forged_impossible_attempts(self) -> None:
        for index, attempt in enumerate((0, 3, 1.5)):
            with self.subTest(attempt=attempt):
                project_id = f"project-impossible-builder-attempt-{index}"
                builder_id, _, builder, review = self._base_graph(
                    project_id, "FAIL"
                )
                self._rewrite_builder_attempt_binding(
                    builder_id=builder_id,
                    builder=builder,
                    review=review,
                    attempt=attempt,
                )
                before = self._publication_counts()
                self._assert_invalid_without_publication(project_id, before)

    def test_review_rejects_impossible_attempt_and_terminal_state(self) -> None:
        attacks = (
            "job-type",
            "worker-type",
            "model",
            "reasoning-effort",
            "attempt-zero",
            "fractional-attempt",
            "attempt-above-bound",
            "expanded-attempt-bound",
            "fractional-attempt-bound",
            "active-lease-residue",
            "reversed-timestamps",
            "cancel-requested",
            "failure-residue",
        )
        for index, attack in enumerate(attacks):
            with self.subTest(attack=attack):
                project_id = f"project-impossible-review-state-{index}"
                _, review_id, _, review = self._base_graph(project_id, "FAIL")
                if attack in {
                    "job-type",
                    "worker-type",
                    "model",
                    "reasoning-effort",
                }:
                    statement, value = {
                        "job-type": (
                            "UPDATE jobs SET type=? WHERE job_id=?",
                            "project_vertical_slice",
                        ),
                        "worker-type": (
                            "UPDATE jobs SET worker_type=? WHERE job_id=?",
                            "reference_builder",
                        ),
                        "model": (
                            "UPDATE jobs SET model=? WHERE job_id=?",
                            "gpt-5.6-terra",
                        ),
                        "reasoning-effort": (
                            "UPDATE jobs SET reasoning_effort=? WHERE job_id=?",
                            "high",
                        ),
                    }[attack]
                    with self.database.transaction(immediate=True) as connection:
                        connection.execute(
                            statement,
                            (value, review_id),
                        )
                elif attack == "attempt-zero":
                    self._rewrite_review_attempt_binding(
                        review_id=review_id,
                        review=review,
                        attempt=0,
                    )
                elif attack == "fractional-attempt":
                    self._rewrite_review_attempt_binding(
                        review_id=review_id,
                        review=review,
                        attempt=1.5,
                    )
                elif attack == "attempt-above-bound":
                    self._rewrite_review_attempt_binding(
                        review_id=review_id,
                        review=review,
                        attempt=3,
                    )
                elif attack == "expanded-attempt-bound":
                    self._rewrite_review_attempt_binding(
                        review_id=review_id,
                        review=review,
                        attempt=3,
                        max_attempts=3,
                    )
                elif attack == "fractional-attempt-bound":
                    self._rewrite_review_attempt_binding(
                        review_id=review_id,
                        review=review,
                        attempt=1,
                        max_attempts=1.5,
                    )
                else:
                    with self.database.transaction(immediate=True) as connection:
                        if attack == "active-lease-residue":
                            connection.execute(
                                """
                                UPDATE jobs
                                SET owner='forged-owner',lease_token='forged-lease',
                                    lease_expires_at=9999999999
                                WHERE job_id=?
                                """,
                                (review_id,),
                            )
                        elif attack == "reversed-timestamps":
                            connection.execute(
                                """
                                UPDATE jobs SET started_at=finished_at+1
                                WHERE job_id=?
                                """,
                                (review_id,),
                            )
                        elif attack == "cancel-requested":
                            connection.execute(
                                """
                                UPDATE jobs SET cancel_requested=1 WHERE job_id=?
                                """,
                                (review_id,),
                            )
                        elif attack == "failure-residue":
                            connection.execute(
                                """
                                UPDATE jobs
                                SET error='forged failure',
                                    failure_kind='validation_failure'
                                WHERE job_id=?
                                """,
                                (review_id,),
                            )
                        else:  # pragma: no cover - exhaustive tuple above
                            raise AssertionError(attack)
                before = self._publication_counts()
                self._assert_invalid_without_publication(project_id, before)

    def test_retried_builder_and_reviewer_accept_current_bounded_attempt(self) -> None:
        project_id = "project-valid-second-attempt"
        builder_id, review_id, builder, review = self._base_graph(
            project_id, "FAIL"
        )
        self._rewrite_builder_attempt_binding(
            builder_id=builder_id,
            builder=builder,
            review=review,
            attempt=2,
        )
        self._rewrite_review_attempt_binding(
            review_id=review_id,
            review=review,
            attempt=2,
        )

        result = seed_byox_remediation_jobs(
            self.database, self.jobs, warehouse=self.settings.warehouse, project_ids=[project_id]
        )

        self.assertEqual(1, result["created_jobs"])
        self.assertEqual(
            "REPAIR_BUILDER_SEEDED", result["projects"][project_id]["status"]
        )

    def test_generic_builder_snapshot_must_match_the_current_catalog(self) -> None:
        stale_project = "project-stale-catalog-snapshot"
        self._base_graph(stale_project, "FAIL")
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                "UPDATE sources SET commit_hash='new-catalog-commit' WHERE source_id='source_byox'"
            )
        before = self._publication_counts()
        self._assert_invalid_without_publication(stale_project, before)

        current_project = "project-current-catalog-snapshot"
        self._base_graph(current_project, "FAIL")
        result = seed_byox_remediation_jobs(
            self.database, self.jobs, warehouse=self.settings.warehouse, project_ids=[current_project]
        )
        self.assertEqual(
            "REPAIR_BUILDER_SEEDED", result["projects"][current_project]["status"]
        )

    def test_stale_detached_loader_cannot_override_transaction_snapshot(self) -> None:
        project_id = "project-detached-stale-loader"
        self._base_graph(project_id, "FAIL")
        stale = load_active_byox_projects(self.database)
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                """
                UPDATE sources SET commit_hash='new-catalog-commit'
                WHERE source_id='source_byox'
                """
            )

        before = self._publication_counts()
        # This is the exact detached-wrapper seam used by the old implementation:
        # it returned a snapshot captured before BEGIN IMMEDIATE.  The repaired
        # seeder does not consult that API and reads current rows on its held
        # transaction connection instead.
        with patch.object(
            remediation_module,
            "load_active_byox_projects",
            return_value=stale,
            create=True,
        ) as detached_loader:
            result = seed_byox_remediation_jobs(
                self.database, self.jobs, warehouse=self.settings.warehouse, project_ids=[project_id]
            )

        detached_loader.assert_not_called()
        self.assertEqual(0, result["created_jobs"])
        self.assertEqual(
            "REMEDIATION_EVIDENCE_INVALID",
            result["projects"][project_id]["status"],
        )
        self.assertEqual(before, self._publication_counts())
        self.assertIsNone(self.jobs.get(repair_builder_job_id(project_id, 1)))

    def test_catalog_writer_cannot_interleave_snapshot_and_publication(self) -> None:
        project_id = "project-transaction-lock"
        self._base_graph(project_id, "FAIL")
        scoped_loader = remediation_module.load_active_byox_projects_from_connection
        second_connection_was_locked: list[bool] = []

        def probe_write_lock(connection: sqlite3.Connection):
            self.assertTrue(connection.in_transaction)
            contender = sqlite3.connect(
                self.database.path,
                isolation_level=None,
                timeout=0,
            )
            try:
                contender.execute("PRAGMA busy_timeout=0")
                with self.assertRaisesRegex(sqlite3.OperationalError, "locked"):
                    contender.execute("BEGIN IMMEDIATE")
                second_connection_was_locked.append(True)
            finally:
                if contender.in_transaction:
                    contender.rollback()
                contender.close()
            return scoped_loader(connection)

        with patch.object(
            remediation_module,
            "load_active_byox_projects_from_connection",
            side_effect=probe_write_lock,
        ):
            first = seed_byox_remediation_jobs(
                self.database, self.jobs, warehouse=self.settings.warehouse, project_ids=[project_id]
            )

        self.assertEqual([True], second_connection_was_locked)
        self.assertEqual(1, first["created_jobs"])
        self.assertEqual(
            "REPAIR_BUILDER_SEEDED", first["projects"][project_id]["status"]
        )

        # Once the transaction commits a real second connection may update the
        # source.  The existing repair is then stale, and no further job/event or
        # dependency may be published from it.
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                """
                UPDATE sources SET commit_hash='post-publication-commit'
                WHERE source_id='source_byox'
                """
            )
        before = self._publication_counts()
        second = seed_byox_remediation_jobs(
            self.database, self.jobs, warehouse=self.settings.warehouse, project_ids=[project_id]
        )
        self.assertEqual(0, second["created_jobs"])
        self.assertEqual(
            "REMEDIATION_EVIDENCE_INVALID",
            second["projects"][project_id]["status"],
        )
        self.assertEqual(before, self._publication_counts())

    def test_transaction_snapshot_selection_is_filtered_bounded_and_idempotent(
        self,
    ) -> None:
        project_ids = (
            "project-selection-a",
            "project-selection-b",
            "project-selection-c",
        )
        for project_id in project_ids:
            self._base_graph(project_id, "REVISE")

        before = self._publication_counts()
        first = seed_byox_remediation_jobs(
            self.database,
            self.jobs,
            warehouse=self.settings.warehouse,
            project_ids=[project_ids[2], project_ids[1]],
            max_projects=1,
        )
        self.assertEqual(2, first["available_active_projects"])
        self.assertEqual(1, first["active_projects"])
        self.assertEqual({project_ids[1]}, set(first["projects"]))
        self.assertEqual(1, first["created_jobs"])
        self.assertIsNone(self.jobs.get(repair_builder_job_id(project_ids[0], 1)))
        self.assertIsNotNone(self.jobs.get(repair_builder_job_id(project_ids[1], 1)))
        self.assertIsNone(self.jobs.get(repair_builder_job_id(project_ids[2], 1)))
        after_first = self._publication_counts()
        self.assertEqual(
            (before[0] + 1, before[1] + 3, before[2] + 1),
            after_first,
        )

        again = seed_byox_remediation_jobs(
            self.database,
            self.jobs,
            warehouse=self.settings.warehouse,
            project_ids=[project_ids[2], project_ids[1]],
            max_projects=1,
        )
        self.assertEqual(0, again["created_jobs"])
        self.assertEqual(
            "WAITING_FOR_REPAIR_BUILDER",
            again["projects"][project_ids[1]]["status"],
        )
        self.assertEqual(after_first, self._publication_counts())

    def _assert_specialized_builder_full_spec_fence(
        self,
        *,
        project_id: str,
        builder_id: str,
        artifact_type: str,
        historical_attempt: int,
    ) -> None:
        builder_id, review_id, builder, review = self._base_graph(
            project_id,
            "FAIL",
            builder_artifact_type=artifact_type,
            specialized_builder_job_id=builder_id,
            builder_attempt=historical_attempt,
        )
        snapshots = load_active_byox_projects(self.database)
        spec = specialized_byox_job_specs_by_id(snapshots)[builder_id]
        with self.database.connect() as connection:
            baseline_job = dict(
                connection.execute(
                    """
                    SELECT type,worker_type,state,priority,score_components_json,
                           payload_json,attempt_count,max_attempts,owner,lease_token,
                           lease_expires_at,heartbeat_at,retry_at,created_at,started_at,
                           finished_at,error,failure_kind,workspace,cancel_requested,
                           model,reasoning_effort
                    FROM jobs WHERE job_id=?
                    """,
                    (builder_id,),
                ).fetchone()
            )
            baseline_dependencies = tuple(
                row["depends_on_job_id"]
                for row in connection.execute(
                    """
                    SELECT depends_on_job_id FROM job_dependencies
                    WHERE job_id=? ORDER BY depends_on_job_id
                    """,
                    (builder_id,),
                )
            )
            baseline_artifact = dict(connection.execute(
                "SELECT attempt_number,path,metadata_json FROM artifacts WHERE artifact_id=?",
                (builder["artifact_id"],),
            ).fetchone())
            baseline_validation_attempts = tuple(
                (row["validation_id"], row["attempt_number"])
                for row in connection.execute(
                    "SELECT validation_id,attempt_number FROM validations WHERE job_id=?",
                    (builder_id,),
                )
            )
            baseline_labels = tuple(
                (row["label"], row["evidence_json"])
                for row in connection.execute(
                    """
                    SELECT label,evidence_json FROM artifact_validation_labels
                    WHERE artifact_id=? ORDER BY label
                    """,
                    (builder["artifact_id"],),
                )
            )
            baseline_review_payload = connection.execute(
                "SELECT payload_json FROM jobs WHERE job_id=?",
                (review_id,),
            ).fetchone()["payload_json"]
            baseline_review_metadata = connection.execute(
                "SELECT metadata_json FROM artifacts WHERE artifact_id=?",
                (review["artifact_id"],),
            ).fetchone()["metadata_json"]
            source = connection.execute(
                """
                SELECT s.source_id,s.commit_hash
                FROM build_projects p JOIN sources s ON s.source_id=p.source_id
                WHERE p.project_id=?
                """,
                (project_id,),
            ).fetchone()
            assert source is not None
            source_id = source["source_id"]
            baseline_source_commit = source["commit_hash"]

        self.assertEqual(spec.job_type, baseline_job["type"])
        self.assertEqual(spec.worker_type, baseline_job["worker_type"])
        self.assertEqual(spec.priority, baseline_job["priority"])
        self.assertEqual(
            canonical_json(spec.score_components),
            baseline_job["score_components_json"],
        )
        self.assertEqual(canonical_json(spec.payload), baseline_job["payload_json"])
        self.assertEqual(spec.max_attempts, baseline_job["max_attempts"])
        self.assertEqual(spec.model, baseline_job["model"])
        self.assertEqual(spec.reasoning_effort, baseline_job["reasoning_effort"])
        self.assertEqual(tuple(sorted(spec.dependencies)), baseline_dependencies)
        self.assertEqual(historical_attempt, baseline_job["attempt_count"])

        job_columns = tuple(baseline_job)

        def restore() -> None:
            with self.database.transaction(immediate=True) as connection:
                current_artifact = connection.execute(
                    "SELECT path FROM artifacts WHERE artifact_id=?",
                    (builder["artifact_id"],),
                ).fetchone()
                assert current_artifact is not None
                current_path = Path(str(current_artifact["path"]))
                baseline_path = Path(str(baseline_artifact["path"]))
                if current_path != baseline_path and current_path.exists():
                    current_path.rename(baseline_path)
                assignments = ",".join(f'"{column}"=?' for column in job_columns)
                connection.execute(
                    f'UPDATE jobs SET {assignments} WHERE job_id=?',
                    (*[baseline_job[column] for column in job_columns], builder_id),
                )
                current_dependencies = tuple(
                    row["depends_on_job_id"]
                    for row in connection.execute(
                        """
                        SELECT depends_on_job_id FROM job_dependencies
                        WHERE job_id=? ORDER BY depends_on_job_id
                        """,
                        (builder_id,),
                    )
                )
                if current_dependencies != baseline_dependencies:
                    connection.execute(
                        "DELETE FROM job_dependencies WHERE job_id=?",
                        (builder_id,),
                    )
                    for dependency in baseline_dependencies:
                        connection.execute(
                            """
                            INSERT INTO job_dependencies(job_id,depends_on_job_id)
                            VALUES (?,?)
                            """,
                            (builder_id, dependency),
                        )
                connection.execute(
                    "UPDATE artifacts SET attempt_number=?,path=?,metadata_json=? WHERE artifact_id=?",
                    (
                        baseline_artifact["attempt_number"],
                        baseline_artifact["path"],
                        baseline_artifact["metadata_json"],
                        builder["artifact_id"],
                    ),
                )
                for validation_id, attempt_number in baseline_validation_attempts:
                    connection.execute(
                        "UPDATE validations SET attempt_number=? WHERE validation_id=?",
                        (attempt_number, validation_id),
                    )
                for label, evidence_json in baseline_labels:
                    connection.execute(
                        """
                        UPDATE artifact_validation_labels SET evidence_json=?
                        WHERE artifact_id=? AND label=?
                        """,
                        (evidence_json, builder["artifact_id"], label),
                    )
                connection.execute(
                    "UPDATE jobs SET payload_json=? WHERE job_id=?",
                    (baseline_review_payload, review_id),
                )
                connection.execute(
                    "UPDATE artifacts SET metadata_json=? WHERE artifact_id=?",
                    (baseline_review_metadata, review["artifact_id"]),
                )
                connection.execute(
                    "UPDATE sources SET commit_hash=? WHERE source_id=?",
                    (baseline_source_commit, source_id),
                )

        attacks = (
            "job-type",
            "worker-type",
            "priority",
            "score-components",
            "max-attempts",
            "model",
            "reasoning-effort",
            "dependencies",
            "payload-extra",
            "payload-missing",
            "payload-value",
            "payload-type",
            "persisted-artifact-type",
            "attempt-zero",
            "attempt-over-bound",
            "attempt-float",
            "owner-residue",
            "lease-residue",
            "expiry-residue",
            "retry-residue",
            "error-residue",
            "failure-residue",
            "cancel-residue",
            "missing-started",
            "missing-finished",
            "nonfinite-created",
            "nonfinite-started",
            "nonfinite-finished",
            "reversed-created",
            "reversed-started",
            "reversed-finished",
            "source-revision",
        )
        baseline_counts = self._publication_counts()
        for attack in attacks:
            with self.subTest(builder_id=builder_id, attack=attack):
                if attack in {
                    "payload-extra",
                    "payload-missing",
                    "payload-value",
                    "payload-type",
                    "persisted-artifact-type",
                }:
                    payload = copy.deepcopy(spec.payload)
                    if attack == "payload-extra":
                        payload["arbitrary_extra"] = "forged"
                    elif attack == "payload-missing":
                        payload.pop("validation_status")
                    elif attack == "payload-value":
                        payload["validation_status"] = "FORGED"
                    elif attack == "payload-type":
                        payload["project_id"] = [project_id]
                    else:
                        payload["artifact_type"] = artifact_type
                    self._rewrite_specialized_base_contract(
                        project_id=project_id,
                        builder_id=builder_id,
                        review_id=review_id,
                        builder=builder,
                        review=review,
                        builder_payload=payload,
                        artifact_type=artifact_type,
                    )
                elif attack in {
                    "attempt-zero",
                    "attempt-over-bound",
                    "attempt-float",
                }:
                    attempt: int | float = {
                        "attempt-zero": 0,
                        "attempt-over-bound": spec.max_attempts + 1,
                        "attempt-float": 1.5,
                    }[attack]
                    self._rewrite_builder_attempt_binding(
                        builder_id=builder_id,
                        builder=builder,
                        review=review,
                        attempt=attempt,
                    )
                elif attack == "dependencies":
                    try:
                        with self.database.transaction(immediate=True) as connection:
                            if spec.dependencies:
                                connection.execute(
                                    """
                                    DELETE FROM job_dependencies
                                    WHERE job_id=? AND depends_on_job_id=?
                                    """,
                                    (builder_id, spec.dependencies[0]),
                                )
                            else:
                                connection.execute(
                                    """
                                    INSERT INTO job_dependencies(job_id,depends_on_job_id)
                                    VALUES (?,?)
                                    """,
                                    (builder_id, CODEX_BACKEND_GATE_JOB_ID),
                                )
                    except sqlite3.IntegrityError as error:
                        self.assertIn(
                            str(error),
                            {
                                "dependencies may only be added to DISCOVERED jobs",
                                "dependencies may only be removed from DISCOVERED jobs",
                            },
                        )
                        self.assertEqual(
                            baseline_counts,
                            self._publication_counts(),
                        )
                        continue
                elif attack == "source-revision":
                    with self.database.transaction(immediate=True) as connection:
                        connection.execute(
                            "UPDATE sources SET commit_hash=? WHERE source_id=?",
                            ("revised-source-commit", source_id),
                        )
                else:
                    statement, parameters = {
                        "job-type": (
                            "UPDATE jobs SET type='codex_task' WHERE job_id=?",
                            (),
                        ),
                        "worker-type": (
                            "UPDATE jobs SET worker_type='student' WHERE job_id=?",
                            (),
                        ),
                        "priority": (
                            "UPDATE jobs SET priority=priority+123 WHERE job_id=?",
                            (),
                        ),
                        "score-components": (
                            "UPDATE jobs SET score_components_json='{}' WHERE job_id=?",
                            (),
                        ),
                        "max-attempts": (
                            "UPDATE jobs SET max_attempts=? WHERE job_id=?",
                            (spec.max_attempts + 1,),
                        ),
                        "model": (
                            "UPDATE jobs SET model='gpt-5.6-terra' WHERE job_id=?",
                            (),
                        ),
                        "reasoning-effort": (
                            "UPDATE jobs SET reasoning_effort='low' WHERE job_id=?",
                            (),
                        ),
                        "owner-residue": (
                            "UPDATE jobs SET owner='forged-owner' WHERE job_id=?",
                            (),
                        ),
                        "lease-residue": (
                            "UPDATE jobs SET lease_token='forged-lease' WHERE job_id=?",
                            (),
                        ),
                        "expiry-residue": (
                            "UPDATE jobs SET lease_expires_at=9999999999 WHERE job_id=?",
                            (),
                        ),
                        "retry-residue": (
                            "UPDATE jobs SET retry_at=9999999999 WHERE job_id=?",
                            (),
                        ),
                        "error-residue": (
                            "UPDATE jobs SET error='forged error' WHERE job_id=?",
                            (),
                        ),
                        "failure-residue": (
                            "UPDATE jobs SET failure_kind='agent_failure' WHERE job_id=?",
                            (),
                        ),
                        "cancel-residue": (
                            "UPDATE jobs SET cancel_requested=1 WHERE job_id=?",
                            (),
                        ),
                        "missing-started": (
                            "UPDATE jobs SET started_at=NULL WHERE job_id=?",
                            (),
                        ),
                        "missing-finished": (
                            "UPDATE jobs SET finished_at=NULL WHERE job_id=?",
                            (),
                        ),
                        "nonfinite-created": (
                            "UPDATE jobs SET created_at=? WHERE job_id=?",
                            (float("inf"),),
                        ),
                        "nonfinite-started": (
                            "UPDATE jobs SET started_at=? WHERE job_id=?",
                            (float("inf"),),
                        ),
                        "nonfinite-finished": (
                            "UPDATE jobs SET finished_at=? WHERE job_id=?",
                            (float("inf"),),
                        ),
                        "reversed-created": (
                            "UPDATE jobs SET created_at=started_at+1 WHERE job_id=?",
                            (),
                        ),
                        "reversed-started": (
                            "UPDATE jobs SET started_at=finished_at+1 WHERE job_id=?",
                            (),
                        ),
                        "reversed-finished": (
                            "UPDATE jobs SET finished_at=started_at-1 WHERE job_id=?",
                            (),
                        ),
                    }[attack]
                    with self.database.transaction(immediate=True) as connection:
                        connection.execute(statement, (*parameters, builder_id))

                before_seed = self._publication_counts()
                result = seed_byox_remediation_jobs(
                    self.database,
                    self.jobs,
                    warehouse=self.settings.warehouse,
                    project_ids=[project_id],
                )
                self.assertEqual(0, result["created_jobs"])
                self.assertEqual(
                    "REMEDIATION_EVIDENCE_INVALID",
                    result["projects"][project_id]["status"],
                )
                self.assertEqual(before_seed, self._publication_counts())
                self.assertIsNone(
                    self.jobs.get(repair_builder_job_id(project_id, 1))
                )
                restore()
                self.assertEqual(baseline_counts, self._publication_counts())

        before_valid = self._publication_counts()
        valid = seed_byox_remediation_jobs(
            self.database,
            self.jobs,
            warehouse=self.settings.warehouse,
            project_ids=[project_id],
        )
        self.assertEqual(1, valid["created_jobs"])
        self.assertEqual(
            "REPAIR_BUILDER_SEEDED",
            valid["projects"][project_id]["status"],
        )
        self.assertEqual(
            (before_valid[0] + 1, before_valid[1] + 3, before_valid[2] + 1),
            self._publication_counts(),
        )
        after_valid = self._publication_counts()
        repeated = seed_byox_remediation_jobs(
            self.database,
            self.jobs,
            warehouse=self.settings.warehouse,
            project_ids=[project_id],
        )
        self.assertEqual(0, repeated["created_jobs"])
        self.assertEqual(
            "WAITING_FOR_REPAIR_BUILDER",
            repeated["projects"][project_id]["status"],
        )
        self.assertEqual(after_valid, self._publication_counts())

    def test_kv_v1_specialized_builder_without_validation_is_quarantined(self) -> None:
        project_id = "project-specialized-kv-v1"
        self._base_graph(
            project_id,
            "FAIL",
            builder_artifact_type="project_challenge_pack",
            specialized_builder_job_id=KVSTORE_JOB_ID,
        )
        before = self._publication_counts()
        result = seed_byox_remediation_jobs(
            self.database,
            self.jobs,
            warehouse=self.settings.warehouse,
            project_ids=[project_id],
        )
        self.assertEqual(0, result["created_jobs"])
        self.assertEqual(
            "REMEDIATION_EVIDENCE_INVALID",
            result["projects"][project_id]["status"],
        )
        self.assertEqual(before, self._publication_counts())

    def test_kv_v2_specialized_builder_requires_complete_released_spec(self) -> None:
        self._assert_specialized_builder_full_spec_fence(
            project_id="project-specialized-kv-v2",
            builder_id=KVSTORE_REVISION_JOB_ID,
            artifact_type="project_challenge_pack",
            historical_attempt=1,
        )

    def test_http_specialized_builder_requires_complete_released_spec(self) -> None:
        self._assert_specialized_builder_full_spec_fence(
            project_id="project-specialized-http",
            builder_id=HTTP_SERVICE_JOB_ID,
            artifact_type="http_service_challenge_pack",
            historical_attempt=1,
        )

    def test_allocator_specialized_builder_requires_complete_released_spec(
        self,
    ) -> None:
        self._assert_specialized_builder_full_spec_fence(
            project_id=ALLOCATOR_PROJECT_ID,
            builder_id=ALLOCATOR_JOB_ID,
            artifact_type="allocator_challenge_pack",
            historical_attempt=2,
        )

    def test_bytecode_specialized_builder_requires_complete_released_spec(
        self,
    ) -> None:
        self._assert_specialized_builder_full_spec_fence(
            project_id=BYTECODE_PROJECT_ID,
            builder_id=BYTECODE_JOB_ID,
            artifact_type="bytecode_vm_challenge_pack",
            historical_attempt=2,
        )

    def test_arbitrary_specialized_builder_identity_publishes_nothing(self) -> None:
        project_id = "project_4b7f4b85b17b06eeba75d235767a898f"
        self._base_graph(
            project_id,
            "FAIL",
            builder_artifact_type="bytecode_vm_challenge_pack",
            specialized_builder_job_id="job_arbitrary_specialized_builder",
        )
        before = self._publication_counts()
        self._assert_invalid_without_publication(project_id, before)

    def test_catalog_bound_specialized_builder_accepts_backed_nonterminal_status(self) -> None:
        project_id = "project_4b7f4b85b17b06eeba75d235767a898f"
        builder_id, _, _, _ = self._base_graph(
            project_id,
            "FAIL",
            builder_artifact_type="bytecode_vm_challenge_pack",
        )
        with self.database.connect() as connection:
            status = connection.execute(
                "SELECT validation_status FROM artifacts WHERE job_id=?",
                (builder_id,),
            ).fetchone()["validation_status"]
        self.assertIn("TESTED", status.split("+"))
        self.assertIn("PARTIAL", status.split("+"))
        self.assertNotIn("PRODUCTIONIZED", status.split("+"))
        result = seed_byox_remediation_jobs(
            self.database, self.jobs, warehouse=self.settings.warehouse, project_ids=[project_id]
        )
        self.assertEqual(
            "REPAIR_BUILDER_SEEDED", result["projects"][project_id]["status"]
        )

    def test_builder_snapshot_rejects_deleted_mutated_and_aliased_archives(self) -> None:
        for attack in (
            "deleted-root",
            "mutated-file",
            "symlinked-file",
            "hardlinked-file",
            "special-file",
            "root-symlink",
            "root-replacement",
        ):
            project_id = f"project-builder-tree-{attack}"
            with self.subTest(attack=attack):
                builder_id, _, _, _ = self._base_graph(project_id, "FAIL")
                with self.database.connect() as connection:
                    root = Path(
                        connection.execute(
                            "SELECT path FROM artifacts WHERE job_id=?",
                            (builder_id,),
                        ).fetchone()["path"]
                    )
                readme = root / "README.md"
                if attack == "deleted-root":
                    shutil.rmtree(root)
                elif attack == "mutated-file":
                    readme.write_text("mutated after verification\n", encoding="utf-8")
                elif attack == "symlinked-file":
                    readme.unlink()
                    readme.symlink_to("MANIFEST.yaml")
                elif attack == "hardlinked-file":
                    readme.unlink()
                    os.link(root / "MANIFEST.yaml", readme)
                elif attack == "special-file":
                    readme.unlink()
                    os.mkfifo(readme)
                elif attack == "root-symlink":
                    displaced = root.with_name(f"{root.name}-displaced")
                    root.rename(displaced)
                    root.symlink_to(displaced, target_is_directory=True)
                else:
                    displaced = root.with_name(f"{root.name}-displaced")
                    root.rename(displaced)
                    root.mkdir()

                before = self._publication_counts()
                self._assert_invalid_without_publication(project_id, before)

    def test_builder_snapshot_rejects_checksum_sandwich_without_publication(self) -> None:
        project_id = "project-builder-checksum-sandwich"
        builder_id, _, _, _ = self._base_graph(project_id, "FAIL")
        with self.database.connect() as connection:
            root = Path(
                connection.execute(
                    "SELECT path FROM artifacts WHERE job_id=?", (builder_id,)
                ).fetchone()["path"]
            )
        target = root / "README.md"
        original = target.read_bytes()
        real_read = os.read
        raced = False

        def sandwich_read(descriptor: int, size: int) -> bytes:
            nonlocal raced
            try:
                opened = Path(os.readlink(f"/proc/self/fd/{descriptor}"))
            except OSError:
                opened = Path("/")
            if not raced and opened == target:
                raced = True
                target.write_bytes(b"Y" * len(original))
                chunk = real_read(descriptor, size)
                target.write_bytes(original)
                return chunk
            return real_read(descriptor, size)

        before = self._publication_counts()
        with patch(
            "learnfactory.byox_remediation.os.read",
            side_effect=sandwich_read,
        ):
            self._assert_invalid_without_publication(project_id, before)
        self.assertTrue(raced)

    def test_builder_snapshot_rejects_root_swap_during_read(self) -> None:
        project_id = "project-builder-root-swap"
        builder_id, _, _, _ = self._base_graph(project_id, "FAIL")
        with self.database.connect() as connection:
            root = Path(
                connection.execute(
                    "SELECT path FROM artifacts WHERE job_id=?", (builder_id,)
                ).fetchone()["path"]
            )
        target = root / "README.md"
        real_read = os.read
        raced = False

        def swap_root(descriptor: int, size: int) -> bytes:
            nonlocal raced
            try:
                opened = Path(os.readlink(f"/proc/self/fd/{descriptor}"))
            except OSError:
                opened = Path("/")
            if not raced and opened == target:
                raced = True
                displaced = root.with_name(f"{root.name}-displaced-during-read")
                root.rename(displaced)
                root.mkdir()
            return real_read(descriptor, size)

        before = self._publication_counts()
        with patch(
            "learnfactory.byox_remediation.os.read",
            side_effect=swap_root,
        ):
            self._assert_invalid_without_publication(project_id, before)
        self.assertTrue(raced)

    def test_matching_artifacts_outside_managed_root_publish_nothing(self) -> None:
        for owner, symlink_escape in (
            ("builder", False),
            ("review", False),
            ("builder", True),
            ("review", True),
        ):
            suffix = f"{owner}-{'symlink' if symlink_escape else 'outside'}"
            project_id = f"project-managed-boundary-{suffix}"
            with self.subTest(owner=owner, symlink_escape=symlink_escape):
                builder_id, review_id, _, _ = self._base_graph(project_id, "FAIL")
                owner_id = builder_id if owner == "builder" else review_id
                with self.database.connect() as connection:
                    row = connection.execute(
                        "SELECT path,checksum FROM artifacts WHERE job_id=?",
                        (owner_id,),
                    ).fetchone()
                original = Path(row["path"])
                outside = self.root / "outside-artifacts" / suffix / "attempt-001"
                outside.parent.mkdir(parents=True)
                shutil.copytree(original, outside)
                self.assertEqual(row["checksum"], tree_sha256(outside))

                attacked_path = outside
                if symlink_escape:
                    managed = self.settings.database.parent / "artifacts"
                    alias = managed / f"escape-{suffix}"
                    alias.symlink_to(outside.parent, target_is_directory=True)
                    attacked_path = alias / outside.name
                with self.database.transaction(immediate=True) as connection:
                    connection.execute(
                        "UPDATE artifacts SET path=? WHERE job_id=?",
                        (str(attacked_path), owner_id),
                    )
                before = self._publication_counts()
                self._assert_invalid_without_publication(project_id, before)

    def test_builder_and_review_binding_mismatches_publish_nothing(self) -> None:
        attacks = (
            "builder-artifact-type",
            "builder-checksum",
            "builder-algorithm",
            "builder-integrity",
            "builder-payload-type",
            "builder-attempt",
            "review-artifact-type",
            "staged-artifact-id",
            "staged-checksum",
            "staged-algorithm",
            "staged-attempt",
            "staged-type",
            "extra-current-artifact",
        )
        for attack in attacks:
            project_id = f"project-binding-{attack}"
            with self.subTest(attack=attack):
                builder_id, review_id, _, review = self._base_graph(
                    project_id, "FAIL"
                )
                with self.database.transaction(immediate=True) as connection:
                    if attack == "builder-artifact-type":
                        connection.execute(
                            "UPDATE artifacts SET type='project_challenge_pack' WHERE job_id=?",
                            (builder_id,),
                        )
                    elif attack == "builder-checksum":
                        connection.execute(
                            "UPDATE artifacts SET checksum=? WHERE job_id=?",
                            ("0" * 64, builder_id),
                        )
                    elif attack == "builder-algorithm":
                        connection.execute(
                            "UPDATE artifacts SET checksum_algorithm='tree-sha256-v1' WHERE job_id=?",
                            (builder_id,),
                        )
                    elif attack == "builder-integrity":
                        connection.execute(
                            "UPDATE artifacts SET integrity_status='LEGACY_UNVERIFIED' WHERE job_id=?",
                            (builder_id,),
                        )
                    elif attack == "builder-payload-type":
                        row = connection.execute(
                            "SELECT payload_json FROM jobs WHERE job_id=?", (builder_id,)
                        ).fetchone()
                        payload = json.loads(row["payload_json"])
                        payload["artifact_type"] = "project_challenge_pack"
                        connection.execute(
                            "UPDATE jobs SET payload_json=? WHERE job_id=?",
                            (canonical_json(payload), builder_id),
                        )
                    elif attack == "builder-attempt":
                        connection.execute(
                            "UPDATE jobs SET attempt_count=2 WHERE job_id=?",
                            (builder_id,),
                        )
                    elif attack == "review-artifact-type":
                        connection.execute(
                            "UPDATE artifacts SET type='forged-review' WHERE job_id=?",
                            (review_id,),
                        )
                    elif attack == "extra-current-artifact":
                        connection.execute(
                            """
                            INSERT INTO artifacts(
                                artifact_id,job_id,type,path,checksum,metadata_json,
                                created_at,validation_status,attempt_number,
                                checksum_algorithm,integrity_status
                            )
                            SELECT artifact_id || '-extra',job_id,'extra-artifact',path,checksum,
                                   metadata_json,created_at + 0.001,
                                   validation_status,attempt_number,
                                   checksum_algorithm,integrity_status
                            FROM artifacts WHERE job_id=?
                            """,
                            (builder_id,),
                        )
                    else:
                        row = connection.execute(
                            "SELECT metadata_json FROM artifacts WHERE artifact_id=?",
                            (review["artifact_id"],),
                        ).fetchone()
                        metadata = json.loads(row["metadata_json"])
                        staged = metadata["staged_inputs"][0]
                        field, value = {
                            "staged-artifact-id": ("artifact_id", "artifact-forged"),
                            "staged-checksum": ("artifact_checksum", "1" * 64),
                            "staged-algorithm": (
                                "artifact_checksum_algorithm",
                                "tree-sha256-v1",
                            ),
                            "staged-attempt": ("artifact_attempt", 2),
                            "staged-type": ("artifact_type", "project_challenge_pack"),
                        }[attack]
                        staged[field] = value
                        connection.execute(
                            "UPDATE artifacts SET metadata_json=? WHERE artifact_id=?",
                            (canonical_json(metadata), review["artifact_id"]),
                        )
                before = self._publication_counts()
                self._assert_invalid_without_publication(project_id, before)

    def test_review_dependency_and_payload_deformations_publish_nothing(self) -> None:
        extra_dependency_id = "job_review_contract_extra_dependency"
        self._insert_finished_job(
            extra_dependency_id,
            {"artifact_type": "unrelated"},
            artifact_type="unrelated",
            files={"UNRELATED.txt": "unrelated\n"},
            worker_type="maintenance",
        )
        attacks = (
            "missing-gate-dependency",
            "missing-builder-dependency",
            "extra-dependency",
            "empty-mappings",
            "missing-mapping",
            "extra-mapping",
            "wrong-destination",
            "wrong-subpath",
            "wrong-artifact-expectation",
            "unprotected-candidate",
            "direct-inputs",
            "extra-payload-field",
            "missing-staged-selection",
            "unrelated-staged-selection",
        )
        for attack in attacks:
            project_id = f"project-contract-deformation-{attack}"
            with self.subTest(attack=attack):
                builder_id, review_id, _, review = self._base_graph(
                    project_id, "FAIL"
                )
                if attack in {
                    "missing-gate-dependency",
                    "missing-builder-dependency",
                    "extra-dependency",
                }:
                    before_tamper = self._publication_counts()
                    try:
                        with self.database.transaction(immediate=True) as connection:
                            if attack == "missing-gate-dependency":
                                connection.execute(
                                    """
                                    DELETE FROM job_dependencies
                                    WHERE job_id=? AND depends_on_job_id=?
                                    """,
                                    (review_id, CODEX_BACKEND_GATE_JOB_ID),
                                )
                            elif attack == "missing-builder-dependency":
                                connection.execute(
                                    """
                                    DELETE FROM job_dependencies
                                    WHERE job_id=? AND depends_on_job_id=?
                                    """,
                                    (review_id, builder_id),
                                )
                            else:
                                connection.execute(
                                    """
                                    INSERT INTO job_dependencies(
                                        job_id,depends_on_job_id
                                    ) VALUES (?,?)
                                    """,
                                    (review_id, extra_dependency_id),
                                )
                    except sqlite3.IntegrityError as error:
                        self.assertIn(
                            str(error),
                            {
                                "dependencies may only be added to DISCOVERED jobs",
                                "dependencies may only be removed from DISCOVERED jobs",
                            },
                        )
                        self.assertEqual(
                            before_tamper,
                            self._publication_counts(),
                        )
                        continue
                    before = self._publication_counts()
                    self._assert_invalid_without_publication(project_id, before)
                    continue
                with self.database.transaction(immediate=True) as connection:
                    if attack in {
                        "missing-staged-selection",
                        "unrelated-staged-selection",
                    }:
                        row = connection.execute(
                            "SELECT metadata_json FROM artifacts WHERE artifact_id=?",
                            (review["artifact_id"],),
                        ).fetchone()
                        metadata = json.loads(row["metadata_json"])
                        if attack == "missing-staged-selection":
                            metadata["staged_inputs"].pop()
                        else:
                            metadata["staged_inputs"][0]["job_id"] = extra_dependency_id
                        connection.execute(
                            "UPDATE artifacts SET metadata_json=? WHERE artifact_id=?",
                            (canonical_json(metadata), review["artifact_id"]),
                        )
                    else:
                        row = connection.execute(
                            "SELECT payload_json FROM jobs WHERE job_id=?", (review_id,)
                        ).fetchone()
                        payload = json.loads(row["payload_json"])
                        mappings = payload["inputs_from_dependencies"]
                        if attack == "empty-mappings":
                            payload["inputs_from_dependencies"] = []
                        elif attack == "missing-mapping":
                            mappings.pop()
                        elif attack == "extra-mapping":
                            extra = dict(mappings[0])
                            extra["destination"] = "CANDIDATE/EXTRA.md"
                            mappings.append(extra)
                        elif attack == "wrong-destination":
                            mappings[0]["destination"] = "UNPROTECTED/README.md"
                        elif attack == "wrong-subpath":
                            mappings[0]["subpath"] = "MANIFEST.yaml"
                        elif attack == "wrong-artifact-expectation":
                            mappings[0]["artifact_type"] = "project_challenge_pack"
                        elif attack == "unprotected-candidate":
                            payload["protected_input_roots"] = []
                        elif attack == "direct-inputs":
                            payload["inputs"] = []
                        else:
                            payload["timeout_seconds"] = 1
                        connection.execute(
                            "UPDATE jobs SET payload_json=? WHERE job_id=?",
                            (canonical_json(payload), review_id),
                        )
                before = self._publication_counts()
                self._assert_invalid_without_publication(project_id, before)

    def test_surrogate_json_evidence_publishes_nothing(self) -> None:
        project_id = "project-surrogate-payload"
        _, review_id, _, _ = self._base_graph(project_id, "FAIL")
        with self.database.transaction(immediate=True) as connection:
            row = connection.execute(
                "SELECT payload_json FROM jobs WHERE job_id=?", (review_id,)
            ).fetchone()
            original_payload = row["payload_json"]
            attacked = original_payload[:-1] + ',"bad":"\\ud800"}'
            connection.execute(
                "UPDATE jobs SET payload_json=? WHERE job_id=?",
                (attacked, review_id),
            )
        before = self._publication_counts()
        with self.assertRaises(ByoxRemediationError):
            seed_byox_remediation_jobs(
                self.database,
                self.jobs,
                warehouse=self.settings.warehouse,
                project_ids=[project_id],
            )
        self.assertEqual(before, self._publication_counts())
        self.assertIsNone(self.jobs.get(repair_builder_job_id(project_id, 1)))
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                "UPDATE jobs SET payload_json=? WHERE job_id=?",
                (original_payload, review_id),
            )

        evaluation_project = "project-surrogate-evaluation"
        _, evaluation_review_id, _, _ = self._base_graph(
            evaluation_project, "FAIL"
        )
        with self.database.connect() as connection:
            artifact = connection.execute(
                "SELECT artifact_id,path FROM artifacts WHERE job_id=?",
                (evaluation_review_id,),
            ).fetchone()
        root = Path(artifact["path"])
        evaluation_path = root / "EVALUATION.json"
        attacked_evaluation = evaluation_path.read_text(encoding="utf-8").replace(
            '"limitations":[]', '"limitations":["\\udfff"]'
        )
        self.assertIn("\\udfff", attacked_evaluation)
        evaluation_path.write_text(attacked_evaluation, encoding="utf-8")
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                "UPDATE artifacts SET checksum=? WHERE artifact_id=?",
                (tree_sha256(root), artifact["artifact_id"]),
            )
        before = self._publication_counts()
        self._assert_invalid_without_publication(evaluation_project, before)

    def test_closed_acceptance_rejects_reviewed_labels_for_every_verdict(self) -> None:
        for verdict in ("PASS", "FAIL"):
            project_id = f"project-reviewed-label-{verdict.lower()}"
            with self.subTest(verdict=verdict):
                _, review_id, _, review = self._base_graph(project_id, verdict)
                with self.database.transaction(immediate=True) as connection:
                    connection.execute(
                        """
                        INSERT INTO artifact_validation_labels(
                            artifact_id,label,evidence_json,created_at
                        ) VALUES (?,'REVIEWED','{}',?)
                        """,
                        (review["artifact_id"], now()),
                    )
                result = seed_byox_remediation_jobs(
                    self.database, self.jobs, warehouse=self.settings.warehouse, project_ids=[project_id]
                )
                self.assertEqual(
                    "REMEDIATION_EVIDENCE_INVALID",
                    result["projects"][project_id]["status"],
                )
                self.assertIsNone(
                    self.jobs.get(repair_builder_job_id(project_id, 1))
                )

    def test_exact_binding_full_root_projection_and_hardened_backend(self) -> None:
        project_id = "project-handler"
        self._base_graph(project_id, "REVISE")
        seed_byox_remediation_jobs(self.database, self.jobs, warehouse=self.settings.warehouse, project_ids=[project_id])
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
        self.assertTrue((workspace / "PRIOR_BUILD/starter/main.py").is_file())
        self.assertEqual(
            0, (workspace / "PRIOR_BUILD/starter/main.py").stat().st_mode & 0o222
        )
        archive_paths, selection = _byox_repair_archive_selection(
            claim, workspace, provenance
        )
        assert archive_paths is not None and selection is not None
        self.assertTrue(BYOX_CANONICAL_CHALLENGE_ROOTS <= set(archive_paths))
        self.assertIn("starter", archive_paths)
        self.assertNotIn("PRIOR_BUILD", archive_paths)
        self.assertEqual(list(archive_paths), selection["paths"])
        _enforce_byox_remediation_backend(claim, self.settings)
        unsafe_settings = replace(
            self.settings,
            backend=replace(self.settings.backend, permission_profile="workspace-write"),
        )
        with self.assertRaisesRegex(HandlerFailure, "factory-isolated"):
            _enforce_byox_remediation_backend(claim, unsafe_settings)

    def test_s2_repair_policy_uses_the_same_hardened_archive_selection(self) -> None:
        project_id = "project-handler-s2-policy"
        self._base_graph(project_id, "REVISE")
        seed_byox_remediation_jobs(
            self.database,
            self.jobs,
            warehouse=self.settings.warehouse,
            project_ids=[project_id],
        )
        repair_id = repair_builder_job_id(project_id, 1)
        self.jobs.promote_eligible()
        claim = self.jobs.claim_next(
            "handler-s2-policy-test", 30, max_total=1, type_limits={}
        )
        assert claim is not None and claim.job_id == repair_id
        workspace = self.manager.allocate(repair_id, claim.attempt_count)
        _, provenance = JobHandlers(
            self.settings, self.database, self.manager
        )._stage_declared_inputs(claim, workspace)
        legacy_archive_paths, legacy_selection = _byox_repair_archive_selection(
            claim, workspace, provenance
        )

        s2_payload = copy.deepcopy(claim.payload)
        s2_payload["seed_policy"]["kind"] = (
            remediation_module.BYOX_REPAIR_S2_POLICY_KIND
        )
        archive_paths, selection = _byox_repair_archive_selection(
            replace(claim, payload=s2_payload), workspace, provenance
        )

        self.assertIsNotNone(archive_paths)
        self.assertIsNotNone(selection)
        self.assertEqual(legacy_archive_paths, archive_paths)
        self.assertEqual(legacy_selection, selection)
        assert archive_paths is not None
        self.assertTrue(BYOX_CANONICAL_CHALLENGE_ROOTS <= set(archive_paths))
        self.assertNotIn("PRIOR_BUILD", archive_paths)
        self.assertNotIn("PRIOR_REVIEW", archive_paths)

    def test_repair_archive_selection_rejects_s2_policy_lookalikes(self) -> None:
        project_id = "project-handler-s2-lookalike"
        self._base_graph(project_id, "REVISE")
        seed_byox_remediation_jobs(
            self.database,
            self.jobs,
            warehouse=self.settings.warehouse,
            project_ids=[project_id],
        )
        repair_id = repair_builder_job_id(project_id, 1)
        self.jobs.promote_eligible()
        claim = self.jobs.claim_next(
            "handler-s2-lookalike-test", 30, max_total=1, type_limits={}
        )
        assert claim is not None and claim.job_id == repair_id
        workspace = self.manager.allocate(repair_id, claim.attempt_count)
        _, provenance = JobHandlers(
            self.settings, self.database, self.manager
        )._stage_declared_inputs(claim, workspace)

        for kind in (
            "byox_reference_repair_s2_suffix",
            remediation_module.BYOX_REPAIR_REVIEW_S2_POLICY_KIND,
            [],
            {},
        ):
            with self.subTest(kind=kind):
                payload = copy.deepcopy(claim.payload)
                payload["seed_policy"]["kind"] = kind
                with self.assertRaisesRegex(
                    HandlerFailure,
                    "policy and artifact type must be declared together",
                ) as caught:
                    _byox_repair_archive_selection(
                        replace(claim, payload=payload), workspace, provenance
                    )
                self.assertEqual("unsafe_archive_projection", caught.exception.kind)
                self.assertFalse(caught.exception.retryable)

    def test_legacy_specialized_profile_excludes_only_controller_root(self) -> None:
        project_id = "project_4b7f4b85b17b06eeba75d235767a898f"
        specialized_files = {
            ".factory-workspace": "legacy controller metadata\n",
            "reports/analysis.md": "specialized report\n",
        }
        self._base_graph(
            project_id,
            "FAIL",
            builder_artifact_type="bytecode_vm_challenge_pack",
            builder_files=specialized_files,
        )
        seed_byox_remediation_jobs(self.database, self.jobs, warehouse=self.settings.warehouse, project_ids=[project_id])
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
        with self.assertRaisesRegex(ByoxRemediationError, "authoritative-cutover"):
            _validated_repair_inventory(
                {"repair_archive_selection": selection}, claim.payload
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
        self.assertEqual(
            projected_inventory,
            _validated_repair_inventory(
                self._published_repair_metadata(selection, claim.payload),
                claim.payload,
                artifact_checksum=selection["authoritative_cutover"][
                    "selected_output_checksum"
                ],
            ),
        )
        self.assertTrue((workspace / "AGENTS.md").is_file())
        self.assertTrue((workspace / "VALIDATION.md").is_file())

        (workspace / "UNDECLARED.txt").write_text("unexpected\n", encoding="utf-8")
        quarantine = _validate_byox_repair_outputs(
            workspace, archive_paths, selection, provenance
        )
        self.assertEqual(["UNDECLARED.txt"], quarantine["roots"])
        self.assertNotIn("UNDECLARED.txt", archive_paths)

    def test_bounded_undeclared_trees_are_manifested_but_not_published(self) -> None:
        claim, workspace, staged, archive_paths, selection = (
            self._materialized_repair_workspace("project-compatibility-accepted")
        )
        original_paths = copy.deepcopy(selection["paths"])
        original_paths_hash = selection["paths_sha256"]
        original_inventory = copy.deepcopy(selection["artifact_inventory"])
        staged_hashes = {
            name: tree_sha256(workspace / name)
            for name in ("PRIOR_BUILD", "PRIOR_REVIEW")
        }

        baseline = self.manager.create_archive_projection(workspace, archive_paths)
        baseline_checksum = tree_sha256(baseline)
        self.manager.discard_archive_projection(baseline)
        license_content = "SPDX-License-Identifier: MIT\n"
        inventory_content = "0123456789abcdef  sealed/reference/main.py\n"
        (workspace / "LICENSE").write_text(license_content, encoding="utf-8")
        (workspace / "ARTIFACT_INVENTORY.sha256").write_text(
            inventory_content, encoding="utf-8"
        )
        (workspace / "ARTIFACT_INVENTORY.json").write_text(
            '{"source":"worker"}\n', encoding="utf-8"
        )
        (workspace / "ARTIFACT_PROVENANCE.json").write_text(
            '{"classification":"generated"}\n', encoding="utf-8"
        )
        (workspace / "UNDECLARED.txt").write_text("bounded\n", encoding="utf-8")
        (workspace / "tools/lib").mkdir(parents=True)
        (workspace / "tools").chmod(0o2755)
        (workspace / "tools/verify.py").write_text(
            "print('verify')\n", encoding="utf-8"
        )
        (workspace / "tools/lib/check.py").write_text(
            "def check(): return True\n", encoding="utf-8"
        )

        evidence = _validate_byox_repair_outputs(
            workspace, archive_paths, selection, staged
        )

        self.assertEqual(evidence, selection["quarantined_outputs"])
        self.assertTrue(evidence["excluded_from_archive_projection"])
        self.assertEqual(
            "capture-time-retired-source-only", evidence["evidence_scope"]
        )
        self.assertEqual("excluded-non-artifact-quarantine", evidence["classification"])
        self.assertRegex(evidence["manifest_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(
            [
                "ARTIFACT_INVENTORY.json",
                "ARTIFACT_INVENTORY.sha256",
                "ARTIFACT_PROVENANCE.json",
                "LICENSE",
                "UNDECLARED.txt",
                "tools",
            ],
            evidence["roots"],
        )
        manifested = {item["path"]: item for item in evidence["entries"]}
        self.assertEqual("directory", manifested["tools"]["kind"])
        self.assertEqual(0o2755, manifested["tools"]["mode"])
        self.assertEqual("directory", manifested["tools/lib"]["kind"])
        self.assertEqual("regular-file", manifested["tools/verify.py"]["kind"])
        self.assertRegex(manifested["LICENSE"]["checksum"], r"^[0-9a-f]{64}$")
        for root in evidence["roots"]:
            self.assertNotIn(root, archive_paths)
        self.assertEqual(original_paths, selection["paths"])
        self.assertEqual(original_paths_hash, selection["paths_sha256"])
        self.assertEqual(original_inventory, selection["artifact_inventory"])
        self.assertEqual(
            original_inventory,
            _validated_repair_inventory(
                self._published_repair_metadata(selection, claim.payload),
                claim.payload,
                artifact_checksum=selection["authoritative_cutover"][
                    "selected_output_checksum"
                ],
            ),
        )
        handler_shaped_metadata = self._published_repair_metadata(
            selection, claim.payload
        )
        staged_by_path = {str(item["path"]): item for item in staged}
        for record in handler_shaped_metadata["staged_inputs"]:
            observed = staged_by_path[str(record["path"])]
            record.update(
                {
                    field: observed[field]
                    for field in remediation_module._STAGED_PROVENANCE_RUNTIME_INODE_FIELDS
                }
            )
        self.assertEqual(
            original_inventory,
            _validated_repair_inventory(
                handler_shaped_metadata,
                claim.payload,
                artifact_checksum=selection["authoritative_cutover"][
                    "selected_output_checksum"
                ],
            ),
        )
        incomplete_inode_metadata = copy.deepcopy(handler_shaped_metadata)
        incomplete_inode_metadata["staged_inputs"][0].pop("root_inode")
        with self.assertRaisesRegex(ByoxRemediationError, "inode evidence is incomplete"):
            _validated_repair_inventory(
                incomplete_inode_metadata,
                claim.payload,
                artifact_checksum=selection["authoritative_cutover"][
                    "selected_output_checksum"
                ],
            )
        with self.assertRaisesRegex(ByoxRemediationError, "bound to publication"):
            _validated_repair_inventory(
                self._published_repair_metadata(selection, claim.payload),
                claim.payload,
                artifact_checksum="0" * 64,
            )
        self.assertEqual(
            staged_hashes,
            {
                name: tree_sha256(workspace / name)
                for name in ("PRIOR_BUILD", "PRIOR_REVIEW")
            },
        )

        projected = self.manager.create_archive_projection(workspace, archive_paths)
        self.assertEqual(baseline_checksum, tree_sha256(projected))
        cutover = selection["authoritative_cutover"]
        self.assertEqual(
            tree_sha256(projected), cutover["selected_output_checksum"]
        )
        self.assertEqual(list(archive_paths), cutover["archive_paths"])
        self.assertEqual(selection["paths_sha256"], cutover["archive_paths_sha256"])
        for root in evidence["roots"]:
            self.assertFalse((projected / root).exists())
        self.manager.discard_archive_projection(projected)
        self.assertEqual(
            tree_sha256(workspace), cutover["validation_snapshot_checksum"]
        )

        code_spec = next(
            item
            for item in byox_runtime_safety_validators()
            if item["type"] == "byox_code_presence"
        )
        for path in (
            workspace / "starter/main.py",
            workspace / "public_tests/test_main.py",
            workspace / "sealed/reference/main.py",
            workspace / "sealed/reference_tests/test_main.py",
        ):
            path.parent.chmod(path.parent.stat().st_mode | 0o700)
            path.unlink(missing_ok=True)
        code_result = evaluate_byox_code_presence(workspace, code_spec)
        self.assertFalse(code_result.passed)
        self.assertTrue(code_result.evidence["missing_groups"])
        self.assertNotIn("tools/verify.py", json.dumps(code_result.evidence))

        tampered = copy.deepcopy(selection)
        tampered["quarantined_outputs"]["summary"]["total_bytes"] += 1
        with self.assertRaisesRegex(
            ByoxRemediationError, "quarantined-output"
        ):
            _validated_repair_inventory(
                self._published_repair_metadata(tampered, claim.payload), claim.payload
            )

        spliced_quarantine = copy.deepcopy(selection)
        quarantine = spliced_quarantine["quarantined_outputs"]
        file_entry = next(
            item for item in quarantine["entries"] if item["kind"] == "regular-file"
        )
        file_entry["checksum"] = "1" * 64
        quarantine_body = {
            key: value
            for key, value in quarantine.items()
            if key != "manifest_sha256"
        }
        quarantine["manifest_sha256"] = hashlib.sha256(
            canonical_json(quarantine_body).encode("utf-8")
        ).hexdigest()
        with self.assertRaisesRegex(
            ByoxRemediationError, "authoritative-cutover quarantine binding"
        ):
            _validated_repair_inventory(
                self._published_repair_metadata(spliced_quarantine, claim.payload), claim.payload
            )

        rewritten_metadata = self._published_repair_metadata(selection, claim.payload)
        rewritten_metadata["staged_inputs"][0]["checksum"] = "2" * 64
        with self.assertRaisesRegex(
            ByoxRemediationError, "staged metadata binding is inconsistent"
        ):
            _validated_repair_inventory(rewritten_metadata, claim.payload)

        removed_metadata = self._published_repair_metadata(selection, claim.payload)
        removed_metadata["staged_inputs"].pop()
        with self.assertRaisesRegex(
            ByoxRemediationError, "staged metadata binding is inconsistent"
        ):
            _validated_repair_inventory(removed_metadata, claim.payload)

        forged_cutover = copy.deepcopy(selection)
        forged_metadata = self._published_repair_metadata(selection, claim.payload)
        forged_record = forged_cutover["authoritative_cutover"]
        forged_record["staged_inputs"][0]["checksum"] = "3" * 64
        cutover_body = {
            key: value
            for key, value in forged_record.items()
            if key != "manifest_sha256"
        }
        forged_record["manifest_sha256"] = hashlib.sha256(
            canonical_json(cutover_body).encode("utf-8")
        ).hexdigest()
        forged_metadata["repair_archive_selection"] = forged_cutover
        forged_metadata["byox_validation_cutover"] = forged_record
        with self.assertRaisesRegex(
            ByoxRemediationError, "staged metadata binding is inconsistent"
        ):
            _validated_repair_inventory(forged_metadata, claim.payload)

    def test_top_level_capture_accounts_for_or_discards_late_source_roots(self) -> None:
        _, workspace, staged, archive_paths, selection = (
            self._materialized_repair_workspace("project-quarantine-root-race")
        )
        real_open = handlers_module.os.open
        injected = False

        def inject_before_first_open(path: object, flags: int, *args: object, **kwargs: object) -> int:
            nonlocal injected
            if (
                not injected
                and isinstance(path, (str, os.PathLike))
                and (Path(path) == workspace or os.fspath(path) == workspace.name)
            ):
                injected = True
                (workspace / "late-root.txt").write_text("late\n", encoding="utf-8")
            return real_open(path, flags, *args, **kwargs)

        with patch.object(
            handlers_module.os, "open", side_effect=inject_before_first_open
        ):
            evidence = _validate_byox_repair_outputs(
                workspace, archive_paths, selection, staged
            )
        self.assertTrue(injected)
        self.assertIn("late-root.txt", evidence["roots"])
        self.assertFalse((workspace / "late-root.txt").exists())

        real_capture = handlers_module._capture_byox_repair_quarantine

        def inject_after_enumeration(
            descriptor: int, paths: list[str], **kwargs: object
        ) -> dict[str, object]:
            (workspace / "later-root.txt").write_text("later\n", encoding="utf-8")
            return real_capture(descriptor, paths, **kwargs)

        with patch.object(
            handlers_module,
            "_capture_byox_repair_quarantine",
            side_effect=inject_after_enumeration,
        ):
            later_evidence = _validate_byox_repair_outputs(
                workspace, archive_paths, selection, staged
            )
        self.assertNotIn("later-root.txt", later_evidence["roots"])
        self.assertFalse((workspace / "later-root.txt").exists())

    def test_cross_boundary_hardlinks_fail_both_gate_and_cutover(self) -> None:
        _, workspace, staged, archive_paths, selection = (
            self._materialized_repair_workspace("project-quarantine-hardlink")
        )
        tools = workspace / "tools"
        tools.mkdir()
        payload = tools / "payload.py"
        payload.write_text("def value(): return 42\n", encoding="utf-8")
        for directory in (
            workspace / "starter",
            workspace / "sealed",
            workspace / "public_tests",
        ):
            directory.chmod(directory.stat().st_mode | 0o700)
        (workspace / "sealed/reference").mkdir(exist_ok=True)
        (workspace / "sealed/reference").chmod(
            (workspace / "sealed/reference").stat().st_mode | 0o700
        )
        for destination in (
            workspace / "starter/main.py",
            workspace / "sealed/reference/main.py",
            workspace / "public_tests/test_main.py",
        ):
            destination.unlink(missing_ok=True)
            os.link(payload, destination)
        self.assertEqual(4, payload.stat().st_nlink)

        code_spec = next(
            item
            for item in byox_runtime_safety_validators()
            if item["type"] == "byox_code_presence"
        )
        self.assertFalse(evaluate_byox_code_presence(workspace, code_spec).passed)
        with self.assertRaisesRegex(HandlerFailure, "multi-linked"):
            _validate_byox_repair_outputs(
                workspace, archive_paths, selection, staged
            )

    def test_cutover_rejects_unbound_entry_in_partially_staged_root(self) -> None:
        _, workspace, staged, archive_paths, selection = (
            self._materialized_repair_workspace("project-staged-root-extra")
        )
        review_root = workspace / "PRIOR_REVIEW"
        review_root.chmod(review_root.stat().st_mode | 0o700)
        (review_root / "worker-added.txt").write_text(
            "not a staged review input\n", encoding="utf-8"
        )
        with self.assertRaisesRegex(HandlerFailure, "unbound entry"):
            _validate_byox_repair_outputs(
                workspace, archive_paths, selection, staged
            )

    def test_post_capture_hardlink_only_mutates_retired_source(self) -> None:
        _, workspace, staged, archive_paths, selection = (
            self._materialized_repair_workspace("project-quarantine-hardlink-race")
        )
        starter = workspace / "starter"
        starter.chmod(starter.stat().st_mode | 0o700)
        real_capture = handlers_module._capture_byox_repair_quarantine

        def inject_staged_hardlink(
            descriptor: int, paths: list[str], **kwargs: object
        ) -> dict[str, object]:
            record = real_capture(descriptor, paths, **kwargs)
            os.link(workspace / "PRIOR_BUILD/README.md", starter / "late.py")
            return record

        with patch.object(
            handlers_module,
            "_capture_byox_repair_quarantine",
            side_effect=inject_staged_hardlink,
        ):
            evidence = _validate_byox_repair_outputs(
                workspace, archive_paths, selection, staged
            )
        self.assertFalse((workspace / "starter/late.py").exists())
        self.assertEqual("capture-time-retired-source-only", evidence["evidence_scope"])

    def test_post_capture_quarantine_rewrite_only_mutates_retired_source(self) -> None:
        _, workspace, staged, archive_paths, selection = (
            self._materialized_repair_workspace("project-quarantine-rewrite-race")
        )
        (workspace / "tools").mkdir()
        note = workspace / "tools/note.txt"
        original = b"before"
        replacement = b"after!"
        note.write_bytes(original)
        real_capture = handlers_module._capture_byox_repair_quarantine

        def rewrite_after_capture(
            descriptor: int, paths: list[str], **kwargs: object
        ) -> dict[str, object]:
            record = real_capture(descriptor, paths, **kwargs)
            note.write_bytes(replacement)
            return record

        with patch.object(
            handlers_module,
            "_capture_byox_repair_quarantine",
            side_effect=rewrite_after_capture,
        ):
            evidence = _validate_byox_repair_outputs(
                workspace, archive_paths, selection, staged
            )
        entries = {item["path"]: item for item in evidence["entries"]}
        self.assertEqual(
            hashlib.sha256(original).hexdigest(), entries["tools/note.txt"]["checksum"]
        )
        self.assertFalse((workspace / "tools").exists())
        self.assertEqual(
            "factory-authoritative-validation-snapshot",
            selection["authoritative_cutover"]["classification"],
        )

    def test_retained_source_descriptor_cannot_mutate_cutover_snapshot(self) -> None:
        _, workspace, staged, archive_paths, selection = (
            self._materialized_repair_workspace("project-retained-source-fd")
        )
        selected = workspace / "README.md"
        selected.chmod(selected.stat().st_mode | 0o600)
        original = selected.read_bytes()
        source_descriptor = os.open(selected, os.O_RDWR)
        source_identity = os.fstat(source_descriptor)
        try:
            _validate_byox_repair_outputs(
                workspace, archive_paths, selection, staged
            )
            replacement_identity = selected.stat()
            self.assertNotEqual(
                (source_identity.st_dev, source_identity.st_ino),
                (replacement_identity.st_dev, replacement_identity.st_ino),
            )
            os.lseek(source_descriptor, 0, os.SEEK_SET)
            os.write(source_descriptor, b"X" * len(original))
            os.fsync(source_descriptor)
            self.assertEqual(original, selected.read_bytes())
            self.assertEqual(0, os.fstat(source_descriptor).st_nlink)
        finally:
            os.close(source_descriptor)

    def test_pre_cutover_input_integrity_rejects_same_byte_inode_replacement(
        self,
    ) -> None:
        _, pre_workspace, _, _, _ = self._materialized_repair_workspace(
            "project-pre-cutover-input-integrity"
        )
        pre_integrity = [
            handlers_module._staged_input_record(pre_workspace / name, name)
            for name in ("PRIOR_BUILD", "PRIOR_REVIEW")
        ]
        handlers_module._verify_pre_cutover_input_integrity(
            pre_workspace, pre_integrity
        )
        pre_tree_checksum = tree_sha256(pre_workspace / "PRIOR_BUILD")
        self._replace_with_same_bytes_and_mode(
            pre_workspace / "PRIOR_BUILD/starter/main.py"
        )
        self.assertEqual(
            pre_tree_checksum, tree_sha256(pre_workspace / "PRIOR_BUILD")
        )
        with self.assertRaisesRegex(
            HandlerFailure, "protected input changed before authoritative cutover"
        ):
            handlers_module._verify_pre_cutover_input_integrity(
                pre_workspace, pre_integrity
            )

    def test_post_cutover_rebind_preserves_runtime_input_integrity(self) -> None:
        _, workspace, staged, archive_paths, selection = (
            self._materialized_repair_workspace(
                "project-post-cutover-input-integrity"
            )
        )
        integrity = [
            handlers_module._staged_input_record(workspace / name, name)
            for name in ("PRIOR_BUILD", "PRIOR_REVIEW")
        ]
        semantic_fields = ("path", "kind", "checksum_algorithm", "checksum")
        semantic_bindings = [
            {field: record[field] for field in semantic_fields}
            for record in integrity
        ]
        root_identities = [
            (record["root_device"], record["root_inode"])
            for record in integrity
        ]
        staged_before = copy.deepcopy(staged)
        handlers_module._verify_pre_cutover_input_integrity(workspace, integrity)
        _validate_byox_repair_outputs(
            workspace, archive_paths, selection, staged
        )
        cutover_bindings = copy.deepcopy(
            selection["authoritative_cutover"]["staged_inputs"]
        )

        validator = Validator(self.database)
        stale = validator._input_integrity(
            "declared-inputs-remained-immutable",
            workspace,
            {"inputs": integrity, "require_fresh_inodes": True},
        )
        self.assertFalse(stale.passed)
        self.assertEqual(
            [
                {"path": "PRIOR_BUILD", "reason": "inode-identity-mismatch"},
                {"path": "PRIOR_REVIEW", "reason": "inode-identity-mismatch"},
            ],
            stale.evidence["mismatches"],
        )

        rebound = handlers_module._rebind_cutover_input_integrity(
            workspace, integrity
        )
        self.assertEqual(
            semantic_bindings,
            [
                {field: record[field] for field in semantic_fields}
                for record in rebound
            ],
        )
        self.assertTrue(
            all(
                before
                != (after["root_device"], after["root_inode"])
                for before, after in zip(root_identities, rebound, strict=True)
            )
        )
        self.assertEqual(staged_before, staged)
        self.assertEqual(
            cutover_bindings,
            selection["authoritative_cutover"]["staged_inputs"],
        )
        valid = validator._input_integrity(
            "declared-inputs-remained-immutable",
            workspace,
            {"inputs": rebound, "require_fresh_inodes": True},
        )
        self.assertTrue(valid.passed)

        prior_build_checksum = tree_sha256(workspace / "PRIOR_BUILD")
        self._replace_with_same_bytes_and_mode(
            workspace / "PRIOR_BUILD/starter/main.py"
        )
        self.assertEqual(
            prior_build_checksum, tree_sha256(workspace / "PRIOR_BUILD")
        )
        tampered = validator._input_integrity(
            "declared-inputs-remained-immutable",
            workspace,
            {"inputs": rebound, "require_fresh_inodes": True},
        )
        self.assertFalse(tampered.passed)
        self.assertEqual(
            [
                {"path": "PRIOR_BUILD", "reason": "inode-identity-mismatch"}
            ],
            tampered.evidence["mismatches"],
        )

    def test_cutover_input_observation_fails_closed_on_symlink_loop(self) -> None:
        workspace = self.root / "symlink-loop-workspace"
        staged = workspace / "INPUT"
        staged.mkdir(parents=True)
        (staged / "input.txt").write_text("immutable\n", encoding="utf-8")
        record = handlers_module._staged_input_record(staged, "INPUT")
        shutil.rmtree(staged)
        staged.symlink_to("INPUT")

        with self.assertRaises(HandlerFailure) as caught:
            handlers_module._observe_cutover_input_integrity(workspace, record)

        self.assertEqual("unsafe_archive_projection", caught.exception.kind)
        self.assertFalse(caught.exception.retryable)

    def test_repair_codex_handler_appends_rebound_input_integrity(self) -> None:
        project_id = "project-repair-handler-cutover-integrity"
        self._base_graph(project_id, "REVISE")
        seed_byox_remediation_jobs(
            self.database,
            self.jobs,
            warehouse=self.settings.warehouse,
            project_ids=[project_id],
        )
        repair_id = repair_builder_job_id(project_id, 1)
        self.jobs.promote_eligible()
        claim = self.jobs.claim_next(
            "repair-handler-cutover-integrity",
            30,
            max_total=1,
            type_limits={},
        )
        assert claim is not None and claim.job_id == repair_id
        workspace = self.manager.allocate(repair_id, claim.attempt_count)
        log_dir = self.root / "repair-handler-cutover-logs"
        log_dir.mkdir()
        backend_result = type(
            "BackendResultDouble",
            (),
            {
                "exit_code": 0,
                "session_id": "repair-cutover-session",
                "usage": {},
                "timed_out": False,
                "cancelled": False,
                "stderr_tail": "",
            },
        )()

        def fake_start(
            _backend: object,
            _prompt: str,
            current_workspace: Path,
            _logs: Path,
            **_kwargs: object,
        ) -> object:
            prior = current_workspace / "PRIOR_BUILD"
            for source in prior.iterdir():
                target = current_workspace / source.name
                if source.is_dir():
                    shutil.copytree(source, target, dirs_exist_ok=True)
                else:
                    shutil.copy2(source, target)
            for name in BYOX_CANONICAL_CHALLENGE_ROOTS:
                target = current_workspace / name
                if target.exists():
                    continue
                if name in BYOX_CANONICAL_DIRECTORY_ROOTS:
                    target.mkdir()
                else:
                    target.write_text(f"generated {name}\n", encoding="utf-8")
            return backend_result

        handlers = JobHandlers(self.settings, self.database, self.manager)
        with patch(
            "learnfactory.handlers.ExecBackend.start_job", new=fake_start
        ), patch.object(
            handlers_module,
            "_enforce_mass_seed_backend",
        ), patch.object(
            handlers_module,
            "_verify_pre_cutover_input_integrity",
            wraps=handlers_module._verify_pre_cutover_input_integrity,
        ) as verify, patch.object(
            handlers_module,
            "_rebind_cutover_input_integrity",
            wraps=handlers_module._rebind_cutover_input_integrity,
        ) as rebind:
            result = handlers._codex(
                claim,
                workspace,
                log_dir,
                threading.Event(),
            )

        verify.assert_called_once()
        rebind.assert_called_once()
        pre_cutover_records = rebind.call_args.args[1]
        matching = [
            specification
            for specification in result.validators
            if specification.get("name")
            == "declared-inputs-remained-immutable"
        ]
        self.assertEqual(1, len(matching))
        [integrity_validator] = matching
        rebound_records = integrity_validator["inputs"]
        semantic_fields = ("path", "kind", "checksum_algorithm", "checksum")
        self.assertEqual(
            [
                {field: record[field] for field in semantic_fields}
                for record in pre_cutover_records
            ],
            [
                {field: record[field] for field in semantic_fields}
                for record in rebound_records
            ],
        )
        self.assertTrue(
            all(
                (before["root_device"], before["root_inode"])
                != (after["root_device"], after["root_inode"])
                for before, after in zip(
                    pre_cutover_records, rebound_records, strict=True
                )
            )
        )
        validation = Validator(self.database)._input_integrity(
            "declared-inputs-remained-immutable",
            workspace,
            integrity_validator,
        )
        self.assertTrue(validation.passed)

    def test_second_cutover_rename_failure_rolls_back_and_cleans_snapshot(self) -> None:
        _, workspace, staged, archive_paths, selection = (
            self._materialized_repair_workspace("project-cutover-rollback")
        )
        (workspace / "extra.txt").write_text("source-only\n", encoding="utf-8")
        original_checksum = tree_sha256(workspace)
        real_rename = handlers_module.os.rename
        calls = 0

        def fail_second_rename(*args: object, **kwargs: object) -> None:
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("injected second rename failure")
            real_rename(*args, **kwargs)

        with patch.object(
            handlers_module.os, "rename", side_effect=fail_second_rename
        ):
            with self.assertRaisesRegex(HandlerFailure, "cutover failed"):
                _validate_byox_repair_outputs(
                    workspace, archive_paths, selection, staged
                )
        self.assertEqual(3, calls)
        self.assertEqual(original_checksum, tree_sha256(workspace))
        self.assertTrue((workspace / "extra.txt").is_file())
        self.assertNotIn("authoritative_cutover", selection)
        self.assertFalse(
            any(
                child.name.startswith((".repair-cutover-", ".repair-retired-"))
                for child in workspace.parent.iterdir()
            )
        )

    def test_sensitive_and_unicode_obfuscated_names_fail_runtime_and_replay(self) -> None:
        claim, workspace, staged, archive_paths, selection = (
            self._materialized_repair_workspace("project-quarantine-sensitive")
        )
        rejected_names = (
            "TOKEN.txt",
            "passwords.json",
            "ＳＯＬＵＴＩＯＮ.py",
            "solu\u200btion.py",
            "credenti\u0301als.json",
        )
        for name in rejected_names:
            with self.subTest(runtime_name=name):
                path = workspace / name
                path.write_text("sensitive\n", encoding="utf-8")
                with self.assertRaises(HandlerFailure) as captured:
                    _validate_byox_repair_outputs(
                        workspace, archive_paths, selection, staged
                    )
                self.assertNotIn(name, str(captured.exception))
                path.unlink()

        safe = workspace / "extra.txt"
        safe.write_text("safe\n", encoding="utf-8")
        _validate_byox_repair_outputs(
            workspace, archive_paths, selection, staged
        )
        for name in rejected_names:
            with self.subTest(replay_name=name):
                forged = copy.deepcopy(selection)
                record = forged["quarantined_outputs"]
                record["roots"] = [name]
                record["entries"][0]["path"] = name
                body = {
                    key: value
                    for key, value in record.items()
                    if key != "manifest_sha256"
                }
                record["manifest_sha256"] = hashlib.sha256(
                    canonical_json(body).encode("utf-8")
                ).hexdigest()
                with self.assertRaisesRegex(
                    ByoxRemediationError, "quarantined-output"
                ):
                    _validated_repair_inventory(
                        self._published_repair_metadata(forged, claim.payload), claim.payload
                    )

    def test_quarantine_rejects_unsafe_names_types_and_oversized_files(self) -> None:
        _, workspace, staged, archive_paths, selection = (
            self._materialized_repair_workspace("project-compatibility-rejected")
        )

        license_path = workspace / "LICENSE"
        license_path.write_bytes(
            b"x" * (BYOX_REPAIR_QUARANTINE_MAX_FILE_BYTES + 1)
        )
        with self.assertRaisesRegex(HandlerFailure, "per-file bytes"):
            _validate_byox_repair_outputs(
                workspace, archive_paths, selection, staged
            )
        license_path.unlink()

        inventory_path = workspace / "ARTIFACT_INVENTORY.sha256"
        inventory_path.symlink_to("LICENSE_BOUNDARY.md")
        with self.assertRaisesRegex(HandlerFailure, "unsafe or unreadable"):
            _validate_byox_repair_outputs(
                workspace, archive_paths, selection, staged
            )
        inventory_path.unlink()

        os.mkfifo(inventory_path)
        with self.assertRaisesRegex(HandlerFailure, "special file"):
            _validate_byox_repair_outputs(
                workspace, archive_paths, selection, staged
            )
        inventory_path.unlink()

        hidden = workspace / ".quarantine-cache"
        hidden.write_text("hidden\n", encoding="utf-8")
        with self.assertRaisesRegex(HandlerFailure, "forbidden.*name"):
            _validate_byox_repair_outputs(
                workspace, archive_paths, selection, staged
            )
        hidden.unlink()

        forbidden = workspace / "secrets"
        forbidden.mkdir()
        with self.assertRaisesRegex(HandlerFailure, "forbidden.*name"):
            _validate_byox_repair_outputs(
                workspace, archive_paths, selection, staged
            )
        forbidden.rmdir()

        tools = workspace / "tools"
        tools.mkdir()
        (tools / "Foo.txt").write_text("a\n", encoding="utf-8")
        (tools / "foo.txt").write_text("b\n", encoding="utf-8")
        with self.assertRaisesRegex(HandlerFailure, "case-colliding"):
            _validate_byox_repair_outputs(
                workspace, archive_paths, selection, staged
            )
        shutil.rmtree(tools)

        tools.mkdir()
        (tools / "JOB.md").write_text("control\n", encoding="utf-8")
        with self.assertRaisesRegex(HandlerFailure, "forbidden.*name"):
            _validate_byox_repair_outputs(
                workspace, archive_paths, selection, staged
            )
        shutil.rmtree(tools)

        tools.mkdir()
        cursor = tools
        for index in range(BYOX_REPAIR_QUARANTINE_MAX_DEPTH):
            cursor = cursor / f"d{index}"
            cursor.mkdir()
        with self.assertRaisesRegex(HandlerFailure, "maximum depth"):
            _validate_byox_repair_outputs(
                workspace, archive_paths, selection, staged
            )
        shutil.rmtree(tools)

    def test_quarantine_enforces_each_aggregate_resource_bound(self) -> None:
        _, workspace, staged, archive_paths, selection = (
            self._materialized_repair_workspace("project-quarantine-limits")
        )

        root_files = [
            workspace / f"extra-{index}.txt"
            for index in range(BYOX_REPAIR_QUARANTINE_MAX_ROOTS + 1)
        ]
        for path in root_files:
            path.write_text("x\n", encoding="utf-8")
        with self.assertRaisesRegex(HandlerFailure, "root count|too many"):
            _validate_byox_repair_outputs(
                workspace, archive_paths, selection, staged
            )
        for path in root_files:
            path.unlink()

        tools = workspace / "tools"
        tools.mkdir()
        for index in range(BYOX_REPAIR_QUARANTINE_MAX_ENTRIES):
            (tools / f"entry-{index}").mkdir()
        with self.assertRaisesRegex(HandlerFailure, "maximum entries"):
            _validate_byox_repair_outputs(
                workspace, archive_paths, selection, staged
            )
        shutil.rmtree(tools)

        tools.mkdir()
        for index in range(BYOX_REPAIR_QUARANTINE_MAX_FILES + 1):
            (tools / f"file-{index}.txt").write_text("x", encoding="utf-8")
        with self.assertRaisesRegex(HandlerFailure, "maximum files"):
            _validate_byox_repair_outputs(
                workspace, archive_paths, selection, staged
            )
        shutil.rmtree(tools)

        tools.mkdir()
        file_count = (
            BYOX_REPAIR_QUARANTINE_MAX_TOTAL_BYTES
            // BYOX_REPAIR_QUARANTINE_MAX_FILE_BYTES
            + 1
        )
        for index in range(file_count):
            (tools / f"blob-{index}.bin").write_bytes(
                b"x" * BYOX_REPAIR_QUARANTINE_MAX_FILE_BYTES
            )
        with self.assertRaisesRegex(HandlerFailure, "maximum total bytes"):
            _validate_byox_repair_outputs(
                workspace, archive_paths, selection, staged
            )
        shutil.rmtree(tools)

    def test_unsupported_builder_artifact_type_fails_closed(self) -> None:
        project_id = "project-unsupported-profile"
        self._base_graph(
            project_id,
            "REVISE",
            builder_artifact_type="unrecognized_challenge_pack",
        )

        result = seed_byox_remediation_jobs(
            self.database, self.jobs, warehouse=self.settings.warehouse, project_ids=[project_id]
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
                        self.database, self.jobs, warehouse=self.settings.warehouse, project_ids=[project_id]
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
                    self.database, self.jobs, warehouse=self.settings.warehouse, project_ids=[rollback_project]
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
