from __future__ import annotations

import copy
import json
import shutil
import unittest
from pathlib import Path
from typing import Any

import learnfactory.byox_remediation as remediation_module
import learnfactory.handlers as handlers_module
from learnfactory.backend_policy import with_mass_seed_backend_policy
from learnfactory.byox_baselines import (
    byox_s2_reviewer_job_id,
    insert_or_verify_bound_job,
    load_byox_baseline,
    load_job_definition,
    load_verified_binding,
    make_job_definition,
)
from learnfactory.byox_remediation import (
    BYOX_REPAIR_ARTIFACT_TYPE,
    BYOX_REPAIR_REVIEW_S2_POLICY_KIND,
    BYOX_REPAIR_S2_POLICY_KIND,
    seed_byox_remediation_jobs,
)
from learnfactory.capability_gate import CODEX_BACKEND_GATE_JOB_ID
from learnfactory.seeding import (
    BYOX_REVIEW_CONTRACT_VERSION,
    BYOX_REVIEW_S2_POLICY_KIND,
    _byox_reviewer_payload,
    seed_all_byox_reference_jobs,
)
from learnfactory.util import canonical_json, now, tree_sha256
from learnfactory.validation import Validator
from learnfactory.worker import _validation_labels
import tests.test_byox_remediation as legacy_tests


