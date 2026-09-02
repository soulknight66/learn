from __future__ import annotations

import copy
import json
import shutil
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import learnfactory.byox_remediation as remediation_module
import learnfactory.handlers as handlers_module
from learnfactory.backend_policy import with_mass_seed_backend_policy
from learnfactory.byox_baselines import (
    byox_remediation_binding_policy_version,
    byox_s2_reviewer_job_id,
    insert_or_verify_bound_job,
    job_definition_sha256,
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
from learnfactory.validation import (
    ByoxCodeManifest,
    ByoxCodeManifestEntry,
    Validator,
)
from learnfactory.worker import _validation_labels
import tests.test_byox_remediation as legacy_tests


ROOT = Path(__file__).resolve().parents[1]


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

    def test_exact_audit_allowlist_binds_only_the_declared_successor(self) -> None:
        [audit] = remediation_module._s2_audit_reissue_allowlist()
        audited = audit["audited_builder"]
        finding = audit["finding"]
        sources = tuple(
            ByoxCodeManifestEntry(
                path=str(item["path"]),
                kind="file",
                mode=0o444,
                size_bytes=1,
                sha256=str(item["sha256"]),
            )
            for item in finding["candidate_sources"]
        )
        snapshot = remediation_module._DescriptorTreeSnapshot(
            checksum=str(audited["artifact_checksum"]),
            entries=len(sources),
            files=len(sources),
            total_bytes=len(sources),
            required_files={},
            required_sha256={},
            paths=tuple(item.path for item in sources),
            root_kinds={"sealed": "directory"},
            code_manifest=ByoxCodeManifest(entries=sources, scope="full-tree"),
        )
        artifact = remediation_module.ArtifactBinding(
            job_id=str(audited["job_id"]),
            artifact_id=str(audited["artifact_id"]),
            artifact_type=str(audited["artifact_type"]),
            artifact_checksum=str(audited["artifact_checksum"]),
            checksum_algorithm=str(audited["checksum_algorithm"]),
            artifact_attempt=int(audited["artifact_attempt"]),
            artifact_path=Path("/controller/audited-artifact"),
            artifact_created_at=1.0,
            tree_snapshot=snapshot,
        )

        accepted = remediation_module._require_s2_audited_artifact(
            audit,
            artifact,
            remediation_policy_version=1,
            generation=2,
        )
        self.assertEqual(audit, accepted)
        self.assertEqual(
            "9768c1e824f3afcf1d3668dbf93c7ce0c7ee31a1783e44fc0e7ee791b2461985",
            audit["audit_sha256"],
        )
        self.assertIsNone(
            remediation_module._s2_audit_reissue_for_lineage(
                "project-not-allowlisted", str(audit["baseline_sha256"])
            )
        )
        self.assertIsNone(
            remediation_module._s2_audit_reissue_for_lineage(
                str(audit["project_id"]), "0" * 64
            )
        )

        artifact_mutations = (
            replace(artifact, job_id="job_wrong"),
            replace(artifact, artifact_id="artifact_wrong"),
            replace(artifact, artifact_attempt=2),
            replace(artifact, artifact_checksum="0" * 64),
            replace(artifact, checksum_algorithm="sha256"),
            replace(
                artifact,
                tree_snapshot=replace(snapshot, checksum="0" * 64),
            ),
            replace(
                artifact,
                tree_snapshot=replace(
                    snapshot,
                    code_manifest=ByoxCodeManifest(
                        entries=(replace(sources[0], sha256="0" * 64), *sources[1:]),
                        scope="full-tree",
                    ),
                ),
            ),
        )
        for mutated in artifact_mutations:
            with self.subTest(mutation=mutated):
                with self.assertRaises(remediation_module.ByoxRemediationError):
                    remediation_module._require_s2_audited_artifact(
                        audit,
                        mutated,
                        remediation_policy_version=1,
                        generation=2,
                    )

        counterfeit = copy.deepcopy(audit)
        counterfeit["finding"]["probe_source_sha256"] = "0" * 64
        counterfeit_body = {
            key: value
            for key, value in counterfeit.items()
            if key != "audit_sha256"
        }
        counterfeit["audit_sha256"] = remediation_module._s2_audit_sha256(
            counterfeit_body
        )
        with self.assertRaises(remediation_module.ByoxRemediationError):
            remediation_module._require_s2_audited_artifact(
                counterfeit,
                artifact,
                remediation_policy_version=1,
                generation=2,
            )

        baseline = str(audit["baseline_sha256"])
        project = str(audit["project_id"])
        self.assertEqual(
            "job_byox_repair_s2_v2_g2_ba9f7fea43e4c4ec88ead0a44f75ec77",
            remediation_module.repair_builder_job_id(
                project,
                2,
                baseline_sha256=baseline,
                remediation_policy_version=2,
            ),
        )
        self.assertEqual(
            "job_byox_repair_review_s2_v2_g2_219042700e8392cd6591bd6441ff449d",
            remediation_module.repair_reviewer_job_id(
                project,
                2,
                baseline_sha256=baseline,
                remediation_policy_version=2,
            ),
        )
        self.assertEqual(2_000_002, byox_remediation_binding_policy_version(2, 2))

    def test_audited_v1_g2_review_feeds_exact_v2_g2_four_input_cutover(self) -> None:
        [audit] = remediation_module._s2_audit_reissue_allowlist()
        audited = audit["audited_builder"]
        sources = tuple(
            ByoxCodeManifestEntry(
                path=str(item["path"]),
                kind="file",
                sha256=str(item["sha256"]),
            )
            for item in audit["finding"]["candidate_sources"]
        )
        snapshot = remediation_module._DescriptorTreeSnapshot(
            checksum=str(audited["artifact_checksum"]),
            entries=len(sources),
            files=len(sources),
            total_bytes=2,
            required_files={},
            required_sha256={},
            paths=tuple(item.path for item in sources),
            root_kinds={"sealed": "directory"},
            code_manifest=ByoxCodeManifest(entries=sources, scope="full-tree"),
        )
        audited_artifact = remediation_module.ArtifactBinding(
            job_id=str(audited["job_id"]),
            artifact_id=str(audited["artifact_id"]),
            artifact_type=str(audited["artifact_type"]),
            artifact_checksum=str(audited["artifact_checksum"]),
            checksum_algorithm=str(audited["checksum_algorithm"]),
            artifact_attempt=int(audited["artifact_attempt"]),
            artifact_path=Path("/controller/audited-artifact"),
            artifact_created_at=1.0,
            tree_snapshot=snapshot,
        )
        project_id = str(audit["project_id"])
        baseline = str(audit["baseline_sha256"])
        audit_reviewer = remediation_module._repair_reviewer_spec(
            project_id=project_id,
            generation=2,
            builder_payload={
                "artifact_profile": "byox-generic-v1",
                "remediation_snapshot": {"policy_version": 1, "generation": 2},
            },
            repaired_artifact=audited_artifact,
            gate_job_id=CODEX_BACKEND_GATE_JOB_ID,
            priority=90.0,
            score_components={"fixture": 1},
            baseline_sha256=baseline,
            remediation_policy_version=1,
            controller_audit=audit,
        )
        self.assertEqual(
            "job_byox_repair_review_s2_v1_g2_50d779aa215424e4d3cd7b0a088ed3be",
            audit_reviewer.job_id,
        )
        verdict_spec = next(
            item
            for item in audit_reviewer.payload["validators"]
            if item["type"] == "review_verdict"
        )
        audit_entry = f"controller-audit-sha256:{audit['audit_sha256']}"
        self.assertEqual(["REVISE", "FAIL"], verdict_spec["allowed_verdicts"])
        self.assertEqual(
            [audit_entry], verdict_spec["required_evidence_entries"]
        )

        review_artifact = replace(
            audited_artifact,
            job_id=audit_reviewer.job_id,
            artifact_id="artifact_audited_review",
            artifact_type="byox-independent-review",
            artifact_checksum="1" * 64,
            artifact_attempt=1,
        )
        prior_review = remediation_module.ValidatedReview(
            project_id=project_id,
            review_job_id=audit_reviewer.job_id,
            review_policy_version=102,
            verdict="REVISE",
            validation_id="validation_audited_review",
            validation_evidence_sha256="2" * 64,
            builder_profile="byox-generic-v1",
            builder_max_attempts=2,
            builder=audited_artifact,
            review=review_artifact,
            controller_audit=audit,
        )
        template = SimpleNamespace(
            payload={
                "prompt": "immutable baseline prompt",
                "validators": [],
                "provenance": {"baseline_sha256": baseline},
            },
            priority=90.0,
            score_components={"fixture": 1},
        )
        successor = remediation_module._repair_builder_spec(
            project_id=project_id,
            generation=2,
            prior_review=prior_review,
            template=template,
            gate_job_id=CODEX_BACKEND_GATE_JOB_ID,
            baseline_sha256=baseline,
            remediation_policy_version=2,
        )
        self.assertEqual(
            "job_byox_repair_s2_v2_g2_ba9f7fea43e4c4ec88ead0a44f75ec77",
            successor.job_id,
        )
        self.assertEqual(
            (
                CODEX_BACKEND_GATE_JOB_ID,
                str(audited["job_id"]),
                audit_reviewer.job_id,
            ),
            successor.dependencies,
        )
        self.assertEqual(
            [
                "PRIOR_BUILD",
                "PRIOR_REVIEW/EVALUATION.json",
                "PRIOR_REVIEW/REVIEW.md",
                "PRIOR_REVIEW/VALIDATION.md",
            ],
            [
                item["destination"]
                for item in successor.payload["inputs_from_dependencies"]
            ],
        )
        self.assertEqual(2, successor.payload["seed_policy"]["version"])
        supersession = successor.payload["remediation_snapshot"]["supersession"]
        self.assertEqual(1, supersession["supersedes_remediation_policy_version"])
        self.assertEqual(2, supersession["supersedes_remediation_generation"])
        self.assertEqual(
            audit["audit_sha256"], supersession["controller_audit_sha256"]
        )

        successor_artifact = replace(
            audited_artifact,
            job_id=successor.job_id,
            artifact_id="artifact_successor",
            artifact_checksum="3" * 64,
            tree_snapshot=replace(snapshot, checksum="3" * 64),
        )
        successor_reviewer = remediation_module._repair_reviewer_spec(
            project_id=project_id,
            generation=2,
            builder_payload=successor.payload,
            repaired_artifact=successor_artifact,
            gate_job_id=CODEX_BACKEND_GATE_JOB_ID,
            priority=successor.priority,
            score_components=successor.score_components,
            baseline_sha256=baseline,
            remediation_policy_version=2,
        )
        self.assertEqual(
            "job_byox_repair_review_s2_v2_g2_219042700e8392cd6591bd6441ff449d",
            successor_reviewer.job_id,
        )
        self.assertEqual(202, successor_reviewer.payload["seed_policy"]["version"])
        successor_verdict = next(
            item
            for item in successor_reviewer.payload["validators"]
            if item["type"] == "review_verdict"
        )
        self.assertNotIn("allowed_verdicts", successor_verdict)
        self.assertNotIn("required_evidence_entries", successor_verdict)

    @unittest.skipUnless(
        (ROOT / "warehouse" / "factory.db").is_file(),
        "checked-in audited lineage is unavailable",
    )
    def test_archived_audit_lineage_converges_once_and_never_creates_g3(self) -> None:
        target_artifact = self._install_archived_audit_lineage()
        project_id = "project_fc8ca1dbad4baba3bd2d54dbb42c1a98"
        baseline = "7bc89daf0774fa3ef7a4a289b88303a0621079ebd035bf47f10009e402340424"
        v1_builder = str(target_artifact["job_id"])
        v1_reviewer = (
            "job_byox_repair_review_s2_v1_g2_50d779aa215424e4d3cd7b0a088ed3be"
        )
        v2_builder = (
            "job_byox_repair_s2_v2_g2_ba9f7fea43e4c4ec88ead0a44f75ec77"
        )
        v2_reviewer = (
            "job_byox_repair_review_s2_v2_g2_219042700e8392cd6591bd6441ff449d"
        )

        first = self._seed_repairs(project_id)
        self.assertEqual(1, first["created_jobs"])
        self.assertEqual(
            "REVIEWER_SEEDED", first["projects"][project_id]["status"]
        )
        self.assertEqual(v1_reviewer, first["projects"][project_id]["reviewer"])
        again = self._seed_repairs(project_id)
        self.assertEqual(0, again["created_jobs"])
        self.assertEqual(
            "WAITING_FOR_REVIEWER", again["projects"][project_id]["status"]
        )
        with self.database.connect() as connection:
            v1_binding = load_verified_binding(connection, v1_reviewer)
        self.assertIsNotNone(v1_binding)
        assert v1_binding is not None
        self.assertEqual(1_000_002, v1_binding.policy_version)

        audit = remediation_module._s2_audit_reissue_for_lineage(
            project_id, baseline
        )
        self.assertIsNotNone(audit)
        assert audit is not None
        token = f"controller-audit-sha256:{audit['audit_sha256']}"
        self._complete_review(
            project_id=project_id,
            reviewer_id=v1_reviewer,
            builder=target_artifact,
            verdict="REVISE",
            evidence_entries=[token, "reproduced stale-return slot reuse"],
        )

        seeded_v2 = self._seed_repairs(project_id)
        self.assertEqual(1, seeded_v2["created_jobs"])
        self.assertEqual(v2_builder, seeded_v2["projects"][project_id]["builder"])
        self.assertEqual(
            2, seeded_v2["projects"][project_id]["remediation_policy_version"]
        )
        with self.database.connect() as connection:
            builder_binding = load_verified_binding(connection, v2_builder)
        self.assertIsNotNone(builder_binding)
        assert builder_binding is not None
        self.assertEqual(2_000_002, builder_binding.policy_version)
        self.assertEqual(
            {CODEX_BACKEND_GATE_JOB_ID, v1_builder, v1_reviewer},
            self._dependencies(v2_builder),
        )

        v2_artifact = self._complete_repair_builder(v2_builder, target_artifact)
        seeded_reviewer = self._seed_repairs(project_id)
        self.assertEqual(1, seeded_reviewer["created_jobs"])
        self.assertEqual(
            v2_reviewer, seeded_reviewer["projects"][project_id]["reviewer"]
        )
        with self.database.connect() as connection:
            reviewer_binding = load_verified_binding(connection, v2_reviewer)
        self.assertIsNotNone(reviewer_binding)
        assert reviewer_binding is not None
        self.assertEqual(2_000_002, reviewer_binding.policy_version)
        self.assertEqual(v2_builder, reviewer_binding.builder_job_id)

        self._complete_review(
            project_id=project_id,
            reviewer_id=v2_reviewer,
            builder=v2_artifact,
            verdict="REVISE",
        )
        exhausted = seed_byox_remediation_jobs(
            self.database,
            self.jobs,
            warehouse=self.settings.warehouse,
            project_ids=[project_id],
            max_repair_generations=10,
        )
        self.assertEqual(0, exhausted["created_jobs"])
        self.assertEqual(
            "REPAIR_LIMIT_EXHAUSTED",
            exhausted["projects"][project_id]["status"],
        )
        self.assertEqual(
            2, exhausted["projects"][project_id]["hard_generation_ceiling"]
        )
        for policy_version in (1, 2, 3):
            self.assertIsNone(
                self.jobs.get(
                    remediation_module.repair_builder_job_id(
                        project_id,
                        3,
                        baseline_sha256=baseline,
                        remediation_policy_version=policy_version,
                    )
                    )
                )

    @unittest.skipUnless(
        (ROOT / "warehouse" / "factory.db").is_file(),
        "checked-in audited lineage is unavailable",
    )
    def test_malformed_exact_deterministic_g3_builder_poison_audit_lineage(
        self,
    ) -> None:
        self._install_archived_audit_lineage()
        project_id = "project_fc8ca1dbad4baba3bd2d54dbb42c1a98"
        baseline = "7bc89daf0774fa3ef7a4a289b88303a0621079ebd035bf47f10009e402340424"
        generation = 3
        job_id = remediation_module.repair_builder_job_id(
            project_id,
            generation,
            baseline_sha256=baseline,
            remediation_policy_version=1,
        )
        self.jobs.create(
            "codex_task",
            "reference_builder",
            {
                "project_id": project_id,
                "baseline_sha256": baseline,
                "remediation_generation": generation,
                "seed_policy": {
                    "kind": f"{BYOX_REPAIR_S2_POLICY_KIND}_typo",
                    "version": 1,
                    "role": "builder",
                    "generation": generation,
                    "baseline_sha256": baseline,
                },
            },
            job_id=job_id,
            max_attempts=2,
        )

        self._assert_invalid_without_new_jobs(
            project_id,
            expected_statuses={
                "REMEDIATION_EVIDENCE_INVALID",
                "REMEDIATION_GRAPH_INVALID",
            },
        )

    @unittest.skipUnless(
        (ROOT / "warehouse" / "factory.db").is_file(),
        "checked-in audited lineage is unavailable",
    )
    def test_unexpected_same_baseline_bound_builder_poison_audit_lineage(
        self,
    ) -> None:
        self._install_archived_audit_lineage()
        project_id = "project_fc8ca1dbad4baba3bd2d54dbb42c1a98"
        baseline = "7bc89daf0774fa3ef7a4a289b88303a0621079ebd035bf47f10009e402340424"
        generation = 3
        job_id = "job_unexpected_same_baseline_bound_builder"
        self.jobs.create(
            "codex_task",
            "reference_builder",
            {
                "project_id": project_id,
                "baseline_sha256": baseline,
                "remediation_generation": generation,
                "seed_policy": {
                    "kind": f"{BYOX_REPAIR_S2_POLICY_KIND}_typo",
                    "version": 1,
                    "role": "builder",
                    "generation": generation,
                    "baseline_sha256": baseline,
                },
            },
            job_id=job_id,
            max_attempts=2,
        )
        with self.database.transaction(immediate=True) as connection:
            definition = load_job_definition(connection, job_id)
            self.assertIsNotNone(definition)
            assert definition is not None
            connection.execute(
                """
                INSERT INTO byox_baseline_job_bindings(
                    job_id,baseline_sha256,role,policy_version,builder_job_id,
                    definition_sha256,bound_at
                ) VALUES (?,?,'builder',?,NULL,?,?)
                """,
                (
                    job_id,
                    baseline,
                    byox_remediation_binding_policy_version(1, generation),
                    job_definition_sha256(definition),
                    now(),
                ),
            )

        self._assert_invalid_without_new_jobs(
            project_id,
            expected_statuses={
                "REMEDIATION_EVIDENCE_INVALID",
                "REMEDIATION_GRAPH_INVALID",
            },
        )

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
        root_inventory: dict[str, object] | None = None
        if any(
            isinstance(item, dict) and item.get("artifact_root") is True
            for item in declarations
        ):
            with self.database.connect() as connection:
                binding = remediation_module._current_artifact(
                    connection,
                    str(builder["job_id"]),
                    expected_type=str(builder["artifact_type"]),
                    managed_artifact_root=self.settings.warehouse / "artifacts",
                )
            root_inventory = binding.artifact_inventory
        staged: list[dict[str, object]] = []
        for item in declarations:
            assert isinstance(item, dict)
            subpath = "." if item.get("artifact_root") is True else str(item["subpath"])
            source = source_root if subpath == "." else source_root / subpath
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
                    **(
                        {"artifact_inventory": root_inventory}
                        if root_inventory is not None
                        else {}
                    ),
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
        evidence_entries: list[str] | None = None,
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
                    "evidence": evidence_entries
                    or ["independent contract fixture finding"],
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

    def _install_archived_audit_lineage(self) -> dict[str, object]:
        """Copy the checked-in audited lineage into this test's isolated store."""

        source_database = ROOT / "warehouse" / "factory.db"
        shutil.copy2(source_database, self.settings.database)
        target_job_id = (
            "job_byox_repair_s2_v1_g2_70a90b5934bcf838b167251b70a24f39"
        )
        job_ids = {target_job_id}
        frontier = {target_job_id}
        with self.database.connect() as connection:
            while frontier:
                placeholders = ",".join("?" for _value in frontier)
                dependencies = {
                    str(row["depends_on_job_id"])
                    for row in connection.execute(
                        f"""
                        SELECT depends_on_job_id FROM job_dependencies
                        WHERE job_id IN ({placeholders})
                        """,
                        tuple(sorted(frontier)),
                    )
                }
                frontier = dependencies - job_ids
                job_ids.update(frontier)
            placeholders = ",".join("?" for _value in job_ids)
            artifacts = connection.execute(
                f"""
                SELECT artifact_id,job_id,path FROM artifacts
                WHERE job_id IN ({placeholders})
                ORDER BY artifact_id
                """,
                tuple(sorted(job_ids)),
            ).fetchall()

        relocated: dict[str, str] = {}
        source_artifact_root = (ROOT / "warehouse" / "artifacts").resolve()
        fixture_root = (self.settings.warehouse / "artifacts").resolve()
        for row in artifacts:
            source = Path(str(row["path"])).resolve()
            destination = fixture_root / source.relative_to(source_artifact_root)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(source, destination, dirs_exist_ok=True)
            relocated[str(row["artifact_id"])] = str(destination.resolve())
        with self.database.transaction(immediate=True) as connection:
            for artifact_id, path in relocated.items():
                connection.execute(
                    "UPDATE artifacts SET path=? WHERE artifact_id=?",
                    (path, artifact_id),
                )
            for job_id in job_ids:
                row = connection.execute(
                    "SELECT state,attempt_count FROM jobs WHERE job_id=?",
                    (job_id,),
                ).fetchone()
                if row is not None and row["state"] == "SUCCEEDED":
                    workspace = (
                        self.settings.warehouse
                        / "workspaces"
                        / job_id
                        / f"attempt-{int(row['attempt_count']):03d}"
                    ).resolve()
                    connection.execute(
                        "UPDATE jobs SET workspace=? WHERE job_id=?",
                        (str(workspace), job_id),
                    )
            source_warehouse = str((ROOT / "warehouse").resolve())
            target_warehouse = str(self.settings.warehouse.resolve())
            connection.execute(
                """
                UPDATE validations
                SET stdout_path=replace(stdout_path, ?, ?),
                    stderr_path=replace(stderr_path, ?, ?)
                WHERE job_id=?
                """,
                (
                    source_warehouse,
                    target_warehouse,
                    source_warehouse,
                    target_warehouse,
                    CODEX_BACKEND_GATE_JOB_ID,
                ),
            )
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT artifact_id,job_id,type,path,checksum,checksum_algorithm,
                       attempt_number,metadata_json
                FROM artifacts WHERE job_id=?
                """,
                (target_job_id,),
            ).fetchone()
        self.assertIsNotNone(row)
        assert row is not None
        return {
            **dict(row),
            "artifact_type": row["type"],
            "artifact_checksum": row["checksum"],
            "artifact_attempt": row["attempt_number"],
        }

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

    def _tree_files(self, root: Path) -> dict[str, bytes]:
        return {
            path.relative_to(root).as_posix(): path.read_bytes()
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
