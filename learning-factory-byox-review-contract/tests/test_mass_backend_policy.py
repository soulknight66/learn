from __future__ import annotations

import hashlib
import json
import tempfile
import threading
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from learnfactory.backend_policy import (
    MASS_SEED_BACKEND_REQUIREMENT,
    MASS_SEED_EXECUTION_POLICY,
    MASS_SEED_ROUTE_REQUIREMENT,
    MassSeedBackendPolicyError,
    mass_seed_payloads_equivalent,
    with_mass_seed_backend_policy,
)
from learnfactory.byox_jobs import byox_job_id
from learnfactory.byox_remediation import (
    BYOX_REPAIR_ARTIFACT_TYPE,
    BYOX_REPAIR_POLICY_KIND,
)
from learnfactory.config import FactorySettings
from learnfactory.db import Database
from learnfactory.handlers import (
    HandlerFailure,
    JobHandlers,
    _enforce_mass_seed_backend,
)
from learnfactory.jobs import ClaimedJob, JobRepository
from learnfactory.seeding import (
    CODEX_BACKEND_GATE_OUTPUT,
    _mass_seed_payload_for_persistence,
    seed_all_csdiy_course_cohorts,
    seed_codex_backend_gate,
)
from learnfactory.util import canonical_json
from learnfactory.workspace import WorkspaceManager


ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "migrations"


class MassBackendRuntimePolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(
            prefix="learnfactory-mass-backend-policy-"
        )
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.settings = FactorySettings(
            root=ROOT,
            database=self.root / "factory.db",
            warehouse=self.root / "warehouse",
        )
        self.settings = replace(
            self.settings,
            backend=replace(
                self.settings.backend,
                provider=str(MASS_SEED_ROUTE_REQUIREMENT["provider"]),
                base_url=str(MASS_SEED_ROUTE_REQUIREMENT["base_url"]),
                requires_openai_auth=True,
                supports_websockets=False,
            ),
        )

    def _job(
        self,
        *,
        job_id: str = "job_legacy_mass_seed",
        job_type: str = "codex_task",
        worker_type: str = "student",
        payload: dict[str, object] | None = None,
        model: str | None = "gpt-5.6-sol",
        reasoning: str | None = "ultra",
    ) -> ClaimedJob:
        return ClaimedJob(
            job_id=job_id,
            type=job_type,
            worker_type=worker_type,
            payload=payload or {},
            attempt_count=1,
            workspace=None,
            model=model,
            reasoning_effort=reasoning,
            lease_token="test-lease",
        )

    def test_legacy_mass_policy_kinds_run_only_on_exact_runtime(self) -> None:
        for kind in (
            "codex_backend_gate",
            "csdiy_course_cohort",
            "csdiy_course_kickoff_revision",
            "csdiy_course_progression",
            "byox_reference_build",
            "byox_reference_review",
        ):
            with self.subTest(kind=kind):
                job = self._job(payload={"seed_policy": {"kind": kind}})
                _enforce_mass_seed_backend(job, self.settings)
                for field, unsafe_backend in (
                    ("name", replace(self.settings.backend, name="fake")),
                    (
                        "permission_profile",
                        replace(
                            self.settings.backend,
                            permission_profile="danger-full-access",
                        ),
                    ),
                ):
                    with self.subTest(field=field):
                        with self.assertRaises(HandlerFailure) as caught:
                            _enforce_mass_seed_backend(
                                job, replace(self.settings, backend=unsafe_backend)
                            )
                        self.assertEqual(
                            "blocked_backend_configuration", caught.exception.kind
                        )
                        self.assertFalse(caught.exception.retryable)

    def test_job_model_and_reasoning_must_be_durable_exact_values(self) -> None:
        payload = {"seed_policy": {"kind": "csdiy_course_cohort"}}
        for field, job in (
            ("model", self._job(payload=payload, model=None)),
            ("model", self._job(payload=payload, model="gpt-5.6-terra")),
            ("reasoning", self._job(payload=payload, reasoning=None)),
            ("reasoning", self._job(payload=payload, reasoning="high")),
        ):
            with self.subTest(field=field):
                with self.assertRaises(HandlerFailure) as caught:
                    _enforce_mass_seed_backend(job, self.settings)
                self.assertEqual(
                    "blocked_backend_configuration", caught.exception.kind
                )

    def test_effective_route_must_match_approved_arm_transport_exactly(self) -> None:
        job = self._job(
            payload={"seed_policy": {"kind": "csdiy_course_cohort"}}
        )
        _enforce_mass_seed_backend(job, self.settings)
        # The provider name is display-only and deliberately outside the fence.
        _enforce_mass_seed_backend(
            job,
            replace(
                self.settings,
                backend=replace(
                    self.settings.backend,
                    provider_name="arbitrary operator display label",
                ),
            ),
        )

        route_violations = (
            ("provider_none", {"provider": None}),
            ("provider_wrong", {"provider": "openai"}),
            ("base_url_missing", {"base_url": None}),
            (
                "base_url_wrong",
                {
                    "base_url": (
                        "https://openai-api-proxy.geo.arm.com/"
                        "api/providers/openai/v1/"
                    )
                },
            ),
            ("auth_disabled", {"requires_openai_auth": False}),
            ("websockets_enabled", {"supports_websockets": True}),
        )
        for case, changes in route_violations:
            with self.subTest(case=case):
                unsafe = replace(
                    self.settings,
                    backend=replace(self.settings.backend, **changes),
                )
                with self.assertRaises(HandlerFailure) as caught:
                    _enforce_mass_seed_backend(job, unsafe)
                self.assertEqual(
                    "blocked_backend_configuration", caught.exception.kind
                )
                self.assertFalse(caught.exception.retryable)

    def test_kind_removal_cannot_bypass_independent_markers(self) -> None:
        by_id = self._job(
            job_id="job_byox_build_v1_0123456789abcdef0123456789abcdef",
            payload={"seed_policy": {"kind": "tampered"}},
            model="gpt-5.6-terra",
        )
        by_artifact = self._job(
            job_id="job_renamed",
            payload={
                "seed_policy": {"kind": "tampered"},
                "artifact_type": "student-course-attempt",
            },
            reasoning="low",
        )
        progression_by_id = self._job(
            job_id=(
                "job_csdiy_progress_v1_0123456789abcdef01234567_"
                "contract_v2_materialize"
            ),
            payload={"seed_policy": {"kind": "tampered"}},
            reasoning="low",
        )
        for marker, job in (
            ("job_id", by_id),
            ("artifact_type", by_artifact),
            ("progression_job_id", progression_by_id),
        ):
            with self.subTest(marker=marker):
                with self.assertRaises(HandlerFailure):
                    _enforce_mass_seed_backend(job, self.settings)

    def test_conflicting_payload_declarations_fail_closed(self) -> None:
        base: dict[str, object] = {
            "seed_policy": {"kind": "byox_reference_review"}
        }
        payloads = (
            {
                **base,
                "required_backend": dict(MASS_SEED_BACKEND_REQUIREMENT),
            },
            {
                **base,
                "execution_policy": {"backend": "exec"},
            },
            {
                **base,
                "required_backend": {
                    "name": "exec",
                    "permission_profile": "danger-full-access",
                },
            },
            {
                **base,
                "execution_policy": {
                    **MASS_SEED_EXECUTION_POLICY,
                    "reasoning_effort": "high",
                },
            },
            {**base, "execution_policy": "ambient"},
        )
        for payload in payloads:
            with self.subTest(payload=payload):
                with self.assertRaises(HandlerFailure):
                    _enforce_mass_seed_backend(self._job(payload=payload), self.settings)

    def test_only_exact_historical_partial_shapes_remain_compatible(self) -> None:
        project_id = "project_copied_legacy_byox"
        legacy_byox = self._job(
            job_id=byox_job_id(project_id),
            worker_type="reference_builder",
            payload={
                "seed_policy": {
                    "kind": "byox_reference_build",
                    "version": 1,
                    "role": "builder",
                },
                "project_id": project_id,
                "artifact_type": "byox-challenge-pack",
                "execution_policy": {
                    "model": "gpt-5.6-sol",
                    "reasoning_effort": "ultra",
                },
            }
        )
        kickoff_digest = "0123456789abcdef01234567"
        legacy_kickoff_revision = self._job(
            job_id=(
                f"job_csdiy_kickoff_rev_v1_{kickoff_digest}_student_target"
            ),
            worker_type="student",
            payload={
                "seed_policy": {
                    "kind": "csdiy_course_kickoff_revision",
                    "version": 1,
                    "attempt_number": 2,
                    "role": "student_revision",
                },
                "revision_id": f"csdiy-kickoff-revision-v1-{kickoff_digest}",
                "artifact_type": "student-course-attempt",
                "required_backend": dict(MASS_SEED_BACKEND_REQUIREMENT),
            }
        )
        _enforce_mass_seed_backend(legacy_byox, self.settings)
        _enforce_mass_seed_backend(legacy_kickoff_revision, self.settings)

    def test_legacy_partial_exception_requires_all_identity_markers(self) -> None:
        project_id = "project_identity_bound_byox"
        byox_payload: dict[str, object] = {
            "seed_policy": {
                "kind": "byox_reference_build",
                "version": 1,
                "role": "builder",
            },
            "project_id": project_id,
            "artifact_type": "byox-challenge-pack",
            "execution_policy": {
                "model": "gpt-5.6-sol",
                "reasoning_effort": "ultra",
            },
        }
        byox_id = byox_job_id(project_id)
        invalid_byox_jobs = (
            self._job(
                job_id=byox_id,
                worker_type="reference_builder",
                payload={**byox_payload, "artifact_type": "course-preparation"},
            ),
            self._job(
                job_id=byox_id,
                worker_type="examiner",
                payload=byox_payload,
            ),
            self._job(
                job_id="job_csdiy_progress_v1_0123456789abcdef01234567_examiner",
                worker_type="reference_builder",
                payload=byox_payload,
            ),
            self._job(
                job_id=byox_id,
                worker_type="reference_builder",
                payload={
                    **byox_payload,
                    "seed_policy": {
                        "kind": "csdiy_course_kickoff_revision",
                        "version": 1,
                        "role": "builder",
                    },
                },
            ),
        )
        kickoff_digest = "fedcba987654321001234567"
        kickoff_payload: dict[str, object] = {
            "seed_policy": {
                "kind": "csdiy_course_kickoff_revision",
                "version": 1,
                "attempt_number": 2,
                "role": "student_revision",
            },
            "revision_id": f"csdiy-kickoff-revision-v1-{kickoff_digest}",
            "artifact_type": "student-course-attempt",
            "required_backend": dict(MASS_SEED_BACKEND_REQUIREMENT),
        }
        invalid_kickoff_jobs = (
            self._job(
                job_id=f"job_csdiy_kickoff_rev_v1_{kickoff_digest}_student_target",
                worker_type="student",
                payload={**kickoff_payload, "artifact_type": "byox-challenge-pack"},
            ),
            self._job(
                job_id=f"job_csdiy_kickoff_rev_v1_{kickoff_digest}_examiner",
                worker_type="student",
                payload=kickoff_payload,
            ),
            self._job(
                job_id=f"job_csdiy_kickoff_rev_v1_{kickoff_digest}_student_target",
                worker_type="student",
                payload={
                    **kickoff_payload,
                    "seed_policy": {
                        "kind": "byox_reference_build",
                        "version": 1,
                        "attempt_number": 2,
                        "role": "student_revision",
                    },
                },
            ),
        )
        for job in (*invalid_byox_jobs, *invalid_kickoff_jobs):
            with self.subTest(job_id=job.job_id, worker_type=job.worker_type):
                with self.assertRaises(HandlerFailure):
                    _enforce_mass_seed_backend(job, self.settings)

    def test_repair_builders_have_kind_artifact_and_id_backstops(self) -> None:
        repair_id = "job_byox_repair_v1_g1_0123456789abcdef0123456789abcdef"
        full_payload: dict[str, object] = {
            "seed_policy": {
                "kind": BYOX_REPAIR_POLICY_KIND,
                "version": 1,
                "role": "builder",
                "generation": 1,
            },
            "artifact_type": BYOX_REPAIR_ARTIFACT_TYPE,
            "required_backend": dict(MASS_SEED_BACKEND_REQUIREMENT),
            "execution_policy": dict(MASS_SEED_EXECUTION_POLICY),
        }
        copied_live = self._job(
            job_id=repair_id,
            worker_type="reference_builder",
            payload=full_payload,
        )
        _enforce_mass_seed_backend(copied_live, self.settings)
        markers = (
            self._job(
                job_id="job_repair_kind_only",
                worker_type="reference_builder",
                payload={
                    **full_payload,
                    "artifact_type": "other",
                },
                model="gpt-5.6-terra",
            ),
            self._job(
                job_id="job_repair_artifact_only",
                worker_type="reference_builder",
                payload={
                    **full_payload,
                    "seed_policy": {"kind": "other"},
                },
                model="gpt-5.6-terra",
            ),
            self._job(
                job_id=repair_id,
                worker_type="reference_builder",
                payload={
                    **full_payload,
                    "seed_policy": {"kind": "other"},
                    "artifact_type": "other",
                },
                model="gpt-5.6-terra",
            ),
        )
        for job in markers:
            with self.subTest(job_id=job.job_id):
                with self.assertRaises(HandlerFailure):
                    _enforce_mass_seed_backend(job, self.settings)

    def test_unrelated_codex_and_deterministic_fake_jobs_are_unchanged(self) -> None:
        unsafe = replace(
            self.settings,
            backend=replace(
                self.settings.backend,
                name="fake",
                permission_profile="danger-full-access",
            ),
        )
        _enforce_mass_seed_backend(
            self._job(
                job_id="job_explicit_local_test",
                payload={"artifact_type": "test-output"},
                model=None,
                reasoning=None,
            ),
            unsafe,
        )
        _enforce_mass_seed_backend(
            self._job(
                job_id="job_byox_build_v1_0123456789abcdef0123456789abcdef",
                job_type="fake",
                payload={"seed_policy": {"kind": "byox_reference_build"}},
                model=None,
                reasoning=None,
            ),
            unsafe,
        )

    def test_handler_rejects_before_backend_construction_or_spawn(self) -> None:
        database = Database(self.root / "handler.db", MIGRATIONS)
        database.migrate()
        manager = WorkspaceManager(self.root / "handler-warehouse", database)
        manager.initialize()
        workspace = self.root / "attempt"
        logs = self.root / "logs"
        workspace.mkdir()
        unsafe = replace(
            self.settings,
            database=database.path,
            warehouse=self.root / "handler-warehouse",
            backend=replace(self.settings.backend, provider=None),
        )
        job = self._job(
            job_id="job_csdiy_progress_v1_0123456789abcdef01234567_examiner",
            payload={"prompt": "must not run", "validators": []},
        )
        with patch("learnfactory.handlers.ExecBackend") as backend:
            with self.assertRaises(HandlerFailure) as caught:
                JobHandlers(unsafe, database, manager).execute(
                    job, workspace, logs, threading.Event()
                )
        backend.assert_not_called()
        self.assertEqual("blocked_backend_configuration", caught.exception.kind)

    def test_new_policy_helper_is_exact_nonmutating_and_rejects_conflicts(self) -> None:
        original: dict[str, object] = {
            "seed_policy": {"kind": "csdiy_course_cohort"},
            "execution_policy": {
                "model": "gpt-5.6-sol",
                "reasoning_effort": "ultra",
            },
        }
        before = canonical_json(original)
        fenced = with_mass_seed_backend_policy(original)
        self.assertEqual(before, canonical_json(original))
        self.assertEqual(
            MASS_SEED_BACKEND_REQUIREMENT, fenced["required_backend"]
        )
        self.assertEqual(MASS_SEED_EXECUTION_POLICY, fenced["execution_policy"])
        with self.assertRaises(MassSeedBackendPolicyError):
            with_mass_seed_backend_policy(
                {"required_backend": {"name": "fake"}}
            )

    def test_only_exact_legacy_omission_is_identity_compatible(self) -> None:
        base = {"seed_policy": {"kind": "csdiy_course_progression"}}
        fenced = with_mass_seed_backend_policy(base)
        self.assertTrue(mass_seed_payloads_equivalent(base, fenced))
        conflicting = {
            **base,
            "required_backend": dict(MASS_SEED_BACKEND_REQUIREMENT),
        }
        self.assertFalse(mass_seed_payloads_equivalent(base, conflicting))
        with self.assertRaisesRegex(RuntimeError, "conflicting explicit"):
            _mass_seed_payload_for_persistence(
                base,
                {"payload": conflicting},
            )
        for malformed_execution in (
            {"backend": "fake"},
            {"backend": "exec"},
            {"model": "gpt-5.6-sol"},
        ):
            with self.subTest(malformed_execution=malformed_execution):
                with self.assertRaisesRegex(RuntimeError, "conflicting explicit"):
                    _mass_seed_payload_for_persistence(
                        base,
                        {
                            "job_id": "job_csdiy_backend_policy_fixture",
                            "type": "codex_task",
                            "worker_type": "student",
                            "payload": {
                                **base,
                                "execution_policy": malformed_execution,
                            },
                        },
                    )

        project_id = "project_live_seed_helper"
        legacy_byox = {
            "seed_policy": {
                "kind": "byox_reference_build",
                "version": 1,
                "role": "builder",
            },
            "project_id": project_id,
            "artifact_type": "byox-challenge-pack",
            "execution_policy": {
                "model": "gpt-5.6-sol",
                "reasoning_effort": "ultra",
            },
        }
        self.assertEqual(
            legacy_byox,
            _mass_seed_payload_for_persistence(
                legacy_byox,
                {
                    "job_id": byox_job_id(project_id),
                    "type": "codex_task",
                    "worker_type": "reference_builder",
                    "payload": legacy_byox,
                },
            ),
        )


class MassBackendSeedingPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(
            prefix="learnfactory-mass-backend-seeding-"
        )
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.database = Database(self.root / "factory.db", MIGRATIONS)
        self.database.migrate()
        self.jobs = JobRepository(self.database)

    def _insert_course(self) -> str:
        course_id = "course_backend_policy_fixture"
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                """
                INSERT INTO sources(
                    source_id,type,name,path,upstream_url,commit_hash,license,
                    ingested_at,metadata_json,is_active
                ) VALUES (?,?,?,?,?,?,?,?,?,1)
                """,
                (
                    "source_backend_policy_csdiy",
                    "course_catalog",
                    "CSDIY",
                    "/public/csdiy",
                    "https://example.invalid/csdiy",
                    "fixture-commit",
                    "CC-BY-SA-4.0",
                    1.0,
                    "{}",
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
                    course_id,
                    "source_backend_policy_csdiy",
                    "backend-policy",
                    "Example University",
                    "Backend Policy",
                    "systems",
                    "fixture",
                    "[]",
                    10.0,
                    5.0,
                    "{}",
                    "DISCOVERED",
                ),
            )
        return course_id

    def test_new_gate_carries_policy_but_existing_legacy_payload_is_not_rewritten(
        self,
    ) -> None:
        new_id = "job_codex_backend_gate_v91"
        seed_codex_backend_gate(self.jobs, job_id=new_id)
        new_job = self.jobs.get(new_id)
        assert new_job is not None
        self.assertEqual(
            MASS_SEED_BACKEND_REQUIREMENT,
            new_job["payload"]["required_backend"],
        )
        self.assertEqual(
            MASS_SEED_EXECUTION_POLICY,
            new_job["payload"]["execution_policy"],
        )

        legacy_id = "job_codex_backend_gate_v92"
        legacy_payload = {
            "seed_policy": {"kind": "codex_backend_gate", "version": 1},
            "prompt": "legacy",
            "validators": [{"type": "required_paths", "paths": ["x"]}],
        }
        self.jobs.create(
            "codex_task",
            "maintenance",
            legacy_payload,
            job_id=legacy_id,
            model="gpt-5.6-sol",
            reasoning_effort="ultra",
        )
        with self.database.connect() as connection:
            before = connection.execute(
                "SELECT payload_json FROM jobs WHERE job_id=?", (legacy_id,)
            ).fetchone()["payload_json"]
        seed_codex_backend_gate(self.jobs, job_id=legacy_id)
        with self.database.connect() as connection:
            after = connection.execute(
                "SELECT payload_json FROM jobs WHERE job_id=?", (legacy_id,)
            ).fetchone()["payload_json"]
        self.assertEqual(before, after)
        self.assertNotIn("required_backend", json.loads(after))

    def test_fresh_backend_gate_is_claimable_under_command_fence(self) -> None:
        gate_id = seed_codex_backend_gate(self.jobs)
        gate = self.jobs.get(gate_id)
        assert gate is not None
        validators = gate["payload"]["validators"]
        self.assertEqual(
            ["required_paths", "input_integrity"],
            [validator["type"] for validator in validators],
        )
        self.assertEqual(
            hashlib.sha256(CODEX_BACKEND_GATE_OUTPUT.encode("utf-8")).hexdigest(),
            validators[1]["inputs"][0]["checksum"],
        )
        self.jobs.promote_eligible()
        fence = frozenset({"command"})
        self.assertEqual(
            0, self.jobs.count_ready_held_by_validator_fence(fence)
        )
        claimed = self.jobs.claim_next(
            "fresh-install-scheduler",
            30,
            max_total=1,
            type_limits={},
            blocked_validator_types=fence,
        )
        self.assertIsNotNone(claimed)
        assert claimed is not None
        self.assertEqual(gate_id, claimed.job_id)

    def test_reseeding_does_not_rewrite_legacy_course_role_payloads(self) -> None:
        course_id = self._insert_course()
        gate_id = seed_codex_backend_gate(self.jobs)
        first = seed_all_csdiy_course_cohorts(self.database, self.jobs)
        graph = first["cohorts"][course_id]
        role_ids = [graph[role] for role in ("preparation", "student", "examiner")]
        for job_id in role_ids:
            record = self.jobs.get(job_id)
            assert record is not None
            self.assertEqual(
                MASS_SEED_BACKEND_REQUIREMENT,
                record["payload"]["required_backend"],
            )
            self.assertEqual(
                MASS_SEED_EXECUTION_POLICY,
                record["payload"]["execution_policy"],
            )

        with self.database.transaction(immediate=True) as connection:
            for job_id in role_ids:
                row = connection.execute(
                    "SELECT payload_json FROM jobs WHERE job_id=?", (job_id,)
                ).fetchone()
                payload = json.loads(row["payload_json"])
                payload.pop("required_backend")
                payload.pop("execution_policy")
                connection.execute(
                    "UPDATE jobs SET payload_json=? WHERE job_id=?",
                    (canonical_json(payload), job_id),
                )
        with self.database.connect() as connection:
            before = {
                job_id: connection.execute(
                    "SELECT payload_json FROM jobs WHERE job_id=?", (job_id,)
                ).fetchone()["payload_json"]
                for job_id in role_ids
            }

        repeated = seed_all_csdiy_course_cohorts(
            self.database, self.jobs, gate_job_id=gate_id
        )
        self.assertEqual(0, repeated["created_jobs"])
        with self.database.connect() as connection:
            after = {
                job_id: connection.execute(
                    "SELECT payload_json FROM jobs WHERE job_id=?", (job_id,)
                ).fetchone()["payload_json"]
                for job_id in role_ids
            }
        self.assertEqual(before, after)
        self.assertTrue(
            all("required_backend" not in json.loads(value) for value in after.values())
        )


if __name__ == "__main__":
    unittest.main()
