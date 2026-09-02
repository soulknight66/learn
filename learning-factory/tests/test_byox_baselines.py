from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
import threading
import unittest
from dataclasses import replace
from pathlib import Path

from learnfactory.byox_baselines import (
    BYOX_BASELINE_SCHEMA_VERSION,
    BYOX_SNAPSHOT_JOB_SCHEME_VERSION,
    ByoxBaseline,
    ByoxBaselineConflict,
    ByoxBaselineError,
    byox_s2_builder_job_id,
    byox_s2_reviewer_job_id,
    derive_byox_baseline,
    insert_or_verify_baseline,
    insert_or_verify_binding,
    insert_or_verify_bound_job,
    insert_or_verify_job,
    job_definition_sha256,
    load_byox_baseline,
    load_job_definition,
    load_verified_binding,
    make_job_definition,
)
from learnfactory.byox_jobs import ByoxProjectSnapshot
from learnfactory.db import Database
from learnfactory.jobs import JobRepository


ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "migrations"


def _metadata(
    *, extractor: str = "1.1", observation: int = 1, tree: str = "tree-abc"
) -> str:
    return json.dumps(
        {
            "adapter": "build_your_own_x",
            "extractor_version": extractor,
            "snapshot_reader": "git-object-database",
            "tree_hash": tree,
            "license_file": "README.md#origins--license",
            "license_sha256": "a" * 64,
            "license_source_commit": "commit-a",
            "license_evidence": "explicit CC0 waiver declaration",
            "linked_resource_license": "NOASSERTION",
            # All following values describe an observation, not source material.
            "head_ref": f"branch-{observation}",
            "working_tree_dirty": bool(observation % 2),
            "last_ingestion": {
                "at": observation,
                "projects": 359,
                "warnings": [f"observation-{observation}"],
            },
            "new_runtime_only_field": observation,
        }
    )


def _project_metadata(*, extractor: str = "1.1") -> str:
    return json.dumps(
        {
            "provenance": {
                "classification": "source-derived",
                "source_commit": "commit-a",
                "source_file": "README.md",
                "source_line": 42,
                "content_sha256": "b" * 64,
                "adapter": "build_your_own_x",
                "extractor_version": extractor,
            },
            "languages": ["Rust"],
            "linked_resource_license": "NOASSERTION",
            "scoring": {
                "classification": "inferred",
                "priority_tier": 1,
                "basis": "category heuristic",
            },
        }
    )


def _snapshot() -> ByoxProjectSnapshot:
    return ByoxProjectSnapshot(
        project_id="project_00000000000000000000000000000001",
        source_id="source_00000000000000000000000000000001",
        slug="build-a-database",
        title="Build a Database",
        category="Database",
        implementation_language="Rust",
        upstream_reference="https://example.invalid/build-a-database",
        concepts=("storage", "indexing", "persistence"),
        difficulty=8.0,
        production_relevance=9.0,
        source_format="repository",
        priority_tier=1,
        project_metadata_json=_project_metadata(),
        source_type="project_catalog",
        source_name="Build Your Own X",
        source_path="/public/build-your-own-x",
        source_upstream_url="https://github.com/codecrafters-io/build-your-own-x",
        source_commit_hash="commit-a",
        source_license="CC0-1.0",
        source_ingested_at=100.0,
        source_metadata_json=_metadata(),
    )