class ByoxS2RemediationContractTests(unittest.TestCase):
    """Executable contract for immutable-baseline BYOX remediation.

    The legacy remediation suite deliberately remains authoritative for legacy
    job identities.  These tests define a disjoint S2 universe: every accepted
    base and repair job is discovered through an exact immutable binding, and
    every identity that can collide across catalog drift includes the baseline.
    """

    def setUp(self) -> None:
        fixture = legacy_tests.ByoxRemediationTests(
            methodName="test_validated_pass_stops_without_claiming_workflow_completion"
        )
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.fixture = fixture
        self.database = fixture.database
        self.jobs = fixture.jobs
        self.manager = fixture.manager
        self.settings = fixture.settings

    def _add_project(self, project_id: str, *, title: str | None = None) -> None:
        self.fixture._catalog_project(project_id, title=title)
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                """
                UPDATE sources SET metadata_json=? WHERE source_id='source_byox'
                """,
                (
                    canonical_json(
                        {
                            "adapter": "build_your_own_x",
                            "extractor_version": "test-s2-v1",
                            "snapshot_reader": "git-object-database",
                            "tree_hash": "test-tree-s2-v1",
                        }
                    ),
                ),
            )

    def _seed_s2(self, project_id: str) -> dict[str, object]:
        result = seed_all_byox_reference_jobs(
            self.database,
            self.jobs,
            warehouse=self.settings.warehouse,
        )
        project = result["projects"][project_id]
        self.assertEqual("seeded_generic_s2", project["mode"])
        baseline = str(project["baseline_sha256"])
        builder_id = str(project["builder"])
        reviewer_id = str(project["reviewer"])
        with self.database.connect() as connection:
            builder_binding = load_verified_binding(connection, builder_id)
            reviewer_binding = load_verified_binding(connection, reviewer_id)
        self.assertIsNotNone(builder_binding)
        self.assertIsNotNone(reviewer_binding)
        assert builder_binding is not None and reviewer_binding is not None
        self.assertEqual(baseline, builder_binding.baseline_sha256)
        self.assertEqual(baseline, reviewer_binding.baseline_sha256)
        self.assertEqual("builder", builder_binding.role)
        self.assertEqual("reviewer", reviewer_binding.role)
        self.assertEqual(builder_id, reviewer_binding.builder_job_id)
        return {
            "baseline": baseline,
            "builder": builder_id,
            "reviewer": reviewer_id,
        }

    def _start_job(self, job_id: str) -> tuple[Path, str, str]:
        workspace = self.manager.allocate(job_id, 1)
        owner = f"s2-contract-owner-{job_id}"
        lease_token = f"s2-contract-lease-{job_id}"
        timestamp = now()
        with self.database.transaction(immediate=True) as connection:
            row = connection.execute(
                "SELECT state FROM jobs WHERE job_id=?", (job_id,)
            ).fetchone()
            self.assertIsNotNone(row)
            assert row is not None
            if row["state"] == "DISCOVERED":
                connection.execute(
                    "UPDATE jobs SET state='READY' WHERE job_id=?", (job_id,)
                )
            changed = connection.execute(
                """
                UPDATE jobs
                SET state='CLAIMED',owner=?,lease_token=?,lease_expires_at=?,
                    heartbeat_at=?,attempt_count=1,started_at=?
                WHERE job_id=? AND state='READY' AND attempt_count=0
                """,
                (
                    owner,
                    lease_token,
                    timestamp + 600,
                    timestamp,
                    timestamp,
                    job_id,
                ),
            )
            self.assertEqual(1, changed.rowcount)
            changed = connection.execute(
                "UPDATE jobs SET state='RUNNING',workspace=? WHERE job_id=? AND state='CLAIMED'",
                (str(workspace), job_id),
            )
            self.assertEqual(1, changed.rowcount)
        return workspace, owner, lease_token

    def _claim_retry_attempt(
        self, job_id: str, attempt_number: int
    ) -> tuple[Path, str, str]:
        owner = f"s2-retry-owner-{attempt_number}"
        claimed = self.jobs.claim_next(
            owner,
            lease_seconds=600,
            max_total=1,
            type_limits={},
        )
        self.assertIsNotNone(claimed)
        assert claimed is not None
        self.assertEqual(job_id, claimed.job_id)
        self.assertEqual(attempt_number, claimed.attempt_count)
        workspace = self.manager.allocate(job_id, attempt_number)
        with self.database.transaction(immediate=True) as connection:
            changed = connection.execute(
                """
                UPDATE jobs SET state='RUNNING',workspace=?
                WHERE job_id=? AND state='CLAIMED' AND owner=? AND lease_token=?
                """,
                (str(workspace), job_id, owner, claimed.lease_token),
            )
            self.assertEqual(1, changed.rowcount)
        return workspace, owner, claimed.lease_token

    @staticmethod
    def _write(path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def _write_canonical_pack(self, workspace: Path, payload: dict[str, object]) -> None:
        validators = payload["validators"]
        assert isinstance(validators, list)
        required = next(
            item for item in validators if item.get("type") == "required_paths"
        )
        for relative in required["paths"]:
            self._write(workspace / str(relative), f"fixture for {relative}\n")
        schemas = {
            str(item["path"]): item["schema"]["enum"][0]
            for item in validators
            if item.get("type") == "json_schema"
            and isinstance(item.get("schema"), dict)
            and isinstance(item["schema"].get("enum"), list)
        }
        for relative, document in schemas.items():
            self._write(workspace / relative, canonical_json(document) + "\n")
        self._write(workspace / "starter" / "main.py", "print('starter')\n")
        self._write(
            workspace / "public_tests" / "test_main.py",
            "assert 1 + 1 == 2\n",
        )
        self._write(
            workspace / "sealed" / "reference" / "main.py",
            "print('reference')\n",
        )
        self._write(
            workspace / "sealed" / "reference_tests" / "test_main.py",
            "assert 2 + 2 == 4\n",
        )

    def _publish_running_workspace(
        self,
        *,
        job_id: str,
        workspace: Path,
        owner: str,
        lease_token: str,
        validators: list[dict[str, object]],
        artifact_type: str,
        semantic_path: str,
        metadata: dict[str, object],
        archive_paths: tuple[str, ...] | None = None,
        attempt_number: int = 1,
    ) -> dict[str, object]:
        self.manager.discard_root_metadata(workspace, ".factory-workspace")
        log_dir = self.settings.warehouse / "logs" / "s2-contract" / job_id
        log_dir.mkdir(parents=True, exist_ok=True)
        results = Validator(self.database).run(
            job_id,
            workspace,
            validators,
            log_dir,
            attempt_number=attempt_number,
        )
        self.assertTrue(results)
        self.assertTrue(
            all(item.passed for item in results),
            [(item.name, item.status, item.evidence) for item in results],
        )
        labels = _validation_labels(results)
        validation_tree = tree_sha256(workspace)
        candidate = workspace
        projection = None
        if archive_paths is not None:
            projection = self.manager.create_archive_projection(workspace, archive_paths)
            candidate = projection
        validated_tree = tree_sha256(candidate)
        prepared = self.manager.prepare_archive(
            job_id,
            attempt_number,
            candidate,
            artifact_type=artifact_type,
            semantic_path=semantic_path,
            metadata={
                **metadata,
                "job_id": job_id,
                "attempt": attempt_number,
                "validation_evidence": [
                    {
                        "validator": item.name,
                        "status": item.status,
                        "evidence": item.evidence,
                    }
                    for item in results
                ],
                "validation_labels": labels,
                "validation_workspace_tree_sha256": validation_tree,
                "validated_tree_sha256": validated_tree,
            },
            validation_status="+".join(labels),
            validation_labels=labels,
        )
        self.jobs.succeed_with_artifact(
            job_id,
            owner,
            lease_token,
            None,  # no worker row is needed for this controller-level fixture
            prepared,
        )
        if projection is not None:
            self.manager.discard_archive_projection(projection)
        with self.database.connect() as connection:
            artifact = connection.execute(
                """
                SELECT artifact_id,job_id,type,path,checksum,checksum_algorithm,
                       attempt_number,metadata_json
                FROM artifacts WHERE job_id=?
                """,
                (job_id,),
            ).fetchone()
        self.assertIsNotNone(artifact)
        assert artifact is not None
        return {
            **dict(artifact),
            "artifact_type": artifact["type"],
            "artifact_checksum": artifact["checksum"],
            "artifact_attempt": artifact["attempt_number"],
        }

    def _complete_builder(self, builder_id: str) -> dict[str, object]:
        job = self.jobs.get(builder_id)
        self.assertIsNotNone(job)
        assert job is not None
        workspace, owner, lease = self._start_job(builder_id)
        self._write_canonical_pack(workspace, job["payload"])
        return self._publish_running_workspace(
            job_id=builder_id,
            workspace=workspace,
            owner=owner,
            lease_token=lease,
            validators=copy.deepcopy(job["payload"]["validators"]),
            artifact_type=str(job["payload"]["artifact_type"]),
            semantic_path=str(job["payload"]["artifact_path"]),
            metadata={},
        )

    def _stage_review_inputs(
        self,
        workspace: Path,
        payload: dict[str, object],
        builder: dict[str, object],
    ) -> list[dict[str, object]]:
        source_root = Path(str(builder["path"]))
        declarations = payload["inputs_from_dependencies"]
        assert isinstance(declarations, list)
        staged: list[dict[str, object]] = []
        for item in declarations:
            assert isinstance(item, dict)
            subpath = str(item["subpath"])
            source = source_root / subpath
            destination = str(item["destination"])
            if source.is_dir():
                target = self.manager.stage_tree(source, workspace, destination)
            else:
                target = self.manager.stage_file(source, workspace, destination)
            own = handlers_module._staged_input_record(target, destination)
            staged.append(
                {
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
            )
        return staged

    def _complete_review(
        self,
        *,
        project_id: str,
        reviewer_id: str,
        builder: dict[str, object],
        verdict: str = "REVISE",
    ) -> dict[str, object]:
        job = self.jobs.get(reviewer_id)
        self.assertIsNotNone(job)
        assert job is not None
        payload = job["payload"]
        workspace, owner, lease = self._start_job(reviewer_id)
        staged = self._stage_review_inputs(workspace, payload, builder)
        protected = workspace / "CANDIDATE"
        protected.chmod(protected.stat().st_mode & ~0o222)
        integrity = [
            handlers_module._staged_input_record(protected, "CANDIDATE")
        ]
        self._write(
            workspace / "EVALUATION.json",
            canonical_json(
                {
                    "project_id": project_id,
                    "builder_job_id": str(builder["job_id"]),
                    "verdict": verdict,
                    "evidence": ["independent contract fixture finding"],
                    "checks_run": ["bounded deterministic fixture check"],
                    "limitations": [],
                }
            )
            + "\n",
        )
        self._write(workspace / "REVIEW.md", f"# {verdict}\nConcrete finding.\n")
        self._write(workspace / "VALIDATION.md", "# Independent checks\n")
        validators = copy.deepcopy(payload["validators"])
        validators.append(
            {
                "type": "input_integrity",
                "name": "declared-inputs-remained-immutable",
                "inputs": integrity,
                "require_fresh_inodes": True,
            }
        )
        return self._publish_running_workspace(
            job_id=reviewer_id,
            workspace=workspace,
            owner=owner,
            lease_token=lease,
            validators=validators,
            artifact_type="byox-independent-review",
            semantic_path=str(payload["artifact_path"]),
            metadata={"staged_inputs": staged},
            archive_paths=("EVALUATION.json", "REVIEW.md", "VALIDATION.md"),
        )

    def _complete_negative_s2(self, project_id: str) -> dict[str, object]:
        graph = self._seed_s2(project_id)
        builder = self._complete_builder(str(graph["builder"]))
        review = self._complete_review(
            project_id=project_id,
            reviewer_id=str(graph["reviewer"]),
            builder=builder,
        )
        return {**graph, "builder_artifact": builder, "review_artifact": review}

    def _seed_repairs(self, project_id: str) -> dict[str, object]:
        return seed_byox_remediation_jobs(
            self.database,
            self.jobs,
            warehouse=self.settings.warehouse,
            project_ids=[project_id],
        )

    def _assert_s2_repair_builder(
        self,
        *,
        result: dict[str, object],
        project_id: str,
        baseline: str,
        builder_id: str,
        reviewer_id: str,
    ) -> tuple[str, dict[str, object]]:
        self.assertEqual(1, result["created_jobs"], result)
        project = result["projects"][project_id]
        self.assertEqual("REPAIR_BUILDER_SEEDED", project["status"])
        repair_id = str(project["builder"])
        repair = self.jobs.get(repair_id)
        self.assertIsNotNone(repair)
        assert repair is not None
        payload = repair["payload"]
        policy = payload["seed_policy"]
        self.assertEqual(BYOX_REPAIR_S2_POLICY_KIND, policy["kind"])
        self.assertEqual(baseline, payload["baseline_sha256"])
        self.assertEqual(baseline, policy["baseline_sha256"])
        self.assertEqual(baseline, payload["remediation_snapshot"]["baseline_sha256"])
        self.assertIn(baseline[:16], str(payload["artifact_path"]))
        self.assertEqual(
            {CODEX_BACKEND_GATE_JOB_ID, builder_id, reviewer_id},
            self._dependencies(repair_id),
        )
        with self.database.connect() as connection:
            binding = load_verified_binding(connection, repair_id)
        self.assertIsNotNone(binding)
        assert binding is not None
        self.assertEqual("builder", binding.role)
        self.assertEqual(baseline, binding.baseline_sha256)
        return repair_id, repair

    def _tree_files(self, root: Path) -> dict[str, str]:
        return {
            path.relative_to(root).as_posix(): path.read_text(encoding="utf-8")
            for path in sorted(root.rglob("*"))
            if path.is_file()
        }

    def _dependencies(self, job_id: str) -> set[str]:
        with self.database.connect() as connection:
            return {
                str(row["depends_on_job_id"])
                for row in connection.execute(
                    "SELECT depends_on_job_id FROM job_dependencies WHERE job_id=?",
                    (job_id,),
                )
            }

    def _replace_fixture_validation_with_exact_rows(self, job_id: str) -> None:
        """Upgrade the legacy test helper's publication to real pure validators."""

        job = self.jobs.get(job_id)
        self.assertIsNotNone(job)
        assert job is not None
        with self.database.connect() as connection:
            artifact = connection.execute(
                "SELECT artifact_id,path,checksum,metadata_json FROM artifacts WHERE job_id=?",
                (job_id,),
            ).fetchone()
        self.assertIsNotNone(artifact)
        assert artifact is not None
        with self.database.transaction(immediate=True) as connection:
            connection.execute("DELETE FROM validations WHERE job_id=?", (job_id,))
        log_dir = self.settings.warehouse / "logs" / "s2-contract" / job_id
        log_dir.mkdir(parents=True, exist_ok=True)
        results = Validator(self.database).run(
            job_id,
            Path(str(artifact["path"])),
            copy.deepcopy(job["payload"]["validators"]),
            log_dir,
            attempt_number=1,
        )
        self.assertTrue(all(item.passed for item in results))
        metadata = json.loads(str(artifact["metadata_json"]))
        validation_timestamp = now()
        integrity_id = f"validation_{job_id}_declared_inputs"
        integrity_evidence = {
            "checked": list(job["payload"]["protected_input_roots"]),
            "mismatches": [],
        }
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                """
                INSERT INTO validations(
                    validation_id,job_id,validator,status,command_json,exit_code,
                    stdout_path,stderr_path,evidence_json,started_at,finished_at,
                    attempt_number,claims_json
                ) VALUES (?,?,'declared-inputs-remained-immutable','PASS',NULL,NULL,
                          NULL,NULL,?,?,?,?, '[]')
                """,
                (
                    integrity_id,
                    job_id,
                    canonical_json(integrity_evidence),
                    validation_timestamp,
                    validation_timestamp,
                    1,
                ),
            )
            rows = connection.execute(
                """
                SELECT validation_id,validator,status,evidence_json,claims_json,
                       finished_at
                FROM validations WHERE job_id=? AND attempt_number=1
                ORDER BY started_at,validation_id
                """,
                (job_id,),
            ).fetchall()
            labels = ["GENERATED", "PARTIAL"]
            validation_evidence = [
                {
                    "validator": row["validator"],
                    "status": row["status"],
                    "evidence": json.loads(row["evidence_json"]),
                }
                for row in rows
            ]
            artifact_created = max(float(row["finished_at"]) for row in rows) + 0.001
            job_finished = artifact_created + 0.001
            metadata.update(
                {
                    "job_id": job_id,
                    "attempt": 1,
                    "validated_tree_sha256": artifact["checksum"],
                    "validation_labels": labels,
                    "validation_evidence": validation_evidence,
                }
            )
            connection.execute(
                """
                UPDATE artifacts SET metadata_json=?,created_at=?,validation_status=?
                WHERE artifact_id=?
                """,
                (
                    canonical_json(metadata),
                    artifact_created,
                    "+".join(labels),
                    artifact["artifact_id"],
                ),
            )
            connection.execute(
                "UPDATE jobs SET finished_at=?,heartbeat_at=? WHERE job_id=?",
                (job_finished, job_finished, job_id),
            )
            for label in labels:
                support = [
                    {
                        "validation_id": row["validation_id"],
                        "validator": row["validator"],
                        "claims": json.loads(row["claims_json"]),
                    }
                    for row in rows
                    if label == "GENERATED"
                    or label in json.loads(row["claims_json"])
                ]
                connection.execute(
                    """
                    UPDATE artifact_validation_labels
                    SET evidence_json=?,created_at=?
                    WHERE artifact_id=? AND label=?
                    """,
                    (
                        canonical_json(
                            {"job_id": job_id, "attempt": 1, "support": support}
                        ),
                        job_finished,
                        artifact["artifact_id"],
                        label,
                    ),
                )

    def _complete_repair_builder(
        self, repair_id: str, prior_builder: dict[str, object]
    ) -> dict[str, object]:
        files = self._tree_files(Path(str(prior_builder["path"])))
        artifact = self.fixture._complete_seeded_job(
            repair_id,
            artifact_type=BYOX_REPAIR_ARTIFACT_TYPE,
            files=files,
        )
        self._replace_fixture_validation_with_exact_rows(repair_id)
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT artifact_id,job_id,type,path,checksum,checksum_algorithm,
                       attempt_number,metadata_json
                FROM artifacts WHERE job_id=?
                """,
                (repair_id,),
            ).fetchone()
        self.assertIsNotNone(row)
        assert row is not None
        return {
            **dict(row),
            "artifact_type": row["type"],
            "artifact_checksum": row["checksum"],
            "artifact_attempt": row["attempt_number"],
        }

    def _assert_invalid_without_new_jobs(
        self,
        project_id: str,
        *,
        expected_statuses: set[str],
        expected_reason: str | None = None,
    ) -> dict[str, object]:
        with self.database.connect() as connection:
            before = {
                str(row["job_id"])
                for row in connection.execute("SELECT job_id FROM jobs")
            }
        result = self._seed_repairs(project_id)
        self.assertEqual(0, result["created_jobs"])
        project = result["projects"][project_id]
        self.assertIn(project["status"], expected_statuses)
        if expected_reason is not None:
            self.assertIn(expected_reason, str(project.get("reason", "")))
        with self.database.connect() as connection:
            after = {
                str(row["job_id"])
                for row in connection.execute("SELECT job_id FROM jobs")
            }
        self.assertEqual(before, after)
        return result

    def _coherently_rebuild_publication_evidence(self, job_id: str) -> None:
        with self.database.transaction(immediate=True) as connection:
            job = connection.execute(
                "SELECT attempt_count,finished_at FROM jobs WHERE job_id=?", (job_id,)
            ).fetchone()
            artifact = connection.execute(
                "SELECT artifact_id,metadata_json FROM artifacts WHERE job_id=?",
                (job_id,),
            ).fetchone()
            assert job is not None and artifact is not None
            rows = connection.execute(
                """
                SELECT validation_id,validator,status,evidence_json,claims_json
                FROM validations WHERE job_id=? AND attempt_number=?
                ORDER BY started_at,validation_id
                """,
                (job_id, job["attempt_count"]),
            ).fetchall()
            metadata = json.loads(artifact["metadata_json"])
            metadata["validation_evidence"] = [
                {
                    "validator": row["validator"],
                    "status": row["status"],
                    "evidence": json.loads(row["evidence_json"]),
                }
                for row in rows
            ]
            connection.execute(
                "UPDATE artifacts SET metadata_json=? WHERE artifact_id=?",
                (canonical_json(metadata), artifact["artifact_id"]),
            )
            labels = connection.execute(
                "SELECT label FROM artifact_validation_labels WHERE artifact_id=?",
                (artifact["artifact_id"],),
            ).fetchall()
            for label_row in labels:
                label = str(label_row["label"])
                support = [
                    {
                        "validation_id": row["validation_id"],
                        "validator": row["validator"],
                        "claims": json.loads(row["claims_json"]),
                    }
                    for row in rows
                    if label == "GENERATED"
                    or label in json.loads(row["claims_json"])
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
                                "attempt": job["attempt_count"],
                                "support": support,
                            }
                        ),
                        artifact["artifact_id"],
                        label,
                    ),
                )

    def _first_s2_repair_builder_spec(
        self, project_id: str, graph: dict[str, object]
    ) -> Any:
        with self.database.connect() as connection:
            baseline = load_byox_baseline(connection, str(graph["baseline"]))
            records = {
                str(record["job_id"]): record
                for record in remediation_module._load_policy_jobs(connection)
            }
            self.assertIsNotNone(baseline)
            assert baseline is not None
            lineage = remediation_module.build_byox_s2_lineage_spec(
                baseline,
                gate_job_id=CODEX_BACKEND_GATE_JOB_ID,
            )
            prior_review = remediation_module._validated_review(
                connection,
                records[str(graph["reviewer"])],
                project_id,
                CODEX_BACKEND_GATE_JOB_ID,
                self.settings.warehouse / "artifacts",
                lineage.build_template,
                {},
                baseline_sha256=str(graph["baseline"]),
                s2_lineage=lineage,
            )
        return remediation_module._repair_builder_spec(
            project_id=project_id,
            generation=1,
            prior_review=prior_review,
            template=lineage.build_template,
            gate_job_id=CODEX_BACKEND_GATE_JOB_ID,
            baseline_sha256=str(graph["baseline"]),
        )

    def _first_s2_repair_reviewer_spec(
        self,
        project_id: str,
        baseline_sha256: str,
        repair_id: str,
    ) -> Any:
        repair = self.jobs.get(repair_id)
        self.assertIsNotNone(repair)
        assert repair is not None
        with self.database.connect() as connection:
            artifact = remediation_module._current_artifact(
                connection,
                repair_id,
                expected_type=BYOX_REPAIR_ARTIFACT_TYPE,
                managed_artifact_root=self.settings.warehouse / "artifacts",
            )
        return remediation_module._repair_reviewer_spec(
            project_id=project_id,
            generation=1,
            builder_payload=repair["payload"],
            repaired_artifact=artifact,
            gate_job_id=CODEX_BACKEND_GATE_JOB_ID,
            priority=float(repair["priority"]),
            score_components=repair["score_components"],
            baseline_sha256=baseline_sha256,
        )

    def _insert_unbound_spec(self, spec: Any) -> None:
        self.jobs.create(
            spec.job_type,
            spec.worker_type,
            copy.deepcopy(spec.payload),
            job_id=spec.job_id,
            priority=spec.priority,
            score_components=copy.deepcopy(spec.score_components),
            dependencies=list(spec.dependencies),
            max_attempts=spec.max_attempts,
            model=spec.model,
            reasoning_effort=spec.reasoning_effort,
        )
        expected = make_job_definition(
            job_id=spec.job_id,
            job_type=spec.job_type,
            worker_type=spec.worker_type,
            payload=spec.payload,
            priority=spec.priority,
            score_components=spec.score_components,
            dependencies=spec.dependencies,
            max_attempts=spec.max_attempts,
            model=spec.model,
            reasoning_effort=spec.reasoning_effort,
        )
        with self.database.connect() as connection:
            self.assertEqual(expected, load_job_definition(connection, spec.job_id))

    def _assert_unbound_s2_repair_rejected_on_resume(
        self, project_id: str, job_id: str
    ) -> None:
        with self.database.connect() as connection:
            self.assertIsNone(load_verified_binding(connection, job_id))
        for _ in range(2):
            self._assert_invalid_without_new_jobs(
                project_id,
                expected_statuses={"REMEDIATION_GRAPH_INVALID"},
                expected_reason="binding",
            )

    def test_authorized_attempt_three_success_can_be_reviewed_and_remediated(
        self,
    ) -> None:
        project_id = "project-s2-authorized-attempt-three"
        self._add_project(project_id)
        graph = self._seed_s2(project_id)
        builder_id = str(graph["builder"])
        builder = self.jobs.get(builder_id)
        self.assertIsNotNone(builder)
        assert builder is not None

        _workspace, owner, lease = self._start_job(builder_id)
        self.assertEqual(
            "FAILED",
            self.jobs.fail(
                builder_id,
                owner,
                lease,
                None,
                kind="deterministic",
                error="fixture failure one",
                retryable=False,
            ).value,
        )
        self.jobs.retry(builder_id)
        _workspace, owner, lease = self._claim_retry_attempt(builder_id, 2)
        self.assertEqual(
            "FAILED",
            self.jobs.fail(
                builder_id,
                owner,
                lease,
                None,
                kind="deterministic",
                error="fixture failure two",
                retryable=False,
            ).value,
        )
        self.jobs.retry(builder_id)
        third_workspace, owner, lease = self._claim_retry_attempt(builder_id, 3)
        third = self.jobs.get(builder_id)
        self.assertIsNotNone(third)
        assert third is not None
        self.assertEqual(2, third["max_attempts"])
        self.assertEqual(1, third["retry_allowance"])
        self._write_canonical_pack(third_workspace, builder["payload"])
        builder_artifact = self._publish_running_workspace(
            job_id=builder_id,
            workspace=third_workspace,
            owner=owner,
            lease_token=lease,
            validators=copy.deepcopy(builder["payload"]["validators"]),
            artifact_type=str(builder["payload"]["artifact_type"]),
            semantic_path=str(builder["payload"]["artifact_path"]),
            metadata={},
            attempt_number=3,
        )
        self.assertEqual(3, builder_artifact["artifact_attempt"])

        self._complete_review(
            project_id=project_id,
            reviewer_id=str(graph["reviewer"]),
            builder=builder_artifact,
        )
        remediation = self._seed_repairs(project_id)
        repair_id, _repair = self._assert_s2_repair_builder(
            result=remediation,
            project_id=project_id,
            baseline=str(graph["baseline"]),
            builder_id=builder_id,
            reviewer_id=str(graph["reviewer"]),
        )
        self.assertIsNotNone(self.jobs.get(repair_id))

        successful = self.jobs.get(builder_id)
        assert successful is not None
        inflated = dict(successful)
        inflated["retry_allowance"] = 2
        self.assertFalse(
            remediation_module._job_has_canonical_success_state(
                inflated,
                max_attempts=2,
                managed_artifact_root=(
                    self.settings.warehouse / "artifacts"
                ).resolve(),
            )
        )

    def test_negative_s2_review_seeds_bound_baseline_scoped_repair_pair(self) -> None:
        project_id = "project-s2-negative"
        self._add_project(project_id)
        graph = self._complete_negative_s2(project_id)

        runtime_inode_fields = (
            remediation_module._STAGED_PROVENANCE_RUNTIME_INODE_FIELDS
        )
        with self.database.connect() as connection:
            artifact = connection.execute(
                "SELECT metadata_json FROM artifacts WHERE job_id=?",
                (graph["reviewer"],),
            ).fetchone()
            integrity = connection.execute(
                """
                SELECT evidence_json FROM validations
                WHERE job_id=? AND validator='declared-inputs-remained-immutable'
                """,
                (graph["reviewer"],),
            ).fetchone()
        assert artifact is not None and integrity is not None
        staged_inputs = json.loads(artifact["metadata_json"])["staged_inputs"]
        self.assertEqual(17, len(staged_inputs))
        self.assertTrue(
            all(
                set(item) & runtime_inode_fields == runtime_inode_fields
                for item in staged_inputs
            )
        )
        self.assertEqual(
            {"checked": ["CANDIDATE"], "mismatches": []},
            json.loads(integrity["evidence_json"]),
        )

        first = self._seed_repairs(project_id)
        repair_id, _ = self._assert_s2_repair_builder(
            result=first,
            project_id=project_id,
            baseline=str(graph["baseline"]),
            builder_id=str(graph["builder"]),
            reviewer_id=str(graph["reviewer"]),
        )
        self._complete_repair_builder(repair_id, graph["builder_artifact"])

        second = self._seed_repairs(project_id)
        self.assertEqual(1, second["created_jobs"])
        project = second["projects"][project_id]
        self.assertIn(project["status"], {"REVIEWER_SEEDED", "REPAIR_REVIEWER_SEEDED"})
        repair_reviewer_id = str(project["reviewer"])
        self.assertNotEqual(str(graph["reviewer"]), repair_reviewer_id)
        reviewer = self.jobs.get(repair_reviewer_id)
        self.assertIsNotNone(reviewer)
        assert reviewer is not None
        payload = reviewer["payload"]
        self.assertEqual(
            BYOX_REPAIR_REVIEW_S2_POLICY_KIND,
            payload["seed_policy"]["kind"],
        )
        self.assertEqual(graph["baseline"], payload["baseline_sha256"])
        self.assertEqual(graph["baseline"], payload["seed_policy"]["baseline_sha256"])
        self.assertIn(str(graph["baseline"])[:16], str(payload["artifact_path"]))
        self.assertEqual(
            {CODEX_BACKEND_GATE_JOB_ID, repair_id},
            self._dependencies(repair_reviewer_id),
        )
        with self.database.connect() as connection:
            binding = load_verified_binding(connection, repair_reviewer_id)
        self.assertIsNotNone(binding)
        assert binding is not None
        self.assertEqual("reviewer", binding.role)
        self.assertEqual(graph["baseline"], binding.baseline_sha256)
        self.assertEqual(repair_id, binding.builder_job_id)

    def test_strict_staged_projection_closes_runtime_inode_schema(self) -> None:
        expected = {
            "path": "CANDIDATE/README.md",
            "kind": "file",
            "checksum_algorithm": "file-sha256",
            "checksum": "1" * 64,
        }
        runtime = {
            "fresh_inode_policy": "regular-files-nlink-one-unique-v1",
            "root_device": 1,
            "root_inode": 2,
            "root_change_time_ns": 3,
            "regular_file_count": 1,
            "inode_manifest_sha256": "2" * 64,
        }
        self.assertEqual(
            expected,
            remediation_module._strict_staged_provenance_projection(
                expected, expected=expected
            ),
        )
        self.assertEqual(
            expected,
            remediation_module._strict_staged_provenance_projection(
                {**expected, **runtime}, expected=expected
            ),
        )

        incomplete = {**expected, **runtime}
        incomplete.pop("root_inode")
        malformed_policy = {**expected, **runtime, "fresh_inode_policy": "forged"}
        malformed_integer = {**expected, **runtime, "root_device": True}
        uppercase_digest = {
            **expected,
            **runtime,
            "inode_manifest_sha256": "A" * 64,
        }
        unknown = {**expected, **runtime, "unexpected": True}
        for name, record in (
            ("incomplete", incomplete),
            ("policy", malformed_policy),
            ("integer", malformed_integer),
            ("digest", uppercase_digest),
            ("unknown", unknown),
        ):
            with self.subTest(name=name), self.assertRaises(
                remediation_module.ByoxRemediationError
            ):
                remediation_module._strict_staged_provenance_projection(
                    record, expected=expected
                )

    def test_s2_review_rejects_partial_runtime_inode_provenance(self) -> None:
        project_id = "project-s2-partial-inode-provenance"
        self._add_project(project_id)
        graph = self._complete_negative_s2(project_id)
        with self.database.transaction(immediate=True) as connection:
            artifact = connection.execute(
                "SELECT artifact_id,metadata_json FROM artifacts WHERE job_id=?",
                (graph["reviewer"],),
            ).fetchone()
            assert artifact is not None
            metadata = json.loads(artifact["metadata_json"])
            metadata["staged_inputs"][0].pop("root_inode")
            connection.execute(
                "UPDATE artifacts SET metadata_json=? WHERE artifact_id=?",
                (canonical_json(metadata), artifact["artifact_id"]),
            )

        self._assert_invalid_without_new_jobs(
            project_id,
            expected_statuses={"REMEDIATION_EVIDENCE_INVALID"},
        )

    def test_s2_review_rejects_leaf_integrity_evidence(self) -> None:
        project_id = "project-s2-leaf-integrity-evidence"
        self._add_project(project_id)
        graph = self._complete_negative_s2(project_id)
        reviewer = self.jobs.get(str(graph["reviewer"]))
        assert reviewer is not None
        leaf_evidence = {
            "checked": [
                str(item["destination"])
                for item in reviewer["payload"]["inputs_from_dependencies"]
            ],
            "mismatches": [],
        }
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                """
                UPDATE validations SET evidence_json=?
                WHERE job_id=? AND validator='declared-inputs-remained-immutable'
                """,
                (canonical_json(leaf_evidence), graph["reviewer"]),
            )
        self._coherently_rebuild_publication_evidence(str(graph["reviewer"]))

        self._assert_invalid_without_new_jobs(
            project_id,
            expected_statuses={"REMEDIATION_EVIDENCE_INVALID"},
        )

    def test_unbound_exact_s2_repair_builder_is_rejected_on_resume(self) -> None:
        project_id = "project-s2-unbound-repair-builder"
        self._add_project(project_id)
        graph = self._complete_negative_s2(project_id)
        repair = self._first_s2_repair_builder_spec(project_id, graph)
        self._insert_unbound_spec(repair)

        self._assert_unbound_s2_repair_rejected_on_resume(
            project_id,
            str(repair.job_id),
        )

    def test_unbound_exact_s2_repair_reviewer_is_rejected_on_resume(self) -> None:
        project_id = "project-s2-unbound-repair-reviewer"
        self._add_project(project_id)
        graph = self._complete_negative_s2(project_id)
        seeded = self._seed_repairs(project_id)
        repair_id, _ = self._assert_s2_repair_builder(
            result=seeded,
            project_id=project_id,
            baseline=str(graph["baseline"]),
            builder_id=str(graph["builder"]),
            reviewer_id=str(graph["reviewer"]),
        )
        self._complete_repair_builder(repair_id, graph["builder_artifact"])
        reviewer = self._first_s2_repair_reviewer_spec(
            project_id,
            str(graph["baseline"]),
            repair_id,
        )
        self._insert_unbound_spec(reviewer)

        self._assert_unbound_s2_repair_rejected_on_resume(
            project_id,
            str(reviewer.job_id),
        )

    def test_material_drift_selects_only_the_new_active_baseline(self) -> None:
        project_id = "project-s2-drift"
        self._add_project(project_id, title="Baseline A")
        first_graph = self._complete_negative_s2(project_id)
        first_result = self._seed_repairs(project_id)
        first_repair, first_row = self._assert_s2_repair_builder(
            result=first_result,
            project_id=project_id,
            baseline=str(first_graph["baseline"]),
            builder_id=str(first_graph["builder"]),
            reviewer_id=str(first_graph["reviewer"]),
        )

        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                "UPDATE build_projects SET title='Baseline B' WHERE project_id=?",
                (project_id,),
            )
        second_graph = self._seed_s2(project_id)
        self.assertNotEqual(first_graph["baseline"], second_graph["baseline"])
        self.assertNotEqual(first_graph["builder"], second_graph["builder"])
        self.assertNotEqual(first_graph["reviewer"], second_graph["reviewer"])

        waiting = self._seed_repairs(project_id)
        self.assertEqual(0, waiting["created_jobs"])
        self.assertIn(
            waiting["projects"][project_id]["status"],
            {"WAITING_FOR_CURRENT_REVIEW", "NO_CURRENT_REVIEW"},
        )
        self.assertEqual(first_row, self.jobs.get(first_repair))

        second_builder = self._complete_builder(str(second_graph["builder"]))
        self._complete_review(
            project_id=project_id,
            reviewer_id=str(second_graph["reviewer"]),
            builder=second_builder,
        )
        second_result = self._seed_repairs(project_id)
        second_repair, second_row = self._assert_s2_repair_builder(
            result=second_result,
            project_id=project_id,
            baseline=str(second_graph["baseline"]),
            builder_id=str(second_graph["builder"]),
            reviewer_id=str(second_graph["reviewer"]),
        )
        self.assertNotEqual(first_repair, second_repair)
        self.assertNotEqual(
            first_row["payload"]["artifact_path"],
            second_row["payload"]["artifact_path"],
        )
        self.assertEqual(first_row, self.jobs.get(first_repair))

    def test_valid_legacy_history_cannot_poison_or_replace_bound_s2(self) -> None:
        project_id = "project-s2-legacy-separation"
        self._add_project(project_id)
        graph = self._complete_negative_s2(project_id)
        legacy_builder, legacy_review, _, _ = self.fixture._base_graph(
            project_id, "FAIL"
        )

        result = self._seed_repairs(project_id)
        repair_id, repair = self._assert_s2_repair_builder(
            result=result,
            project_id=project_id,
            baseline=str(graph["baseline"]),
            builder_id=str(graph["builder"]),
            reviewer_id=str(graph["reviewer"]),
        )
        repair_dependencies = self._dependencies(repair_id)
        self.assertNotIn(legacy_builder, repair_dependencies)
        self.assertNotIn(legacy_review, repair_dependencies)
        self.assertNotEqual(
            remediation_module.repair_builder_job_id(project_id, 1), repair_id
        )

    def test_unbound_s2_lookalike_fails_closed(self) -> None:
        project_id = "project-s2-unbound-fork"
        self._add_project(project_id)
        graph = self._complete_negative_s2(project_id)
        real = self.jobs.get(str(graph["reviewer"]))
        assert real is not None
        with self.database.connect() as connection:
            dependencies = [
                str(row["depends_on_job_id"])
                for row in connection.execute(
                    """
                    SELECT depends_on_job_id FROM job_dependencies
                    WHERE job_id=? ORDER BY depends_on_job_id
                    """,
                    (graph["reviewer"],),
                )
            ]
        forged = copy.deepcopy(real["payload"])
        forged["provenance"]["supersedes_reviewer_job_id"] = graph["reviewer"]
        self.jobs.create(
            "codex_task",
            "examiner",
            forged,
            job_id="job_byox_review_s2_p999_unbound_contract_fork",
            priority=float(real["priority"]),
            score_components=real["score_components"],
            dependencies=dependencies,
            max_attempts=2,
            model="gpt-5.6-sol",
            reasoning_effort="ultra",
        )

        self._assert_invalid_without_new_jobs(
            project_id,
            expected_statuses={
                "REMEDIATION_EVIDENCE_INVALID",
                "REMEDIATION_GRAPH_INVALID",
            },
            expected_reason="lacks an immutable baseline binding",
        )

    def _insert_bound_s2_review_successor(
        self,
        *,
        baseline_sha256: str,
        builder_id: str,
        version: int,
        supersedes: str,
    ) -> str:
        with self.database.connect() as connection:
            baseline = load_byox_baseline(connection, baseline_sha256)
            builder_definition = load_job_definition(connection, builder_id)
            base_reviewer_id = byox_s2_reviewer_job_id(
                baseline_sha256,
                builder_id,
                review_contract_version=BYOX_REVIEW_CONTRACT_VERSION,
            )
            base_definition = load_job_definition(connection, base_reviewer_id)
        assert baseline is not None
        assert builder_definition is not None
        assert base_definition is not None
        builder_payload = builder_definition.payload()
        payload = _byox_reviewer_payload(
            project_id=baseline.project_id,
            builder_job_id=builder_id,
            builder_payload=builder_payload,
            specialized=False,
            policy_version=version,
            supersedes_reviewer_job_id=supersedes,
        )
        payload.update(
            {
                "seed_policy": {
                    "kind": BYOX_REVIEW_S2_POLICY_KIND,
                    "version": version,
                    "role": "reviewer",
                    "baseline_sha256": baseline_sha256,
                    "baseline_schema_version": baseline.schema_version,
                },
                "baseline_sha256": baseline_sha256,
                "baseline_schema_version": baseline.schema_version,
            }
        )
        payload = with_mass_seed_backend_policy(payload)
        reviewer_id = byox_s2_reviewer_job_id(
            baseline_sha256,
            builder_id,
            review_contract_version=version,
        )
        definition = make_job_definition(
            job_id=reviewer_id,
            job_type=base_definition.job_type,
            worker_type=base_definition.worker_type,
            payload=payload,
            priority=base_definition.priority,
            score_components=base_definition.score_components(),
            dependencies=base_definition.dependencies,
            max_attempts=base_definition.max_attempts,
            model=base_definition.model,
            reasoning_effort=base_definition.reasoning_effort,
        )
        with self.database.transaction(immediate=True) as connection:
            insert_or_verify_bound_job(
                self.database,
                connection,
                baseline,
                definition,
                role="reviewer",
                policy_version=version,
                builder_job_id=builder_id,
                created_at=now(),
                bound_at=now(),
            )
        return reviewer_id

    def test_bound_s2_reviewer_fork_is_not_resolved_by_highest_version(self) -> None:
        project_id = "project-s2-bound-fork"
        self._add_project(project_id)
        graph = self._complete_negative_s2(project_id)
        base = str(graph["reviewer"])
        self._insert_bound_s2_review_successor(
            baseline_sha256=str(graph["baseline"]),
            builder_id=str(graph["builder"]),
            version=3,
            supersedes=base,
        )
        self._insert_bound_s2_review_successor(
            baseline_sha256=str(graph["baseline"]),
            builder_id=str(graph["builder"]),
            version=4,
            supersedes=base,
        )

        self._assert_invalid_without_new_jobs(
            project_id,
            expected_statuses={"REMEDIATION_EVIDENCE_INVALID"},
            expected_reason="unadmitted fork",
        )

    def test_s2_reviewer_must_start_after_its_builder_finishes(self) -> None:
        project_id = "project-s2-causality"
        self._add_project(project_id)
        graph = self._complete_negative_s2(project_id)
        with self.database.transaction(immediate=True) as connection:
            builder = connection.execute(
                "SELECT started_at,finished_at FROM jobs WHERE job_id=?",
                (graph["builder"],),
            ).fetchone()
            assert builder is not None
            impossible_start = (
                float(builder["started_at"]) + float(builder["finished_at"])
            ) / 2.0
            connection.execute(
                "UPDATE jobs SET started_at=? WHERE job_id=?",
                (impossible_start, graph["reviewer"]),
            )

        self._assert_invalid_without_new_jobs(
            project_id,
            expected_statuses={
                "REMEDIATION_EVIDENCE_INVALID",
                "REMEDIATION_GRAPH_INVALID",
            },
        )

    def test_exact_s2_validator_envelope_rejects_opaque_command_fields(self) -> None:
        mutations = (
            ("command_json", canonical_json(["true"])),
            ("exit_code", 0),
            ("stdout_path", "/tmp/forged-validation.stdout"),
            ("stderr_path", "/tmp/forged-validation.stderr"),
        )
        for index, (column, value) in enumerate(mutations, start=1):
            project_id = f"project-s2-envelope-{index}"
            self._add_project(project_id)
            graph = self._complete_negative_s2(project_id)
            clean = self._seed_repairs(project_id)
            self._assert_s2_repair_builder(
                result=clean,
                project_id=project_id,
                baseline=str(graph["baseline"]),
                builder_id=str(graph["builder"]),
                reviewer_id=str(graph["reviewer"]),
            )
            with self.database.transaction(immediate=True) as connection:
                validation = connection.execute(
                    """
                    SELECT validation_id FROM validations
                    WHERE job_id=? ORDER BY started_at,validation_id LIMIT 1
                    """,
                    (graph["builder"],),
                ).fetchone()
                assert validation is not None
                connection.execute(
                    f"UPDATE validations SET {column}=? WHERE validation_id=?",
                    (value, validation["validation_id"]),
                )
            with self.subTest(column=column):
                self._assert_invalid_without_new_jobs(
                    project_id,
                    expected_statuses={"REMEDIATION_EVIDENCE_INVALID"},
                )

    def test_exact_s2_validator_set_rejects_coherent_name_and_evidence_forgery(
        self,
    ) -> None:
        attacks = ("name", "evidence", "extra")
        for index, attack in enumerate(attacks, start=1):
            project_id = f"project-s2-validator-set-{index}"
            self._add_project(project_id)
            graph = self._complete_negative_s2(project_id)
            clean = self._seed_repairs(project_id)
            self._assert_s2_repair_builder(
                result=clean,
                project_id=project_id,
                baseline=str(graph["baseline"]),
                builder_id=str(graph["builder"]),
                reviewer_id=str(graph["reviewer"]),
            )
            with self.database.transaction(immediate=True) as connection:
                validation = connection.execute(
                    """
                    SELECT * FROM validations WHERE job_id=?
                    ORDER BY started_at,validation_id LIMIT 1
                    """,
                    (graph["builder"],),
                ).fetchone()
                assert validation is not None
                if attack == "name":
                    connection.execute(
                        "UPDATE validations SET validator='forged-validator-name' WHERE validation_id=?",
                        (validation["validation_id"],),
                    )
                elif attack == "evidence":
                    connection.execute(
                        "UPDATE validations SET evidence_json=? WHERE validation_id=?",
                        (canonical_json({"forged": True}), validation["validation_id"]),
                    )
                else:
                    connection.execute(
                        """
                        INSERT INTO validations(
                            validation_id,job_id,validator,status,command_json,
                            exit_code,stdout_path,stderr_path,evidence_json,
                            started_at,finished_at,attempt_number,claims_json
                        ) VALUES (?,?,?,'PASS',NULL,NULL,NULL,NULL,?,?,?,?,?)
                        """,
                        (
                            f"validation_{graph['builder']}_forged_extra",
                            graph["builder"],
                            "forged-extra-validator",
                            canonical_json({"forged": True}),
                            validation["started_at"],
                            validation["finished_at"],
                            1,
                            canonical_json(["PARTIAL"]),
                        ),
                    )
            self._coherently_rebuild_publication_evidence(str(graph["builder"]))
            with self.subTest(attack=attack):
                self._assert_invalid_without_new_jobs(
                    project_id,
                    expected_statuses={"REMEDIATION_EVIDENCE_INVALID"},
                )


if __name__ == "__main__":
    unittest.main()