class ByoxBaselineIdentityTests(unittest.TestCase):
    def _from_material(self, material: dict[str, object]) -> ByoxBaseline:
        rendered = json.dumps(
            material,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        original = derive_byox_baseline(_snapshot())
        return ByoxBaseline(
            baseline_sha256=hashlib.sha256(rendered.encode("utf-8")).hexdigest(),
            schema_version=original.schema_version,
            project_id=original.project_id,
            source_id=original.source_id,
            source_commit_hash=original.source_commit_hash,
            extractor_version=original.extractor_version,
            material_json=rendered,
        )

    def test_observation_only_reingest_has_the_same_material_and_ids(self) -> None:
        first = derive_byox_baseline(_snapshot())
        reingested = derive_byox_baseline(
            replace(
                _snapshot(),
                source_ingested_at=999_999.0,
                source_metadata_json=_metadata(observation=2),
            )
        )

        self.assertEqual(BYOX_BASELINE_SCHEMA_VERSION, first.schema_version)
        self.assertEqual(first, reingested)
        source_material = first.material()["source"]
        self.assertNotIn("ingested_at", source_material)
        self.assertNotIn("last_ingestion", source_material["material_metadata"])
        self.assertNotIn("head_ref", source_material["material_metadata"])
        self.assertNotIn("working_tree_dirty", source_material["material_metadata"])
        self.assertNotIn("new_runtime_only_field", source_material["material_metadata"])
        self.assertEqual(
            byox_s2_builder_job_id(first.baseline_sha256),
            byox_s2_builder_job_id(reingested.baseline_sha256),
        )

    def test_repository_relocation_does_not_change_material_identity(self) -> None:
        original = derive_byox_baseline(_snapshot())
        relocated = derive_byox_baseline(
            replace(
                _snapshot(),
                source_name="A local checkout label",
                source_path="/another/authorized/checkout",
                source_upstream_url="https://mirror.example.invalid/byox.git",
            )
        )

        self.assertEqual(original, relocated)
        self.assertEqual("content-v2", original.material()["identity_profile"])
        source_material = original.material()["source"]
        self.assertNotIn("name", source_material)
        self.assertNotIn("path", source_material)
        self.assertNotIn("upstream_url", source_material)

    def test_identity_profile_and_source_shape_fail_closed(self) -> None:
        material = derive_byox_baseline(_snapshot()).material()
        unknown = json.loads(json.dumps(material))
        unknown["identity_profile"] = "future-unknown"
        with self.assertRaisesRegex(ByoxBaselineError, "unknown"):
            self._from_material(unknown)

        locator_in_content = json.loads(json.dumps(material))
        locator_in_content["source"]["path"] = "/observational/path"
        with self.assertRaisesRegex(ByoxBaselineError, "content-v2"):
            self._from_material(locator_in_content)

        legacy_missing_locator = json.loads(json.dumps(material))
        legacy_missing_locator.pop("identity_profile")
        with self.assertRaisesRegex(ByoxBaselineError, "legacy"):
            self._from_material(legacy_missing_locator)

    def test_material_and_semantic_extractor_changes_get_new_baselines(self) -> None:
        original = derive_byox_baseline(_snapshot())
        renamed = derive_byox_baseline(replace(_snapshot(), title="Build a KV Store"))
        new_tree = derive_byox_baseline(
            replace(_snapshot(), source_metadata_json=_metadata(tree="tree-def"))
        )
        new_extractor = derive_byox_baseline(
            replace(
                _snapshot(),
                source_metadata_json=_metadata(extractor="1.2"),
                project_metadata_json=_project_metadata(extractor="1.2"),
            )
        )

        self.assertEqual(4, len({
            original.baseline_sha256,
            renamed.baseline_sha256,
            new_tree.baseline_sha256,
            new_extractor.baseline_sha256,
        }))
        self.assertNotEqual(
            byox_s2_builder_job_id(original.baseline_sha256),
            byox_s2_builder_job_id(new_extractor.baseline_sha256),
        )

    def test_inconsistent_provenance_is_rejected(self) -> None:
        bad_project_metadata = json.loads(_project_metadata())
        bad_project_metadata["provenance"]["source_commit"] = "another-commit"
        with self.assertRaisesRegex(ByoxBaselineError, "another source commit"):
            derive_byox_baseline(
                replace(
                    _snapshot(),
                    project_metadata_json=json.dumps(bad_project_metadata),
                )
            )

        with self.assertRaisesRegex(ByoxBaselineError, "BYOX adapter"):
            derive_byox_baseline(
                replace(
                    _snapshot(),
                    source_metadata_json=json.dumps(
                        {
                            "adapter": "another_catalog",
                            "extractor_version": "1",
                            "tree_hash": "tree",
                        }
                    ),
                )
            )

    def test_s2_ids_have_independent_recomputable_domains(self) -> None:
        baseline = derive_byox_baseline(_snapshot())
        builder = byox_s2_builder_job_id(baseline.baseline_sha256)
        expected_builder = hashlib.sha256(
            f"byox-builder-s2\0{baseline.baseline_sha256}".encode("ascii")
        ).hexdigest()[:32]
        self.assertEqual(f"job_byox_build_s2_{expected_builder}", builder)

        reviewer = byox_s2_reviewer_job_id(
            baseline.baseline_sha256,
            builder,
            review_contract_version=4,
        )
        expected_reviewer = hashlib.sha256(
            "\0".join(
                ("byox-review-s2", baseline.baseline_sha256, builder, "4")
            ).encode("ascii")
        ).hexdigest()[:32]
        self.assertEqual(f"job_byox_review_s2_p4_{expected_reviewer}", reviewer)
        self.assertEqual(2, BYOX_SNAPSHOT_JOB_SCHEME_VERSION)

        with self.assertRaises(ByoxBaselineError):
            byox_s2_builder_job_id("not-a-digest")
        with self.assertRaises(ByoxBaselineError):
            byox_s2_reviewer_job_id(
                baseline.baseline_sha256,
                builder,
                review_contract_version=0,
            )


class ByoxBaselineStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="learnfactory-byox-baseline-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.database = Database(self.root / "factory.db", MIGRATIONS)
        self.database.migrate()
        self.jobs = JobRepository(self.database)
        self.snapshot = _snapshot()
        self.baseline = derive_byox_baseline(self.snapshot)
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                """
                INSERT INTO sources(
                    source_id,type,name,path,upstream_url,commit_hash,license,
                    ingested_at,metadata_json,is_active
                ) VALUES (?,?,?,?,?,?,?,?,?,1)
                """,
                (
                    self.snapshot.source_id,
                    self.snapshot.source_type,
                    self.snapshot.source_name,
                    self.snapshot.source_path,
                    self.snapshot.source_upstream_url,
                    self.snapshot.source_commit_hash,
                    self.snapshot.source_license,
                    self.snapshot.source_ingested_at,
                    self.snapshot.source_metadata_json,
                ),
            )
        self.gate_job_id = self.jobs.create(
            "capability_gate",
            "validator",
            {"kind": "test-gate"},
            job_id="job_test_byox_baseline_gate",
            max_attempts=1,
        )

    def _definition(
        self,
        job_id: str,
        *,
        baseline=None,
        dependencies: tuple[str, ...] | None = None,
        payload_suffix: str = "",
        worker_type: str = "reference_builder",
        builder_job_id: str | None = None,
        policy_version: int = 4,
    ):
        selected_baseline = baseline or self.baseline
        payload = {
            "baseline_sha256": selected_baseline.baseline_sha256,
            "baseline_schema_version": selected_baseline.schema_version,
            "project_id": selected_baseline.project_id,
            "prompt": f"build independently{payload_suffix}",
            "seed_policy": {
                "kind": (
                    "byox_reference_review_s2"
                    if worker_type == "examiner"
                    else "byox_reference_build_s2"
                ),
                "version": (
                    policy_version
                    if worker_type == "examiner"
                    else BYOX_SNAPSHOT_JOB_SCHEME_VERSION
                ),
                "baseline_sha256": selected_baseline.baseline_sha256,
                "baseline_schema_version": selected_baseline.schema_version,
            },
        }
        if builder_job_id is not None:
            payload["builder_job_id"] = builder_job_id
        return make_job_definition(
            job_id=job_id,
            job_type="codex_task",
            worker_type=worker_type,
            payload=payload,
            priority=90.0,
            score_components={"future_learning_value": 10.0},
            dependencies=dependencies or (self.gate_job_id,),
            max_attempts=2,
            model="gpt-5.6-sol",
            reasoning_effort="ultra",
        )

    def _record_baseline(self) -> None:
        with self.database.transaction(immediate=True) as connection:
            insert_or_verify_baseline(
                self.database,
                connection,
                self.baseline,
                first_observed_at=10.0,
            )

    def test_baseline_insert_is_idempotent_and_append_only(self) -> None:
        with self.assertRaisesRegex(ByoxBaselineError, "caller-owned transaction"):
            with self.database.connect() as connection:
                insert_or_verify_baseline(self.database, connection, self.baseline)

        with self.database.transaction(immediate=True) as connection:
            self.assertTrue(
                insert_or_verify_baseline(
                    self.database,
                    connection,
                    self.baseline,
                    first_observed_at=10.0,
                )
            )
        with self.database.transaction(immediate=True) as connection:
            self.assertFalse(
                insert_or_verify_baseline(
                    self.database,
                    connection,
                    self.baseline,
                    first_observed_at=20.0,
                )
            )
            self.assertEqual(
                self.baseline,
                load_byox_baseline(connection, self.baseline.baseline_sha256),
            )
            observed = connection.execute(
                """
                SELECT first_observed_at FROM byox_baseline_snapshots
                WHERE baseline_sha256=?
                """,
                (self.baseline.baseline_sha256,),
            ).fetchone()["first_observed_at"]
            self.assertEqual(10.0, observed)

        with self.database.connect() as connection:
            with self.assertRaisesRegex(sqlite3.IntegrityError, "immutable"):
                connection.execute(
                    """
                    UPDATE byox_baseline_snapshots SET first_observed_at=20
                    WHERE baseline_sha256=?
                    """,
                    (self.baseline.baseline_sha256,),
                )
            with self.assertRaisesRegex(sqlite3.IntegrityError, "immutable"):
                connection.execute(
                    """
                    DELETE FROM byox_baseline_snapshots WHERE baseline_sha256=?
                    """,
                    (self.baseline.baseline_sha256,),
                )
            events = connection.execute(
                """
                SELECT COUNT(*) AS n FROM events
                WHERE type='BYOX_BASELINE_SNAPSHOT_RECORDED'
                """
            ).fetchone()["n"]
        self.assertEqual(1, events)

    def test_fresh_in_window_job_and_binding_publication_is_idempotent(self) -> None:
        definition = self._definition(
            byox_s2_builder_job_id(self.baseline.baseline_sha256)
        )
        with self.database.transaction(immediate=True) as connection:
            self.assertTrue(
                insert_or_verify_baseline(
                    self.database,
                    connection,
                    self.baseline,
                    first_observed_at=10.0,
                )
            )
            first = insert_or_verify_bound_job(
                self.database,
                connection,
                self.baseline,
                definition,
                role="builder",
                policy_version=BYOX_SNAPSHOT_JOB_SCHEME_VERSION,
                created_at=30.0,
                bound_at=31.0,
            )
        self.assertTrue(first.job_created)
        self.assertTrue(first.binding_created)

        with self.database.transaction(immediate=True) as connection:
            second = insert_or_verify_bound_job(
                self.database,
                connection,
                self.baseline,
                definition,
                role="builder",
                policy_version=BYOX_SNAPSHOT_JOB_SCHEME_VERSION,
            )
            self.assertFalse(second.job_created)
            self.assertFalse(second.binding_created)
            self.assertEqual(definition, load_job_definition(connection, definition.job_id))
            binding = load_verified_binding(connection, definition.job_id)
            self.assertIsNotNone(binding)
            assert binding is not None
            self.assertEqual(job_definition_sha256(definition), binding.definition_sha256)
            self.assertEqual("gpt-5.6-sol", definition.model)
            self.assertEqual("ultra", definition.reasoning_effort)
            times = connection.execute(
                """
                SELECT baseline.first_observed_at,job.created_at,binding.bound_at
                FROM byox_baseline_snapshots baseline
                JOIN byox_baseline_job_bindings binding
                  ON binding.baseline_sha256=baseline.baseline_sha256
                JOIN jobs job ON job.job_id=binding.job_id
                WHERE binding.job_id=?
                """,
                (definition.job_id,),
            ).fetchone()
            self.assertLessEqual(times["first_observed_at"], times["created_at"])
            self.assertLessEqual(times["created_at"], times["bound_at"])

        changed = self._definition(definition.job_id, payload_suffix=" changed")
        with self.database.transaction(immediate=True) as connection:
            with self.assertRaisesRegex(ByoxBaselineConflict, "conflicting"):
                insert_or_verify_job(self.database, connection, changed)

    def test_bound_publication_rolls_back_new_job_when_binding_fails(self) -> None:
        target_id = byox_s2_builder_job_id(self.baseline.baseline_sha256)
        target = self._definition(target_id)
        blocker = self._definition("job_conflicting_baseline_binding_holder")
        with self.database.transaction(immediate=True) as connection:
            insert_or_verify_baseline(
                self.database,
                connection,
                self.baseline,
                first_observed_at=10.0,
            )
            insert_or_verify_job(
                self.database,
                connection,
                blocker,
                created_at=20.0,
            )
            connection.execute(
                """
                INSERT INTO byox_baseline_job_bindings(
                    job_id,baseline_sha256,role,policy_version,builder_job_id,
                    definition_sha256,bound_at
                ) VALUES (?,?,'builder',?,NULL,?,?)
                """,
                (
                    blocker.job_id,
                    self.baseline.baseline_sha256,
                    BYOX_SNAPSHOT_JOB_SCHEME_VERSION,
                    job_definition_sha256(blocker),
                    21.0,
                ),
            )
            with self.assertRaisesRegex(
                ByoxBaselineConflict, "binding identity conflicts"
            ):
                insert_or_verify_bound_job(
                    self.database,
                    connection,
                    self.baseline,
                    target,
                    role="builder",
                    policy_version=BYOX_SNAPSHOT_JOB_SCHEME_VERSION,
                    created_at=30.0,
                    bound_at=31.0,
                )

        with self.database.connect() as connection:
            self.assertIsNone(load_job_definition(connection, target_id))
            self.assertEqual(
                0,
                connection.execute(
                    "SELECT COUNT(*) FROM job_dependencies WHERE job_id=?",
                    (target_id,),
                ).fetchone()[0],
            )
            self.assertEqual(
                0,
                connection.execute(
                    "SELECT COUNT(*) FROM events WHERE job_id=?",
                    (target_id,),
                ).fetchone()[0],
            )
            self.assertIsNotNone(load_job_definition(connection, blocker.job_id))

    def test_bound_definition_and_dependencies_are_database_immutable(self) -> None:
        definition = self._definition(
            byox_s2_builder_job_id(self.baseline.baseline_sha256)
        )
        with self.database.transaction(immediate=True) as connection:
            insert_or_verify_baseline(self.database, connection, self.baseline)
            insert_or_verify_bound_job(
                self.database,
                connection,
                self.baseline,
                definition,
                role="builder",
                policy_version=2,
            )

        statements = (
            (
                "UPDATE jobs SET payload_json='{}' WHERE job_id=?",
                (definition.job_id,),
            ),
            (
                "UPDATE jobs SET priority=1 WHERE job_id=?",
                (definition.job_id,),
            ),
            (
                "DELETE FROM job_dependencies WHERE job_id=?",
                (definition.job_id,),
            ),
            (
                "UPDATE byox_baseline_job_bindings SET policy_version=3 WHERE job_id=?",
                (definition.job_id,),
            ),
            (
                "DELETE FROM byox_baseline_job_bindings WHERE job_id=?",
                (definition.job_id,),
            ),
        )
        for statement, parameters in statements:
            with self.database.connect() as connection:
                with self.assertRaisesRegex(sqlite3.IntegrityError, "immutable"):
                    connection.execute(statement, parameters)

        # Runtime state is deliberately not part of the immutable definition.
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                """
                UPDATE jobs SET state='BLOCKED',failure_kind='operator_hold'
                WHERE job_id=?
                """,
                (definition.job_id,),
            )
            self.assertEqual(definition, load_job_definition(connection, definition.job_id))
            self.assertIsNotNone(load_verified_binding(connection, definition.job_id))

    def test_reviewer_requires_exact_same_baseline_bound_builder_dependency(self) -> None:
        builder_id = byox_s2_builder_job_id(self.baseline.baseline_sha256)
        builder = self._definition(builder_id)
        reviewer_id = byox_s2_reviewer_job_id(
            self.baseline.baseline_sha256,
            builder_id,
            review_contract_version=4,
        )
        reviewer = self._definition(
            reviewer_id,
            dependencies=(self.gate_job_id, builder_id),
            worker_type="examiner",
            builder_job_id=builder_id,
        )
        with self.database.transaction(immediate=True) as connection:
            insert_or_verify_baseline(self.database, connection, self.baseline)
            insert_or_verify_bound_job(
                self.database,
                connection,
                self.baseline,
                builder,
                role="builder",
                policy_version=2,
            )
            result = insert_or_verify_bound_job(
                self.database,
                connection,
                self.baseline,
                reviewer,
                role="reviewer",
                policy_version=4,
                builder_job_id=builder_id,
            )
            self.assertTrue(result.job_created)
            self.assertTrue(result.binding_created)
            binding = load_verified_binding(connection, reviewer_id)
            self.assertIsNotNone(binding)
            assert binding is not None
            self.assertEqual(builder_id, binding.builder_job_id)

        missing_dependency_id = byox_s2_reviewer_job_id(
            self.baseline.baseline_sha256,
            builder_id,
            review_contract_version=5,
        )
        missing_dependency = self._definition(
            missing_dependency_id,
            worker_type="examiner",
            builder_job_id=builder_id,
            policy_version=5,
        )
        with self.database.transaction(immediate=True) as connection:
            insert_or_verify_job(self.database, connection, missing_dependency)
            with self.assertRaisesRegex(ByoxBaselineConflict, "same-baseline"):
                insert_or_verify_binding(
                    self.database,
                    connection,
                    self.baseline,
                    missing_dependency,
                    role="reviewer",
                    policy_version=5,
                    builder_job_id=builder_id,
                )

    def test_canonical_binding_tuple_cannot_fork(self) -> None:
        first_id = byox_s2_builder_job_id(self.baseline.baseline_sha256)
        first = self._definition(first_id)
        second = self._definition("job_another_exact_builder")
        with self.database.transaction(immediate=True) as connection:
            insert_or_verify_baseline(self.database, connection, self.baseline)
            insert_or_verify_bound_job(
                self.database,
                connection,
                self.baseline,
                first,
                role="builder",
                policy_version=2,
            )
            insert_or_verify_job(self.database, connection, second)
            with self.assertRaisesRegex(ByoxBaselineConflict, "S2 builder"):
                insert_or_verify_binding(
                    self.database,
                    connection,
                    self.baseline,
                    second,
                    role="builder",
                    policy_version=2,
                )

    def test_unbound_preexisting_or_attempted_job_cannot_be_blessed(self) -> None:
        preexisting_id = byox_s2_builder_job_id(self.baseline.baseline_sha256)
        preexisting = self._definition(preexisting_id)
        # This exact-looking deterministic row predates controller observation of
        # the authoritative baseline, so its payload cannot retrospectively bless it.
        with self.database.transaction(immediate=True) as connection:
            insert_or_verify_job(
                self.database,
                connection,
                preexisting,
                created_at=10.0,
            )
            insert_or_verify_baseline(
                self.database,
                connection,
                self.baseline,
                first_observed_at=20.0,
            )
            with self.assertRaisesRegex(ByoxBaselineConflict, "outside"):
                insert_or_verify_binding(
                    self.database,
                    connection,
                    self.baseline,
                    preexisting,
                    role="builder",
                    policy_version=2,
                    bound_at=30.0,
                )

        attempted_baseline = derive_byox_baseline(
            replace(self.snapshot, title="Build an Attempted Database")
        )
        attempted_id = byox_s2_builder_job_id(attempted_baseline.baseline_sha256)
        attempted = self._definition(
            attempted_id,
            baseline=attempted_baseline,
        )
        with self.database.transaction(immediate=True) as connection:
            insert_or_verify_baseline(
                self.database,
                connection,
                attempted_baseline,
                first_observed_at=20.0,
            )
            insert_or_verify_job(
                self.database,
                connection,
                attempted,
                created_at=21.0,
            )
            connection.execute(
                "UPDATE jobs SET attempt_count=1,workspace='/stale' WHERE job_id=?",
                (attempted_id,),
            )
            with self.assertRaisesRegex(ByoxBaselineConflict, "pristine"):
                insert_or_verify_binding(
                    self.database,
                    connection,
                    attempted_baseline,
                    attempted,
                    role="builder",
                    policy_version=2,
                    bound_at=30.0,
                )
        with self.database.connect() as connection:
            self.assertIsNone(load_verified_binding(connection, preexisting_id))
            self.assertIsNone(load_verified_binding(connection, attempted_id))

    def test_running_terminal_and_runtime_residue_jobs_cannot_be_newly_bound(self) -> None:
        cases = ("running", "terminal", "runtime-residue")
        for index, state_case in enumerate(cases, 1):
            baseline = derive_byox_baseline(
                replace(self.snapshot, title=f"Build Database Variant {index}")
            )
            job_id = byox_s2_builder_job_id(baseline.baseline_sha256)
            definition = self._definition(job_id, baseline=baseline)
            with self.database.transaction(immediate=True) as connection:
                insert_or_verify_baseline(
                    self.database,
                    connection,
                    baseline,
                    first_observed_at=20.0,
                )
                insert_or_verify_job(
                    self.database,
                    connection,
                    definition,
                    created_at=21.0,
                )
                if state_case == "running":
                    connection.execute(
                        "UPDATE jobs SET state='READY' WHERE job_id=?", (job_id,)
                    )
                    connection.execute(
                        """
                        UPDATE jobs
                        SET state='CLAIMED',owner='worker-test',lease_token='lease-test',
                            lease_expires_at=100
                        WHERE job_id=?
                        """,
                        (job_id,),
                    )
                    connection.execute(
                        "UPDATE jobs SET state='RUNNING' WHERE job_id=?", (job_id,)
                    )
                elif state_case == "terminal":
                    connection.execute(
                        """
                        UPDATE jobs SET state='CANCELLED',cancel_requested=1,
                                        finished_at=22
                        WHERE job_id=?
                        """,
                        (job_id,),
                    )
                else:
                    connection.execute(
                        "UPDATE jobs SET workspace='/runtime/residue' WHERE job_id=?",
                        (job_id,),
                    )
                with self.assertRaisesRegex(ByoxBaselineConflict, "pristine"):
                    insert_or_verify_binding(
                        self.database,
                        connection,
                        baseline,
                        definition,
                        role="builder",
                        policy_version=2,
                        bound_at=30.0,
                    )

    def test_generic_binding_api_has_no_legacy_adoption_escape_hatch(self) -> None:
        legacy = self._definition("job_byox_build_v1_legacy_exact_definition")
        with self.database.transaction(immediate=True) as connection:
            insert_or_verify_baseline(
                self.database,
                connection,
                self.baseline,
                first_observed_at=20.0,
            )
            insert_or_verify_job(
                self.database,
                connection,
                legacy,
                created_at=21.0,
            )
            with self.assertRaisesRegex(ByoxBaselineConflict, "S2 builder"):
                insert_or_verify_binding(
                    self.database,
                    connection,
                    self.baseline,
                    legacy,
                    role="builder",
                    policy_version=1,
                    bound_at=30.0,
                )
        with self.database.connect() as connection:
            self.assertIsNone(load_verified_binding(connection, legacy.job_id))

    def test_nonfinite_durable_timestamps_fail_closed_on_read(self) -> None:
        # SQLite 3.26 accepts positive infinity for a REAL >= 0 CHECK.  The
        # deterministic reader applies the stronger finite-number invariant.
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                """
                INSERT INTO byox_baseline_snapshots(
                    baseline_sha256,schema_version,project_id,source_id,
                    source_commit_hash,extractor_version,material_json,
                    first_observed_at
                ) VALUES (?,?,?,?,?,?,?,?)
                """,
                (
                    self.baseline.baseline_sha256,
                    self.baseline.schema_version,
                    self.baseline.project_id,
                    self.baseline.source_id,
                    self.baseline.source_commit_hash,
                    self.baseline.extractor_version,
                    self.baseline.material_json,
                    float("inf"),
                ),
            )
        with self.database.connect() as connection:
            with self.assertRaisesRegex(ByoxBaselineError, "finite"):
                load_byox_baseline(connection, self.baseline.baseline_sha256)

    def test_two_seeders_converge_on_one_exact_graph(self) -> None:
        definition = self._definition(
            byox_s2_builder_job_id(self.baseline.baseline_sha256)
        )
        barrier = threading.Barrier(2)
        outcomes: list[tuple[bool, bool, bool]] = []
        failures: list[BaseException] = []

        def publish() -> None:
            try:
                barrier.wait(timeout=5)
                with self.database.transaction(immediate=True) as connection:
                    baseline_created = insert_or_verify_baseline(
                        self.database, connection, self.baseline
                    )
                    result = insert_or_verify_bound_job(
                        self.database,
                        connection,
                        self.baseline,
                        definition,
                        role="builder",
                        policy_version=2,
                    )
                    outcomes.append(
                        (
                            baseline_created,
                            result.job_created,
                            result.binding_created,
                        )
                    )
            except BaseException as error:  # pragma: no cover - reported below
                failures.append(error)

        threads = [threading.Thread(target=publish) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=20)

        self.assertFalse(failures)
        self.assertEqual(2, len(outcomes))
        self.assertEqual(1, sum(all(outcome) for outcome in outcomes))
        self.assertEqual(1, sum(not any(outcome) for outcome in outcomes))
        with self.database.connect() as connection:
            self.assertEqual(
                1,
                connection.execute(
                    "SELECT COUNT(*) AS n FROM byox_baseline_snapshots"
                ).fetchone()["n"],
            )
            self.assertEqual(
                1,
                connection.execute(
                    "SELECT COUNT(*) AS n FROM byox_baseline_job_bindings"
                ).fetchone()["n"],
            )
            self.assertEqual(
                1,
                connection.execute(
                    "SELECT COUNT(*) AS n FROM jobs WHERE job_id=?",
                    (definition.job_id,),
                ).fetchone()["n"],
            )


if __name__ == "__main__":
    unittest.main()
