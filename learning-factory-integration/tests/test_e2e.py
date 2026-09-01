from __future__ import annotations

import asyncio
import contextlib
import hashlib
import json
import shutil
import signal
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from learnfactory import worker as worker_module
from learnfactory.backend_policy import (
    MASS_SEED_BACKEND_REQUIREMENT,
    MASS_SEED_EXECUTION_POLICY,
    MASS_SEED_ROUTE_REQUIREMENT,
)
from learnfactory.config import load_settings
from learnfactory.course_submission import (
    SUBMISSION_BINDING_VALIDATOR,
    SUBMISSION_INPUT_INTEGRITY_VALIDATOR,
    student_submission_binding_payload,
)
from learnfactory.db import Database
from learnfactory.handlers import (
    HandlerFailure,
    HandlerResult,
    JobHandlers,
    _archive_paths_exclude_staged_inputs,
    _cutover_byox_validation_workspace,
    _materialize_csdiy_examiner_result,
)
from learnfactory.jobs import JobRepository, UnsatisfiedDependencyError
from learnfactory.publication import PublicationScope
from learnfactory.scheduler import Scheduler, run_scheduler
from learnfactory.seeding import CODEX_BACKEND_GATE_OUTPUT, seed_codex_backend_gate
from learnfactory.util import now, tree_sha256
from learnfactory.validation import ValidationResult, Validator
from learnfactory.worker import run_worker
from learnfactory.workspace import WorkspaceError, WorkspaceManager


ROOT = Path(__file__).resolve().parents[1]

COURSE_EVALUATION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "result": {"type": "string", "enum": ["PASS", "REVISE", "FAIL"]},
        "score": {"type": "number", "minimum": 0, "maximum": 100},
        "evidence": {"type": "array", "items": {"type": "string"}},
        "transfer_gaps": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["result", "score", "evidence", "transfer_gaps"],
}


def _examiner_final_message(result: str = "PASS") -> str:
    return json.dumps(
        {
            "evaluation": {
                "result": result,
                "score": 90 if result == "PASS" else 50,
                "evidence": ["observable source tree reviewed"],
                "transfer_gaps": [],
            },
            "feedback": "observable review",
        }
    )


class EndToEndWorkerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(dir=ROOT / "warehouse")
        self.root = Path(self.temporary.name)
        self.config_path = self.root / "factory.toml"
        database = self.root / "factory.db"
        warehouse = self.root / "warehouse"
        self.config_path.write_text(
            "\n".join(
                [
                    "[factory]",
                    f'database = "{database}"',
                    f'warehouse = "{warehouse}"',
                    # Shared filesystem provenance capture can exceed one second
                    # under concurrent agents. Expiry-specific tests below use
                    # explicit short leases or force the timestamp directly.
                    "lease_seconds = 5",
                    "heartbeat_seconds = 0.05",
                    "poll_seconds = 0.02",
                    "max_concurrency = 2",
                    "shutdown_grace_seconds = 1",
                    "[backend]",
                    'name = "exec"',
                    'command = "codex"',
                    'sandbox = "workspace-write"',
                    f'provider = "{MASS_SEED_ROUTE_REQUIREMENT["provider"]}"',
                    f'base_url = "{MASS_SEED_ROUTE_REQUIREMENT["base_url"]}"',
                    "requires_openai_auth = true",
                    "supports_websockets = false",
                    "timeout_seconds = 5",
                    "[limits]",
                    "test = 2",
                    "[retry]",
                    "base_seconds = 0.01",
                    "max_seconds = 0.02",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        self.settings = load_settings(self.config_path)
        self.db = Database(self.settings.database, self.settings.migrations)
        self.db.migrate()
        WorkspaceManager(self.settings.warehouse, self.db).initialize()
        self.jobs = JobRepository(self.db, retry_base=0.01, retry_max=0.02)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _claimed_boundary_job(self, suffix: str) -> tuple[str, str, str]:
        job_id = self.jobs.create(
            "fake",
            "test",
            {
                "files": {"candidate/result.txt": "validated\n"},
                "validators": [
                    {
                        "type": "required_paths",
                        "name": "boundary-output",
                        "paths": ["candidate/result.txt"],
                    }
                ],
                "artifact_path": f"e2e/local-cancel-{suffix}",
            },
            job_id=f"job_local_cancel_{suffix}",
            max_attempts=1,
        )
        self.jobs.promote_eligible()
        owner = f"local-cancel-{suffix}-owner"
        claim = self.jobs.claim_next(
            owner,
            30,
            max_total=1,
            type_limits={"test": 1},
        )
        self.assertIsNotNone(claim)
        assert claim is not None
        self.assertEqual(job_id, claim.job_id)
        return job_id, owner, claim.lease_token

    def _assert_local_boundary_stop(self, job_id: str, exit_code: int) -> None:
        self.assertEqual(6, exit_code)
        record = self.jobs.get(job_id)
        assert record is not None
        self.assertEqual("FAILED", record["state"])
        self.assertEqual("worker_interrupted", record["failure_kind"])
        with self.db.connect() as connection:
            self.assertEqual(
                0,
                connection.execute(
                    "SELECT COUNT(*) FROM artifacts WHERE job_id=?", (job_id,)
                ).fetchone()[0],
            )
            run = connection.execute(
                "SELECT exit_code FROM job_runs WHERE job_id=?", (job_id,)
            ).fetchone()
        self.assertIsNotNone(run)
        assert run is not None
        self.assertEqual(6, run["exit_code"])

    def test_fake_job_traverses_claim_worker_validation_and_archive(self) -> None:
        job_id = self.jobs.create(
            "fake",
            "test",
            {
                "files": {"candidate/result.txt": "validated\n"},
                "validators": [
                    {"type": "required_paths", "name": "authoritative-output", "paths": ["candidate/result.txt"]}
                ],
                "artifact_path": "e2e/success",
            },
            max_attempts=1,
        )
        self.jobs.promote_eligible()
        dispatched = asyncio.run(run_scheduler(self.settings, self.db, until_idle=True, max_jobs=1))
        self.assertEqual(dispatched, 1)
        self.assertEqual(self.jobs.get(job_id)["state"], "SUCCEEDED")
        with self.db.connect() as connection:
            artifact = connection.execute("SELECT * FROM artifacts WHERE job_id=?", (job_id,)).fetchone()
            validation = connection.execute("SELECT * FROM validations WHERE job_id=?", (job_id,)).fetchone()
            run = connection.execute("SELECT * FROM job_runs WHERE job_id=?", (job_id,)).fetchone()
        self.assertIsNotNone(artifact)
        self.assertEqual(validation["status"], "PASS")
        self.assertEqual(run["exit_code"], 0)
        self.assertRegex(run["reproducibility_digest"], r"^[0-9a-f]{64}$")
        reproducibility = json.loads(run["reproducibility_json"])
        self.assertEqual(
            run["reproducibility_digest"],
            reproducibility["fingerprint_sha256"],
        )
        self.assertEqual("learnfactory-run-provenance-v3", reproducibility["schema"])
        provenance_path = Path(run["reproducibility_path"])
        self.assertTrue(provenance_path.is_file())
        self.assertEqual(
            reproducibility,
            json.loads(provenance_path.read_text(encoding="utf-8")),
        )
        expected_log_dir = (
            self.settings.warehouse / "logs" / job_id / "attempt-001"
        )
        self.assertEqual(expected_log_dir / "worker.stdout.log", Path(run["stdout_path"]))
        self.assertEqual(expected_log_dir / "worker.stderr.log", Path(run["stderr_path"]))
        self.assertTrue(Path(run["stdout_path"]).is_file())
        self.assertTrue(Path(run["stderr_path"]).is_file())
        self.assertFalse(
            (self.settings.warehouse / "logs" / job_id / "supervisor.stdout.log").exists()
        )
        archived = Path(artifact["path"])
        self.assertEqual((archived / "candidate/result.txt").read_text(), "validated\n")
        artifact_metadata = json.loads(artifact["metadata_json"])
        self.assertEqual(
            run["reproducibility_digest"],
            artifact_metadata["run_reproducibility"]["digest"],
        )
        with self.db.connect() as connection:
            event = connection.execute(
                """
                SELECT payload_json FROM events
                WHERE job_id=? AND type='RUN_REPRODUCIBILITY_CAPTURED'
                """,
                (job_id,),
            ).fetchone()
        self.assertIsNotNone(event)
        self.assertEqual(
            run["reproducibility_digest"], json.loads(event["payload_json"])["digest"]
        )

    def test_publication_dependency_failure_blocks_without_artifact(self) -> None:
        job_id = self.jobs.create(
            "fake",
            "test",
            {
                "files": {"candidate/result.txt": "validated\n"},
                "validators": [
                    {
                        "type": "required_paths",
                        "name": "authoritative-output",
                        "paths": ["candidate/result.txt"],
                    }
                ],
                "artifact_path": "e2e/dependency-publication-failure",
            },
            max_attempts=1,
        )
        self.jobs.promote_eligible()
        claim = self.jobs.claim_next(
            "dependency-publication-owner",
            30,
            max_total=1,
            type_limits={"test": 1},
        )
        assert claim is not None

        with patch.object(
            JobRepository,
            "succeed_with_artifact",
            side_effect=UnsatisfiedDependencyError(
                "cannot succeed with unsatisfied dependencies"
            ),
        ):
            exit_code = run_worker(
                job_id,
                "dependency-publication-owner",
                claim.lease_token,
                self.config_path,
            )

        self.assertEqual(8, exit_code)
        record = self.jobs.get(job_id)
        self.assertEqual("BLOCKED", record["state"])
        self.assertEqual("blocked_dependency", record["failure_kind"])
        with self.db.connect() as connection:
            self.assertEqual(
                0,
                connection.execute(
                    "SELECT COUNT(*) FROM artifacts WHERE job_id=?",
                    (job_id,),
                ).fetchone()[0],
            )
            run = connection.execute(
                "SELECT exit_code FROM job_runs WHERE job_id=?",
                (job_id,),
            ).fetchone()
        self.assertEqual(8, run["exit_code"])

    def test_scheduler_holds_command_validator_and_runs_structural_work(self) -> None:
        held = self.jobs.create(
            "fake",
            "test",
            {
                "files": {"held.txt": "must not run\n"},
                "validators": [
                    {
                        "type": "command",
                        "name": "unsafe-host-command",
                        "argv": ["/bin/true"],
                    }
                ],
                "artifact_path": "e2e/held-command",
            },
            priority=100,
        )
        structural = self.jobs.create(
            "fake",
            "test",
            {
                "files": {"result.txt": "safe\n"},
                "validators": [
                    {
                        "type": "required_paths",
                        "name": "safe-structure",
                        "paths": ["result.txt"],
                    }
                ],
                "artifact_path": "e2e/structural-while-held",
            },
            priority=1,
        )
        self.jobs.promote_eligible()

        dispatched = asyncio.run(
            run_scheduler(self.settings, self.db, until_idle=True)
        )
        self.assertEqual(1, dispatched)
        self.assertEqual("READY", self.jobs.get(held)["state"])
        self.assertEqual("SUCCEEDED", self.jobs.get(structural)["state"])

    def test_worker_blocks_handler_generated_command_before_validator_run(self) -> None:
        job_id = self.jobs.create(
            "fake",
            "test",
            {
                "files": {"safe.txt": "safe\n"},
                "validators": [
                    {
                        "type": "required_paths",
                        "name": "payload-looks-structural",
                        "paths": ["safe.txt"],
                    }
                ],
            },
            job_id="job_handler_generated_command_fence",
            max_attempts=1,
        )
        self.jobs.promote_eligible()
        claim = self.jobs.claim_next(
            "handler-command-fence-test",
            30,
            max_total=1,
            type_limits={"test": 1},
        )
        assert claim is not None
        handled = HandlerResult(
            evidence={},
            validators=[
                {
                    "type": "review_acceptance",
                    "name": "handler-hidden-command",
                    "mode": "command",
                    "argv": ["/bin/true"],
                }
            ],
            artifact_type="internal-generated-output",
            semantic_path="e2e/handler-command-fence",
        )
        with (
            patch("learnfactory.worker.JobHandlers.execute", return_value=handled),
            patch("learnfactory.worker.Validator.run") as validator_run,
        ):
            exit_code = run_worker(
                job_id,
                "handler-command-fence-test",
                claim.lease_token,
                self.config_path,
            )

        self.assertEqual(8, exit_code)
        validator_run.assert_not_called()
        job = self.jobs.get(job_id)
        assert job is not None
        self.assertEqual("BLOCKED", job["state"])
        self.assertEqual(
            "blocked_validator_execution_policy", job["failure_kind"]
        )

    def test_worker_exit_zero_cannot_override_validation_failure(self) -> None:
        job_id = self.jobs.create(
            "fake",
            "test",
            {
                "files": {"worker-claims-done.txt": "done\n"},
                "validators": [
                    {"type": "required_paths", "name": "immutable-hidden-check", "paths": ["actually-required.txt"]}
                ],
                "artifact_path": "e2e/reward-hack",
            },
            max_attempts=1,
        )
        self.jobs.promote_eligible()
        asyncio.run(run_scheduler(self.settings, self.db, until_idle=True, max_jobs=1))
        record = self.jobs.get(job_id)
        self.assertEqual(record["state"], "FAILED")
        self.assertEqual(record["failure_kind"], "validation_failure")
        with self.db.connect() as connection:
            artifacts = connection.execute("SELECT COUNT(*) FROM artifacts WHERE job_id=?", (job_id,)).fetchone()[0]
            failed = connection.execute("SELECT status FROM validations WHERE job_id=?", (job_id,)).fetchone()[0]
        self.assertEqual(artifacts, 0)
        self.assertEqual(failed, "FAIL")

    def test_codex_root_git_metadata_is_removed_before_validation(self) -> None:
        job_id = self.jobs.create(
            "codex_task",
            "test",
            {
                "prompt": "write result",
                "validators": [
                    {
                        "type": "forbidden_paths",
                        "name": "no-vcs-metadata",
                        "paths": [".git"],
                    },
                    {
                        "type": "required_paths",
                        "name": "result-exists",
                        "paths": ["result.txt"],
                    },
                ],
                "artifact_path": "e2e/codex-metadata-cleanup",
            },
            max_attempts=1,
        )
        self.jobs.promote_eligible()

        backend_result = type(
            "BackendResultDouble",
            (),
            {
                "exit_code": 0,
                "session_id": "session-test",
                "stdout_tail": "",
                "stderr_tail": "",
                "timed_out": False,
                "cancelled": False,
                "usage": {},
            },
        )()

        def fake_start(_backend: object, _prompt: str, workspace: Path, _logs: Path, **_kwargs: object) -> object:
            (workspace / ".git").mkdir()
            (workspace / ".git" / "config").write_text("worker metadata\n", encoding="utf-8")
            (workspace / ".agents").mkdir()
            (workspace / ".agents" / "state").write_text("worker metadata\n", encoding="utf-8")
            (workspace / ".codex").mkdir()
            (workspace / ".codex" / "state").write_text("worker metadata\n", encoding="utf-8")
            (workspace / "result.txt").write_text("ok\n", encoding="utf-8")
            return backend_result

        claim = self.jobs.claim_next(
            "metadata-cleanup-test", 30, max_total=1, type_limits={"test": 1}
        )
        self.assertIsNotNone(claim)
        assert claim is not None
        with patch("learnfactory.handlers.ExecBackend.start_job", new=fake_start):
            exit_code = run_worker(
                job_id,
                "metadata-cleanup-test",
                claim.lease_token,
                self.config_path,
            )
        self.assertEqual(0, exit_code)
        self.assertEqual("SUCCEEDED", self.jobs.get(job_id)["state"])
        with self.db.connect() as connection:
            artifact = connection.execute(
                "SELECT path,checksum,metadata_json FROM artifacts WHERE job_id=?",
                (job_id,),
            ).fetchone()
        self.assertIsNotNone(artifact)
        for name in (".git", ".agents", ".codex", "JOB.md", ".factory-workspace"):
            self.assertFalse((Path(artifact["path"]) / name).exists())
        self.assertEqual(
            [".git", ".agents", ".codex", ".factory-workspace"],
            json.loads(artifact["metadata_json"])["removed_root_metadata"],
        )

    def test_examiner_archive_projects_outputs_without_staged_candidate(self) -> None:
        job_id = self.jobs.create(
            "codex_task",
            "examiner",
            {
                "prompt": "review candidate",
                "validators": [
                    {
                        "type": "required_paths",
                        "name": "review-output",
                        "paths": ["EVALUATION.json", "REVIEW.md", "VALIDATION.md"],
                    }
                ],
                "artifact_type": "byox-independent-review",
                "artifact_path": "e2e/projected-review",
                "required_backend": dict(MASS_SEED_BACKEND_REQUIREMENT),
                "execution_policy": dict(MASS_SEED_EXECUTION_POLICY),
            },
            max_attempts=1,
            model="gpt-5.6-sol",
            reasoning_effort="ultra",
        )
        self.jobs.promote_eligible()
        backend_result = type(
            "BackendResultDouble",
            (),
            {
                "exit_code": 0,
                "session_id": "session-projection",
                "stdout_tail": "",
                "stderr_tail": "",
                "timed_out": False,
                "cancelled": False,
                "usage": {},
            },
        )()

        def fake_start(
            _backend: object,
            _prompt: str,
            workspace: Path,
            _logs: Path,
            **_kwargs: object,
        ) -> object:
            (workspace / "CANDIDATE" / "sealed").mkdir(parents=True)
            (workspace / "CANDIDATE" / "sealed" / "answer.txt").write_text(
                "input-only\n", encoding="utf-8"
            )
            (workspace / "EVALUATION.json").write_text(
                '{"verdict":"REVISE"}\n', encoding="utf-8"
            )
            (workspace / "REVIEW.md").write_text("review\n", encoding="utf-8")
            (workspace / "VALIDATION.md").write_text("checks\n", encoding="utf-8")
            return backend_result

        claim = self.jobs.claim_next(
            "projection-test", 30, max_total=1, type_limits={"examiner": 1}
        )
        assert claim is not None
        with patch("learnfactory.handlers.ExecBackend.start_job", new=fake_start):
            exit_code = run_worker(
                job_id, "projection-test", claim.lease_token, self.config_path
            )
        self.assertEqual(0, exit_code)
        with self.db.connect() as connection:
            artifact = connection.execute(
                "SELECT path,checksum,metadata_json FROM artifacts WHERE job_id=?",
                (job_id,),
            ).fetchone()
        self.assertIsNotNone(artifact)
        archived = Path(artifact["path"])
        self.assertEqual(
            ["EVALUATION.json", "REVIEW.md", "VALIDATION.md"],
            sorted(path.name for path in archived.iterdir()),
        )
        self.assertFalse((archived / "CANDIDATE").exists())
        projection_metadata = json.loads(artifact["metadata_json"])[
            "archive_projection"
        ]
        self.assertTrue(projection_metadata["staged_inputs_excluded"])
        self.assertEqual(1, projection_metadata["schema_version"])
        self.assertEqual(
            artifact["checksum"], projection_metadata["projected_tree_checksum"]
        )
        self.assertRegex(
            projection_metadata["source_workspace_checksum"], r"^[0-9a-f]{64}$"
        )
        self.assertFalse(
            any(
                path.name.startswith(".archive-projection-")
                for path in (self.settings.warehouse / "workspaces").rglob("*")
            )
        )

    def _student_submission_parent(
        self,
        files: dict[str, str],
        *,
        artifact_type: str = "student-course-attempt",
    ) -> str:
        parent = self.jobs.create(
            "fake",
            "student",
            {
                "files": files,
                "artifact_type": artifact_type,
                "artifact_path": f"e2e/csdiy-student-submission-{artifact_type}",
            },
            max_attempts=1,
        )
        self.jobs.promote_eligible()
        claim = self.jobs.claim_next(
            "csdiy-student-parent", 30, max_total=1, type_limits={"student": 1}
        )
        assert claim is not None
        self.assertEqual(
            0,
            run_worker(
                parent, "csdiy-student-parent", claim.lease_token, self.config_path
            ),
        )
        parent_record = self.jobs.get(parent)
        self.assertEqual("SUCCEEDED", parent_record["state"], parent_record)
        return parent

    def _submission_examiner_payload(self, parent: str) -> dict[str, object]:
        return {
            "seed_policy": {
                "kind": "csdiy_course_cohort",
                "version": 2,
                "role": "examiner",
            },
            "prompt": "Inspect the complete staged student tree and write the two outputs.",
            "inputs_from_dependencies": [
                {
                    "job_id": parent,
                    "artifact_type": "student-course-attempt",
                    "student_submission_root": True,
                    "destination": "STUDENT_SUBMISSION",
                }
            ],
            "protected_input_roots": ["STUDENT_SUBMISSION"],
            "student_submission_binding": student_submission_binding_payload(
                parent, "student-course-attempt"
            ),
            "output_schema": COURSE_EVALUATION_SCHEMA,
            "validators": [
                {
                    "type": "regular_files",
                    "name": "course-examiner-files",
                    "paths": ["evaluation.json", "feedback.md"],
                    "minimum_bytes": 1,
                }
            ],
            "artifact_type": "independent-course-evaluation",
            "artifact_path": "e2e/csdiy-submission-examiner",
            "required_backend": dict(MASS_SEED_BACKEND_REQUIREMENT),
            "execution_policy": dict(MASS_SEED_EXECUTION_POLICY),
        }

    def test_csdiy_examiner_sees_code_and_archives_only_outputs_with_binding_evidence(
        self,
    ) -> None:
        parent = self._student_submission_parent(
            {
                "src/service.py": "def answer():\n    return 42\n",
                "tests/test_service.py": (
                    "from src.service import answer\n"
                    "def test_answer(): assert answer() == 42\n"
                ),
                "notes.md": "learner notes\n",
                "__pycache__/service.pyc": "disposable\n",
            }
        )
        examiner = self.jobs.create(
            "codex_task",
            "examiner",
            self._submission_examiner_payload(parent),
            dependencies=[parent],
            max_attempts=1,
            model="gpt-5.6-sol",
            reasoning_effort="ultra",
        )
        self.jobs.promote_eligible()
        backend_result = type(
            "BackendResultDouble",
            (),
            {
                "exit_code": 0,
                "session_id": "session-csdiy-submission",
                "stdout_tail": "",
                "stderr_tail": "",
                "timed_out": False,
                "cancelled": False,
                "usage": {},
                "final_message": _examiner_final_message(),
            },
        )()
        result_capabilities: list[str] = []

        def fake_start(
            _backend: object,
            prompt: str,
            workspace: Path,
            _logs: Path,
            **kwargs: object,
        ) -> object:
            self.assertIn("def answer()", prompt)
            self.assertIn("tests/test_service.py", prompt)
            self.assertNotIn("__pycache__", prompt)
            self.assertEqual([], list(workspace.iterdir()))
            manifest = kwargs["sandbox_manifest"]
            result_capabilities.append(str(manifest.result_channel))
            self.assertNotIn(manifest.result_channel, prompt)
            self.assertNotIn(Path(manifest.result_channel).parent.name, prompt)
            self.assertEqual("deny", manifest.workspace_access)
            self.assertFalse(manifest.tools_enabled)
            self.assertEqual((), manifest.staged_inputs)
            self.assertEqual((), manifest.rules)
            return backend_result

        claim = self.jobs.claim_next(
            "csdiy-submission-e2e", 30, max_total=1, type_limits={"examiner": 1}
        )
        assert claim is not None
        capability_nonce = "c7" * 32
        with patch(
            "learnfactory.result_channel.secrets.token_hex",
            return_value=capability_nonce,
        ), patch("learnfactory.handlers.ExecBackend.start_job", new=fake_start):
            exit_code = run_worker(
                examiner, "csdiy-submission-e2e", claim.lease_token, self.config_path
            )
        self.assertEqual(0, exit_code)
        with self.db.connect() as connection:
            artifact = connection.execute(
                "SELECT path,metadata_json FROM artifacts WHERE job_id=?", (examiner,)
            ).fetchone()
            validations = {
                row["validator"]: row
                for row in connection.execute(
                    "SELECT validator,status,evidence_json FROM validations WHERE job_id=?",
                    (examiner,),
                )
            }
        self.assertIsNotNone(artifact)
        archived = Path(artifact["path"])
        self.assertEqual(
            ["evaluation.json", "feedback.md"],
            sorted(path.name for path in archived.iterdir()),
        )
        self.assertFalse((archived / "STUDENT_SUBMISSION").exists())
        self.assertEqual("PASS", validations[SUBMISSION_BINDING_VALIDATOR]["status"])
        self.assertEqual(
            "PASS", validations[SUBMISSION_INPUT_INTEGRITY_VALIDATOR]["status"]
        )
        binding = json.loads(
            validations[SUBMISSION_BINDING_VALIDATOR]["evidence_json"]
        )
        self.assertEqual(2, binding["projection"]["code_file_count"])
        self.assertEqual(1, binding["projection"]["test_file_count"])
        metadata = json.loads(artifact["metadata_json"])
        self.assertTrue(metadata["archive_projection"]["staged_inputs_excluded"])
        self.assertEqual(
            parent, metadata["staged_inputs"][0]["job_id"]
        )
        self.assertEqual(1, len(result_capabilities))
        raw_capability = result_capabilities[0]
        self.assertIn(capability_nonce, raw_capability)
        with self.db.connect() as connection:
            run_id = str(
                connection.execute(
                    "SELECT run_id FROM job_runs WHERE job_id=?", (examiner,)
                ).fetchone()[0]
            )
        self.assertNotIn(run_id, raw_capability)
        needles = (
            raw_capability.encode(),
            capability_nonce.encode(),
            hashlib.sha256(raw_capability.encode()).hexdigest().encode(),
            hashlib.sha256(capability_nonce.encode()).hexdigest().encode(),
        )
        scanned = 0
        for candidate in self.root.rglob("*"):
            if not candidate.is_file():
                continue
            scanned += 1
            content = candidate.read_bytes()
            for needle in needles:
                self.assertNotIn(
                    needle,
                    content,
                    msg=f"result capability persisted in {candidate}",
                )
        self.assertGreater(scanned, 5)

    def test_csdiy_examiner_candidate_is_not_mounted(self) -> None:
        parent = self._student_submission_parent(
            {"student_work/src/main.c": "int main(void) { return 0; }\n"}
        )
        examiner = self.jobs.create(
            "codex_task",
            "examiner",
            self._submission_examiner_payload(parent),
            dependencies=[parent],
            max_attempts=1,
            model="gpt-5.6-sol",
            reasoning_effort="ultra",
        )
        self.jobs.promote_eligible()
        backend_result = type(
            "BackendResultDouble",
            (),
            {
                "exit_code": 0,
                "session_id": "session-csdiy-tamper",
                "stdout_tail": "",
                "stderr_tail": "",
                "timed_out": False,
                "cancelled": False,
                "usage": {},
                "final_message": _examiner_final_message(),
            },
        )()

        def fake_start(
            _backend: object,
            prompt: str,
            workspace: Path,
            _logs: Path,
            **_kwargs: object,
        ) -> object:
            self.assertIn("int main(void)", prompt)
            self.assertFalse((workspace / "STUDENT_SUBMISSION").exists())
            self.assertEqual([], list(workspace.iterdir()))
            return backend_result

        claim = self.jobs.claim_next(
            "csdiy-tamper-e2e", 30, max_total=1, type_limits={"examiner": 1}
        )
        assert claim is not None
        with patch("learnfactory.handlers.ExecBackend.start_job", new=fake_start):
            exit_code = run_worker(
                examiner, "csdiy-tamper-e2e", claim.lease_token, self.config_path
            )
        self.assertEqual(0, exit_code)
        self.assertEqual("SUCCEEDED", self.jobs.get(examiner)["state"])
        with self.db.connect() as connection:
            integrity = connection.execute(
                "SELECT status,evidence_json FROM validations WHERE job_id=? AND validator=?",
                (examiner, SUBMISSION_INPUT_INTEGRITY_VALIDATOR),
            ).fetchone()
            artifact_count = connection.execute(
                "SELECT COUNT(*) AS n FROM artifacts WHERE job_id=?", (examiner,)
            ).fetchone()["n"]
        self.assertEqual("PASS", integrity["status"])
        self.assertIn("descriptor-pinned", integrity["evidence_json"])
        self.assertEqual(1, artifact_count)

    def test_csdiy_examiner_rejects_workspace_forgery_without_final_json(self) -> None:
        parent = self._student_submission_parent(
            {"student_work/src/main.py": "print('candidate')\n"}
        )
        examiner = self.jobs.create(
            "codex_task",
            "examiner",
            self._submission_examiner_payload(parent),
            dependencies=[parent],
            max_attempts=1,
            model="gpt-5.6-sol",
            reasoning_effort="ultra",
        )
        self.jobs.promote_eligible()
        result = type(
            "ForgedWorkspaceResult",
            (),
            {
                "exit_code": 0,
                "session_id": "session-forged-workspace",
                "stderr_tail": "",
                "timed_out": False,
                "cancelled": False,
                "usage": {},
                "final_message": "not one JSON object",
            },
        )()

        def fake_start(
            _backend: object,
            _prompt: str,
            workspace: Path,
            _logs: Path,
            **_kwargs: object,
        ) -> object:
            # A test double bypasses the kernel profile to reproduce the old
            # exploit. These files are never accepted as the result channel.
            (workspace / "evaluation.json").write_text(
                json.dumps(
                    {
                        "result": "PASS",
                        "score": 100,
                        "evidence": ["forged"],
                        "transfer_gaps": [],
                    }
                ),
                encoding="utf-8",
            )
            (workspace / "feedback.md").write_text("forged\n", encoding="utf-8")
            return result

        with self.db.connect() as connection:
            before_attempts = connection.execute(
                "SELECT COUNT(*) FROM attempts"
            ).fetchone()[0]
        claim = self.jobs.claim_next(
            "csdiy-final-channel-forgery", 30, max_total=1, type_limits={"examiner": 1}
        )
        assert claim is not None
        with patch("learnfactory.handlers.ExecBackend.start_job", new=fake_start):
            exit_code = run_worker(
                examiner,
                "csdiy-final-channel-forgery",
                claim.lease_token,
                self.config_path,
            )
        self.assertEqual(6, exit_code)
        record = self.jobs.get(examiner)
        self.assertEqual("FAILED", record["state"])
        self.assertEqual("validation_failure", record["failure_kind"])
        self.assertIn("final-message contract failed", record["error"])
        with self.db.connect() as connection:
            self.assertEqual(
                before_attempts,
                connection.execute("SELECT COUNT(*) FROM attempts").fetchone()[0],
            )
            self.assertEqual(
                0,
                connection.execute(
                    "SELECT COUNT(*) FROM artifacts WHERE job_id=?", (examiner,)
                ).fetchone()[0],
            )

    def test_csdiy_examiner_rejects_deeply_nested_result_without_outputs(self) -> None:
        workspace = self.root / "nested-result-workspace"
        workspace.mkdir()
        deeply_nested = "[" * 2_000 + "0" + "]" * 2_000

        with self.assertRaisesRegex(ValueError, "malformed single JSON object"):
            _materialize_csdiy_examiner_result(
                workspace, deeply_nested, COURSE_EVALUATION_SCHEMA
            )

        self.assertFalse((workspace / "evaluation.json").exists())
        self.assertFalse((workspace / "feedback.md").exists())

    def test_csdiy_rubric_and_candidate_are_prompt_only_with_empty_workspace(self) -> None:
        preparation = self.jobs.create(
            "fake",
            "course_manager",
            {
                "files": {
                    "examiner_only/RUBRIC.md": "RUBRIC-SENTINEL: demand observable evidence\n"
                },
                "artifact_type": "course-preparation",
                "artifact_path": "e2e/csdiy-prompt-only-rubric",
            },
            max_attempts=1,
        )
        self.jobs.promote_eligible()
        self.assertEqual(
            1,
            asyncio.run(
                run_scheduler(self.settings, self.db, until_idle=True, max_jobs=1)
            ),
        )
        parent = self._student_submission_parent(
            {"student_work/src/main.py": "print('candidate')\n"}
        )
        payload = self._submission_examiner_payload(parent)
        payload["inputs_from_dependencies"].insert(
            0,
            {
                "job_id": preparation,
                "subpath": "examiner_only/RUBRIC.md",
                "destination": "RUBRIC.md",
                "artifact_type": "course-preparation",
                "prompt_context": True,
            },
        )
        examiner = self.jobs.create(
            "codex_task",
            "examiner",
            payload,
            dependencies=[preparation, parent],
            max_attempts=1,
            model="gpt-5.6-sol",
            reasoning_effort="ultra",
        )
        self.jobs.promote_eligible()
        result = type(
            "PromptOnlyRubricResult",
            (),
            {
                "exit_code": 0,
                "session_id": "session-prompt-only-rubric",
                "stderr_tail": "",
                "timed_out": False,
                "cancelled": False,
                "usage": {},
                "final_message": _examiner_final_message(),
            },
        )()

        def fake_start(
            _backend: object,
            prompt: str,
            workspace: Path,
            _logs: Path,
            **kwargs: object,
        ) -> object:
            self.assertIn("RUBRIC-SENTINEL", prompt)
            self.assertFalse((workspace / "RUBRIC.md").exists())
            self.assertFalse((workspace / "JOB.md").exists())
            manifest = kwargs["sandbox_manifest"]
            self.assertEqual([], list(workspace.iterdir()))
            self.assertEqual("deny", manifest.workspace_access)
            self.assertFalse(manifest.tools_enabled)
            self.assertEqual((), manifest.declared_outputs)
            self.assertEqual((), manifest.staged_inputs)
            self.assertEqual((), manifest.rules)
            return result

        claim = self.jobs.claim_next(
            "csdiy-prompt-context", 30, max_total=1, type_limits={"examiner": 1}
        )
        assert claim is not None
        with patch("learnfactory.handlers.ExecBackend.start_job", new=fake_start):
            self.assertEqual(
                0,
                run_worker(
                    examiner,
                    "csdiy-prompt-context",
                    claim.lease_token,
                    self.config_path,
                ),
            )
        with self.db.connect() as connection:
            artifact = connection.execute(
                "SELECT metadata_json FROM artifacts WHERE job_id=?", (examiner,)
            ).fetchone()
        metadata = json.loads(artifact["metadata_json"])
        context = metadata["prompt_contexts"][0]
        self.assertEqual("RUBRIC.md", context["path"])
        self.assertFalse(context["mounted"])
        self.assertFalse(context["content_stored"])
        self.assertNotIn("content", context)
        self.assertRegex(context["checksum"], r"^[0-9a-f]{64}$")

    def test_csdiy_revision_examiners_receive_complete_code_and_test_tree(self) -> None:
        cases = (
            (
                "csdiy_course_kickoff_revision",
                2,
                "student-course-attempt",
                "independent-course-evaluation",
            ),
            (
                "csdiy_course_progression",
                1,
                "student-course-unit-attempt",
                "independent-course-unit-evaluation",
            ),
        )
        for index, (kind, version, student_type, evaluation_type) in enumerate(cases):
            with self.subTest(kind=kind):
                parent = self._student_submission_parent(
                    {
                        "student_work/src/worker.rs": "pub fn answer() -> u8 { 42 }\n",
                        "student_work/tests/worker_test.rs": (
                            "#[test] fn answer_is_42() { "
                            "assert_eq!(crate::answer(), 42); }\n"
                        ),
                        "student_work/notes.md": "revision notes\n",
                        "student_work/target/cache.bin": "disposable\n",
                    },
                    artifact_type=student_type,
                )
                payload = {
                    "seed_policy": {
                        "kind": kind,
                        "version": version,
                        "attempt_number": 2,
                        "role": "examiner_revision",
                    },
                    "prompt": "Inspect the full revised tree and write bounded outputs.",
                    "inputs_from_dependencies": [
                        {
                            "job_id": parent,
                            "artifact_type": student_type,
                            "student_submission_root": True,
                            "destination": "STUDENT_SUBMISSION",
                        }
                    ],
                    "protected_input_roots": ["STUDENT_SUBMISSION"],
                    "student_submission_binding": student_submission_binding_payload(
                        parent, student_type
                    ),
                    "output_schema": COURSE_EVALUATION_SCHEMA,
                    "validators": [
                        {
                            "type": "regular_files",
                            "name": f"revision-examiner-files-{index}",
                            "paths": ["evaluation.json", "feedback.md"],
                            "minimum_bytes": 1,
                        }
                    ],
                    "artifact_type": evaluation_type,
                    "artifact_path": f"e2e/revision-submission-{index}",
                    "required_backend": dict(MASS_SEED_BACKEND_REQUIREMENT),
                    "execution_policy": dict(MASS_SEED_EXECUTION_POLICY),
                }
                examiner = self.jobs.create(
                    "codex_task",
                    "examiner",
                    payload,
                    dependencies=[parent],
                    max_attempts=1,
                    model="gpt-5.6-sol",
                    reasoning_effort="ultra",
                )
                self.jobs.promote_eligible()
                result = type(
                    "RevisionBackendResultDouble",
                    (),
                    {
                        "exit_code": 0,
                        "session_id": f"session-revision-{index}",
                        "stdout_tail": "",
                        "stderr_tail": "",
                        "timed_out": False,
                        "cancelled": False,
                        "usage": {},
                        "final_message": _examiner_final_message(),
                    },
                )()

                def fake_start(
                    _backend: object,
                    prompt: str,
                    workspace: Path,
                    _logs: Path,
                    **_kwargs: object,
                ) -> object:
                    self.assertIn("src/worker.rs", prompt)
                    self.assertIn("tests/worker_test.rs", prompt)
                    self.assertNotIn("target/cache.bin", prompt)
                    self.assertEqual([], list(workspace.iterdir()))
                    return result

                claim = self.jobs.claim_next(
                    f"revision-submission-e2e-{index}",
                    30,
                    max_total=1,
                    type_limits={"examiner": 1},
                )
                assert claim is not None
                with patch(
                    "learnfactory.handlers.ExecBackend.start_job", new=fake_start
                ):
                    exit_code = run_worker(
                        examiner,
                        f"revision-submission-e2e-{index}",
                        claim.lease_token,
                        self.config_path,
                    )
                self.assertEqual(0, exit_code)
                with self.db.connect() as connection:
                    artifact = connection.execute(
                        "SELECT path FROM artifacts WHERE job_id=?", (examiner,)
                    ).fetchone()
                    binding = connection.execute(
                        """
                        SELECT status FROM validations
                        WHERE job_id=? AND validator=?
                        """,
                        (examiner, SUBMISSION_BINDING_VALIDATOR),
                    ).fetchone()
                self.assertEqual("PASS", binding["status"])
                archived = Path(artifact["path"])
                self.assertFalse((archived / "STUDENT_SUBMISSION").exists())
                self.assertEqual(
                    ["evaluation.json", "feedback.md"],
                    sorted(path.name for path in archived.iterdir()),
                )

    def test_csdiy_examiner_rejects_forbidden_student_tree_before_launch(self) -> None:
        parent = self._student_submission_parent(
            {
                "src/main.py": "print('ok')\n",
                "sealed/reference.py": "answer = 42\n",
            }
        )
        examiner = self.jobs.create(
            "codex_task",
            "examiner",
            self._submission_examiner_payload(parent),
            dependencies=[parent],
            max_attempts=1,
            model="gpt-5.6-sol",
            reasoning_effort="ultra",
        )
        self.jobs.promote_eligible()
        claim = self.jobs.claim_next(
            "csdiy-forbidden-e2e", 30, max_total=1, type_limits={"examiner": 1}
        )
        assert claim is not None
        with patch("learnfactory.handlers.ExecBackend.start_job") as start:
            exit_code = run_worker(
                examiner, "csdiy-forbidden-e2e", claim.lease_token, self.config_path
            )
        self.assertNotEqual(0, exit_code)
        start.assert_not_called()
        self.assertEqual("FAILED", self.jobs.get(examiner)["state"])

    def test_output_only_policy_rejects_overlap_with_staged_input(self) -> None:
        with self.assertRaises(HandlerFailure) as captured:
            _archive_paths_exclude_staged_inputs(
                ("student_work",),
                [
                    {
                        "path": "student_work/template.md",
                        "kind": "file",
                        "checksum": "0" * 64,
                    }
                ],
            )
        self.assertEqual("unsafe_archive_projection", captured.exception.kind)
        self.assertFalse(captured.exception.retryable)

    def test_unsafe_projection_is_a_validation_failure_not_worker_crash(self) -> None:
        job_id = self.jobs.create(
            "fake",
            "examiner",
            {},
            job_id="job_projection_validation_failure",
            max_attempts=1,
        )
        self.jobs.promote_eligible()
        claim = self.jobs.claim_next(
            "projection-failure-test",
            30,
            max_total=1,
            type_limits={"examiner": 1},
        )
        assert claim is not None
        handled = HandlerResult(
            evidence={},
            validators=[
                {
                    "type": "handler_evidence",
                    "name": "worker-finished",
                    "passed": True,
                }
            ],
            artifact_type="byox-independent-review",
            semantic_path="e2e/projected-review-failure",
            archive_paths=("REVIEW.md",),
        )
        with patch(
            "learnfactory.worker.JobHandlers.execute", return_value=handled
        ), patch(
            "learnfactory.worker.WorkspaceManager.create_archive_projection",
            side_effect=WorkspaceError("output is a symlink"),
        ):
            exit_code = run_worker(
                job_id,
                "projection-failure-test",
                claim.lease_token,
                self.config_path,
            )

        self.assertEqual(6, exit_code)
        job = self.jobs.get(job_id)
        assert job is not None
        self.assertEqual("FAILED", job["state"])
        self.assertEqual("validation_failure", job["failure_kind"])

    def test_authoritative_byox_snapshot_cannot_change_after_validation(self) -> None:
        job_id = self.jobs.create(
            "fake",
            "reference_builder",
            {},
            job_id="job_byox_cutover_validator_mutation",
            max_attempts=1,
        )
        self.jobs.promote_eligible()
        claim = self.jobs.claim_next(
            "byox-cutover-mutation-test",
            30,
            max_total=1,
            type_limits={"reference_builder": 1},
        )
        assert claim is not None

        def execute_with_cutover(
            _handlers: JobHandlers,
            _job: object,
            workspace: Path,
            _log_dir: Path,
            _cancel_event: object,
        ) -> HandlerResult:
            (workspace / "README.md").write_text("before\n", encoding="utf-8")
            cutover = _cutover_byox_validation_workspace(workspace)
            return HandlerResult(
                evidence={},
                validators=[
                    {
                        "type": "byox_code_presence",
                        "name": "byox-authoritative-code-bearing-tree",
                    }
                ],
                artifact_type="byox-challenge-pack",
                semantic_path="e2e/cutover-mutation",
                metadata={"byox_validation_cutover": cutover},
            )

        def validate_then_mutate(
            _validator: Validator,
            _current_job_id: str,
            workspace: Path,
            *args: object,
            **kwargs: object,
        ) -> object:
            (workspace / "README.md").write_text("after!\n", encoding="utf-8")
            return [
                ValidationResult(
                    "byox-authoritative-code-bearing-tree",
                    "PASS",
                    {"synthetic": "validator already observed detached bytes"},
                )
            ]

        with patch(
            "learnfactory.worker.JobHandlers.execute", new=execute_with_cutover
        ), patch("learnfactory.worker.Validator.run", new=validate_then_mutate):
            exit_code = run_worker(
                job_id,
                "byox-cutover-mutation-test",
                claim.lease_token,
                self.config_path,
            )

        self.assertEqual(6, exit_code)
        job = self.jobs.get(job_id)
        assert job is not None
        self.assertEqual("FAILED", job["state"])
        self.assertEqual("validation_failure", job["failure_kind"])
        with self.db.connect() as connection:
            self.assertEqual(
                0,
                connection.execute(
                    "SELECT COUNT(*) FROM artifacts WHERE job_id=?", (job_id,)
                ).fetchone()[0],
            )

    def test_real_backend_gate_snapshot_cannot_change_after_validation(self) -> None:
        job_id = seed_codex_backend_gate(self.jobs)
        self.jobs.promote_eligible()
        claim = self.jobs.claim_next(
            "backend-gate-cutover-mutation-test",
            30,
            max_total=1,
            type_limits={"maintenance": 1},
            blocked_validator_types=frozenset({"command"}),
        )
        self.assertIsNotNone(claim)
        assert claim is not None
        self.assertEqual(job_id, claim.job_id)

        backend_result = type(
            "BackendResultDouble",
            (),
            {
                "exit_code": 0,
                "session_id": "session-backend-gate-cutover",
                "stdout_tail": "",
                "stderr_tail": "",
                "timed_out": False,
                "cancelled": False,
                "usage": {},
            },
        )()

        def fake_start(
            _backend: object,
            _prompt: str,
            workspace: Path,
            _logs: Path,
            **_kwargs: object,
        ) -> object:
            (workspace / "BACKEND_READY.txt").write_text(
                CODEX_BACKEND_GATE_OUTPUT, encoding="utf-8"
            )
            return backend_result

        original_validate = Validator.run

        def validate_then_mutate(
            validator: Validator,
            current_job_id: str,
            workspace: Path,
            *args: object,
            **kwargs: object,
        ) -> object:
            results = original_validate(
                validator, current_job_id, workspace, *args, **kwargs
            )
            (workspace / "BACKEND_READY.txt").write_text(
                "MUTATED_AFTER_VALIDATION\n", encoding="utf-8"
            )
            return results

        with patch(
            "learnfactory.handlers.ExecBackend.start_job", new=fake_start
        ), patch("learnfactory.worker.Validator.run", new=validate_then_mutate):
            exit_code = run_worker(
                job_id,
                "backend-gate-cutover-mutation-test",
                claim.lease_token,
                self.config_path,
            )

        self.assertEqual(6, exit_code)
        job = self.jobs.get(job_id)
        assert job is not None
        self.assertEqual("FAILED", job["state"])
        self.assertEqual("validation_failure", job["failure_kind"])
        self.assertIn("authoritative validation snapshot changed", job["error"])
        with self.db.connect() as connection:
            self.assertEqual(
                ["PASS", "PASS"],
                [
                    row["status"]
                    for row in connection.execute(
                        "SELECT status FROM validations WHERE job_id=? "
                        "ORDER BY validation_id",
                        (job_id,),
                    ).fetchall()
                ],
            )
            self.assertEqual(
                0,
                connection.execute(
                    "SELECT COUNT(*) FROM artifacts WHERE job_id=?", (job_id,)
                ).fetchone()[0],
            )

    def test_real_backend_gate_publishes_cutover_and_unlocks_dependency(self) -> None:
        job_id = seed_codex_backend_gate(self.jobs)
        dependent_id = self.jobs.create(
            "fake",
            "test",
            {"files": {"dependent.txt": "ready\n"}},
            job_id="job_after_backend_gate",
            dependencies=(job_id,),
        )
        self.jobs.promote_eligible()
        self.assertEqual("DISCOVERED", self.jobs.get(dependent_id)["state"])
        claim = self.jobs.claim_next(
            "backend-gate-cutover-success-test",
            30,
            max_total=1,
            type_limits={"maintenance": 1},
            blocked_validator_types=frozenset({"command"}),
        )
        self.assertIsNotNone(claim)
        assert claim is not None
        self.assertEqual(job_id, claim.job_id)

        backend_result = type(
            "BackendResultDouble",
            (),
            {
                "exit_code": 0,
                "session_id": "session-backend-gate-success",
                "stdout_tail": "",
                "stderr_tail": "",
                "timed_out": False,
                "cancelled": False,
                "usage": {},
            },
        )()

        def fake_start(
            _backend: object,
            _prompt: str,
            workspace: Path,
            _logs: Path,
            **_kwargs: object,
        ) -> object:
            (workspace / "BACKEND_READY.txt").write_text(
                CODEX_BACKEND_GATE_OUTPUT, encoding="utf-8"
            )
            return backend_result

        with patch("learnfactory.handlers.ExecBackend.start_job", new=fake_start):
            exit_code = run_worker(
                job_id,
                "backend-gate-cutover-success-test",
                claim.lease_token,
                self.config_path,
            )

        self.assertEqual(0, exit_code)
        self.assertEqual("SUCCEEDED", self.jobs.get(job_id)["state"])
        self.assertEqual(1, self.jobs.promote_eligible())
        self.assertEqual("READY", self.jobs.get(dependent_id)["state"])
        with self.db.connect() as connection:
            artifact = connection.execute(
                "SELECT path,checksum,metadata_json FROM artifacts WHERE job_id=?",
                (job_id,),
            ).fetchone()
        self.assertIsNotNone(artifact)
        assert artifact is not None
        archived = Path(artifact["path"])
        self.assertEqual(
            CODEX_BACKEND_GATE_OUTPUT,
            (archived / "BACKEND_READY.txt").read_text(encoding="utf-8"),
        )
        metadata = json.loads(artifact["metadata_json"])
        cutover = metadata["authoritative_validation_cutover"]
        self.assertEqual(artifact["checksum"], cutover["selected_output_checksum"])
        self.assertEqual(
            artifact["checksum"], cutover["validation_snapshot_checksum"]
        )

    def test_cancellation_during_projected_archive_preparation_is_not_promoted(self) -> None:
        job_id = self.jobs.create(
            "fake",
            "examiner",
            {},
            job_id="job_projection_cancel_boundary",
            max_attempts=1,
        )
        self.jobs.promote_eligible()
        claim = self.jobs.claim_next(
            "projection-cancel-test",
            30,
            max_total=1,
            type_limits={"examiner": 1},
        )
        assert claim is not None

        def execute_with_output(
            _handlers: JobHandlers,
            _job: object,
            workspace: Path,
            _log_dir: Path,
            _cancel_event: object,
        ) -> HandlerResult:
            (workspace / "REVIEW.md").write_text("review\n", encoding="utf-8")
            return HandlerResult(
                evidence={},
                validators=[
                    {
                        "type": "regular_files",
                        "name": "review-output",
                        "paths": ["REVIEW.md"],
                    }
                ],
                artifact_type="byox-independent-review",
                semantic_path="e2e/projected-review-cancelled",
                archive_paths=("REVIEW.md",),
            )

        original_prepare = WorkspaceManager.prepare_archive

        def prepare_then_cancel(
            manager: WorkspaceManager, *args: object, **kwargs: object
        ) -> object:
            prepared = original_prepare(manager, *args, **kwargs)
            self.jobs.cancel(job_id)
            return prepared

        with patch(
            "learnfactory.worker.JobHandlers.execute", new=execute_with_output
        ), patch(
            "learnfactory.worker.WorkspaceManager.prepare_archive",
            new=prepare_then_cancel,
        ):
            exit_code = run_worker(
                job_id,
                "projection-cancel-test",
                claim.lease_token,
                self.config_path,
            )

        self.assertEqual(130, exit_code)
        job = self.jobs.get(job_id)
        assert job is not None
        self.assertEqual("CANCELLED", job["state"])
        with self.db.connect() as connection:
            self.assertEqual(
                0,
                connection.execute(
                    "SELECT COUNT(*) FROM artifacts WHERE job_id=?", (job_id,)
                ).fetchone()[0],
            )
        self.assertFalse(
            any(
                path.name.startswith(".archive-projection-")
                for path in (self.settings.warehouse / "workspaces").rglob("*")
            )
        )

    def test_local_lease_loss_after_handler_never_publishes(self) -> None:
        job_id, owner, lease_token = self._claimed_boundary_job("after_handler")
        original_execute = JobHandlers.execute

        def execute_then_cancel(
            handlers: JobHandlers,
            job: object,
            workspace: Path,
            log_dir: Path,
            cancel_event: object,
        ) -> HandlerResult:
            result = original_execute(handlers, job, workspace, log_dir, cancel_event)  # type: ignore[arg-type]
            cancel_event.set()  # type: ignore[attr-defined]
            return result

        with patch(
            "learnfactory.worker.JobHandlers.execute", new=execute_then_cancel
        ):
            exit_code = run_worker(job_id, owner, lease_token, self.config_path)

        self._assert_local_boundary_stop(job_id, exit_code)

    def test_local_lease_loss_after_validation_never_publishes(self) -> None:
        job_id, owner, lease_token = self._claimed_boundary_job("after_validation")
        original_validate = Validator.run

        def validate_then_cancel(
            validator: Validator, *args: object, **kwargs: object
        ) -> list[ValidationResult]:
            result = original_validate(validator, *args, **kwargs)  # type: ignore[arg-type]
            kwargs["cancel_event"].set()  # type: ignore[union-attr]
            return result

        with patch("learnfactory.worker.Validator.run", new=validate_then_cancel):
            exit_code = run_worker(job_id, owner, lease_token, self.config_path)

        self._assert_local_boundary_stop(job_id, exit_code)

    def test_local_lease_loss_after_archive_preparation_never_publishes(self) -> None:
        job_id, owner, lease_token = self._claimed_boundary_job("after_archive")
        original_execute = JobHandlers.execute
        original_prepare = WorkspaceManager.prepare_archive
        observed_cancel_event: list[object] = []

        def remember_cancel_event(
            handlers: JobHandlers,
            job: object,
            workspace: Path,
            log_dir: Path,
            cancel_event: object,
        ) -> HandlerResult:
            observed_cancel_event.append(cancel_event)
            return original_execute(handlers, job, workspace, log_dir, cancel_event)  # type: ignore[arg-type]

        def prepare_then_cancel(
            manager: WorkspaceManager, *args: object, **kwargs: object
        ) -> object:
            prepared = original_prepare(manager, *args, **kwargs)
            observed_cancel_event[0].set()  # type: ignore[attr-defined]
            return prepared

        with patch(
            "learnfactory.worker.JobHandlers.execute", new=remember_cancel_event
        ), patch(
            "learnfactory.worker.WorkspaceManager.prepare_archive",
            new=prepare_then_cancel,
        ):
            exit_code = run_worker(job_id, owner, lease_token, self.config_path)

        self._assert_local_boundary_stop(job_id, exit_code)

    def test_local_lease_loss_at_final_publication_gate_never_publishes(self) -> None:
        job_id, owner, lease_token = self._claimed_boundary_job("final_gate")
        real_quiesce = worker_module._quiesced_heartbeat_publication

        @contextlib.contextmanager
        def cancel_before_publication(
            gate: worker_module._HeartbeatPublicationGate,
            heartbeat: object,
        ) -> object:
            with real_quiesce(gate, heartbeat):  # type: ignore[arg-type]
                gate.request_local_cancel()
                yield

        with patch(
            "learnfactory.worker._quiesced_heartbeat_publication",
            new=cancel_before_publication,
        ):
            exit_code = run_worker(job_id, owner, lease_token, self.config_path)

        self._assert_local_boundary_stop(job_id, exit_code)

    def test_publication_authority_violation_is_permanent_not_dependency_block(
        self,
    ) -> None:
        job_id, owner, lease_token = self._claimed_boundary_job(
            "publication_authority"
        )
        original_execute = JobHandlers.execute

        def execute_with_forbidden_publication(
            handlers: JobHandlers,
            job: object,
            workspace: Path,
            log_dir: Path,
            cancel_event: object,
        ) -> HandlerResult:
            result = original_execute(  # type: ignore[arg-type]
                handlers, job, workspace, log_dir, cancel_event
            )
            result.on_publish = lambda connection: connection.execute(
                "UPDATE jobs SET state='SUCCEEDED' WHERE job_id=?", (job_id,)
            )
            result.publication_scope = PublicationScope.SOURCE_INGESTION
            return result

        with patch(
            "learnfactory.worker.JobHandlers.execute",
            new=execute_with_forbidden_publication,
        ):
            exit_code = run_worker(job_id, owner, lease_token, self.config_path)

        self.assertEqual(6, exit_code)
        record = self.jobs.get(job_id)
        assert record is not None
        self.assertEqual("FAILED", record["state"])
        self.assertEqual("publication_failure", record["failure_kind"])
        with self.db.connect() as connection:
            self.assertEqual(
                0,
                connection.execute(
                    "SELECT COUNT(*) FROM artifacts WHERE job_id=?", (job_id,)
                ).fetchone()[0],
            )

    def test_supervisor_signal_before_final_publication_linearization_interrupts(
        self,
    ) -> None:
        job_id, owner, lease_token = self._claimed_boundary_job(
            "supervisor_before_final"
        )
        real_quiesce = worker_module._quiesced_heartbeat_publication

        @contextlib.contextmanager
        def signal_before_final_fence(
            gate: worker_module._HeartbeatPublicationGate,
            heartbeat: object,
        ) -> object:
            with real_quiesce(gate, heartbeat):  # type: ignore[arg-type]
                signal.raise_signal(signal.SIGTERM)
                yield

        with patch(
            "learnfactory.worker._quiesced_heartbeat_publication",
            new=signal_before_final_fence,
        ):
            exit_code = run_worker(job_id, owner, lease_token, self.config_path)

        self.assertEqual(143, exit_code)
        record = self.jobs.get(job_id)
        assert record is not None
        self.assertEqual("RETRY_WAIT", record["state"])
        self.assertEqual("worker_interrupted", record["failure_kind"])
        with self.db.connect() as connection:
            self.assertEqual(
                0,
                connection.execute(
                    "SELECT COUNT(*) FROM artifacts WHERE job_id=?", (job_id,)
                ).fetchone()[0],
            )

    def test_supervisor_signal_after_final_publication_linearization_keeps_success(
        self,
    ) -> None:
        job_id, owner, lease_token = self._claimed_boundary_job(
            "supervisor_after_final"
        )
        real_succeed = JobRepository.succeed_with_artifact
        signal_injected = False

        def signal_after_final_fence(
            repository: JobRepository, *args: object, **kwargs: object
        ) -> None:
            nonlocal signal_injected
            signal.raise_signal(signal.SIGTERM)
            signal_injected = True
            real_succeed(repository, *args, **kwargs)  # type: ignore[arg-type]

        with patch.object(
            JobRepository,
            "succeed_with_artifact",
            new=signal_after_final_fence,
        ):
            exit_code = run_worker(job_id, owner, lease_token, self.config_path)

        self.assertTrue(signal_injected)
        self.assertEqual(0, exit_code)
        self.assertEqual("SUCCEEDED", self.jobs.get(job_id)["state"])
        with self.db.connect() as connection:
            self.assertEqual(
                1,
                connection.execute(
                    "SELECT COUNT(*) FROM artifacts WHERE job_id=?", (job_id,)
                ).fetchone()[0],
            )

    def test_expired_claim_is_recovered_and_next_attempt_completes(self) -> None:
        job_id = self.jobs.create(
            "fake", "test", {"files": {"result.txt": "recovered\n"}, "artifact_path": "e2e/recovery"},
            max_attempts=2,
        )
        self.jobs.promote_eligible()
        abandoned = self.jobs.claim_next("dead-controller", 0.01, max_total=1, type_limits={"test": 1})
        self.assertIsNotNone(abandoned)
        self.assertEqual(self.jobs.recover_expired(at=now() + 1), 1)
        self.jobs.promote_eligible(at=now() + 2)
        asyncio.run(run_scheduler(self.settings, self.db, until_idle=True, max_jobs=1))
        record = self.jobs.get(job_id)
        self.assertEqual(record["state"], "SUCCEEDED")
        self.assertEqual(record["attempt_count"], 2)
        with self.db.connect() as connection:
            lease_events = connection.execute(
                "SELECT COUNT(*) FROM events WHERE job_id=? AND type='LEASE_EXPIRED'", (job_id,)
            ).fetchone()[0]
            run = connection.execute(
                "SELECT attempt_number,stdout_path,stderr_path FROM job_runs WHERE job_id=?",
                (job_id,),
            ).fetchone()
        self.assertEqual(lease_events, 1)
        self.assertEqual(2, run["attempt_number"])
        attempt_log_dir = self.settings.warehouse / "logs" / job_id / "attempt-002"
        self.assertEqual(attempt_log_dir / "worker.stdout.log", Path(run["stdout_path"]))
        self.assertEqual(attempt_log_dir / "worker.stderr.log", Path(run["stderr_path"]))
        self.assertTrue(Path(run["stdout_path"]).is_file())
        self.assertTrue(Path(run["stderr_path"]).is_file())

    def test_active_cancellation_terminates_without_artifact(self) -> None:
        job_id = self.jobs.create(
            "fake",
            "test",
            {"delay": 5, "files": {"too-late.txt": "bad\n"}, "artifact_path": "e2e/cancel"},
            max_attempts=1,
        )
        self.jobs.promote_eligible()

        async def scenario() -> None:
            scheduler = Scheduler(self.settings, self.db)
            task = asyncio.create_task(scheduler.run(until_idle=True, max_jobs=1))
            for _ in range(250):
                if self.jobs.get(job_id)["state"] == "RUNNING":
                    break
                await asyncio.sleep(0.02)
            else:
                self.fail("worker never entered RUNNING")
            self.jobs.cancel(job_id)
            await asyncio.wait_for(task, timeout=3)

        asyncio.run(scenario())
        self.assertEqual(self.jobs.get(job_id)["state"], "CANCELLED")
        with self.db.connect() as connection:
            artifacts = connection.execute("SELECT COUNT(*) FROM artifacts WHERE job_id=?", (job_id,)).fetchone()[0]
        self.assertEqual(artifacts, 0)

    def test_cancelled_claim_is_reconciled_when_worker_loses_start_race(self) -> None:
        job_id = self.jobs.create("fake", "test", {"files": {"late.txt": "no\n"}})
        self.jobs.promote_eligible()
        claim = self.jobs.claim_next(
            "prestart-owner", 30, max_total=1, type_limits={}
        )
        assert claim is not None
        self.jobs.cancel(job_id)

        exit_code = run_worker(
            job_id, "prestart-owner", claim.lease_token, self.config_path
        )

        self.assertEqual(4, exit_code)
        self.assertEqual("CANCELLED", self.jobs.get(job_id)["state"])

    def test_late_worker_exit_does_not_overwrite_lost_worker_state(self) -> None:
        job_id = self.jobs.create(
            "fake",
            "test",
            {"delay": 5, "files": {"late.txt": "no\n"}},
            max_attempts=2,
        )
        self.jobs.promote_eligible()

        async def scenario() -> None:
            scheduler = Scheduler(self.settings, self.db)
            task = asyncio.create_task(scheduler.run(until_idle=True, max_jobs=1))
            for _ in range(250):
                if self.jobs.get(job_id)["state"] == "RUNNING":
                    break
                await asyncio.sleep(0.02)
            else:
                self.fail("worker never entered RUNNING")
            with self.db.transaction(immediate=True) as connection:
                connection.execute(
                    "UPDATE jobs SET lease_expires_at=? WHERE job_id=?",
                    (now() - 1, job_id),
                )
            await asyncio.wait_for(task, timeout=5)

        asyncio.run(scenario())
        with self.db.connect() as connection:
            worker = connection.execute(
                "SELECT state,current_job FROM workers WHERE current_job=? OR state='LOST' ORDER BY started_at DESC LIMIT 1",
                (job_id,),
            ).fetchone()
        self.assertIsNotNone(worker)
        self.assertEqual("LOST", worker["state"])
        self.assertEqual(job_id, worker["current_job"])

    def test_controller_stop_preserves_inflight_job_for_retry(self) -> None:
        job_id = self.jobs.create(
            "fake",
            "test",
            {"delay": 5, "files": {"eventual.txt": "ok\n"}},
            max_attempts=1,
        )
        self.jobs.promote_eligible()

        async def scenario() -> None:
            scheduler = Scheduler(self.settings, self.db)
            task = asyncio.create_task(scheduler.run(until_idle=True, max_jobs=1))
            loop = asyncio.get_running_loop()
            deadline = loop.time() + 15
            while True:
                observed = self.jobs.get(job_id)
                if observed["state"] == "RUNNING":
                    break
                if loop.time() >= deadline:
                    with self.db.connect() as connection:
                        workers = [
                            dict(row)
                            for row in connection.execute(
                                """
                                SELECT worker_id,state,process_id,last_activity,current_job
                                FROM workers WHERE current_job=? ORDER BY started_at
                                """,
                                (job_id,),
                            )
                        ]
                    children = {
                        child_job: child.process.returncode
                        for child_job, child in scheduler.children.items()
                    }
                    self.fail(
                        "worker did not enter RUNNING within 15s: "
                        f"job_state={observed['state']!r}, "
                        f"workers={workers!r}, children={children!r}"
                    )
                await asyncio.sleep(0.02)
            scheduler.request_stop()
            await asyncio.wait_for(task, timeout=5)

        asyncio.run(scenario())
        record = self.jobs.get(job_id)
        self.assertEqual("RETRY_WAIT", record["state"])
        self.assertEqual("worker_interrupted", record["failure_kind"])
        self.assertEqual(1, record["max_attempts"])
        self.assertEqual(1, record["retry_allowance"])

    def test_unexpected_scheduler_error_still_reaps_active_children(self) -> None:
        job_id = self.jobs.create(
            "fake",
            "test",
            {"delay": 5, "files": {"too-late.txt": "no\n"}},
            max_attempts=1,
        )
        self.jobs.promote_eligible()
        spawned: list[asyncio.subprocess.Process] = []
        real_spawn = asyncio.create_subprocess_exec

        async def capture_spawn(*args: object, **kwargs: object) -> asyncio.subprocess.Process:
            process = await real_spawn(*args, **kwargs)
            spawned.append(process)
            return process

        async def scenario() -> None:
            scheduler = Scheduler(self.settings, self.db)
            real_reap = scheduler._reap_children

            async def fail_after_dispatch() -> None:
                if scheduler.children:
                    raise RuntimeError("injected scheduler-loop failure")
                await real_reap()

            with patch(
                "learnfactory.scheduler.asyncio.create_subprocess_exec",
                side_effect=capture_spawn,
            ), patch.object(scheduler, "_reap_children", side_effect=fail_after_dispatch):
                with self.assertRaisesRegex(RuntimeError, "injected scheduler-loop failure"):
                    await scheduler.run(until_idle=True, max_jobs=1)
            self.assertFalse(scheduler.children)

        asyncio.run(scenario())
        self.assertEqual(1, len(spawned))
        self.assertIsNotNone(spawned[0].returncode)
        with self.db.connect() as connection:
            stopped = connection.execute(
                """
                SELECT payload_json FROM events
                WHERE type='SCHEDULER_STOPPED' ORDER BY event_id DESC LIMIT 1
                """
            ).fetchone()
        self.assertIsNotNone(stopped)
        self.assertTrue(json.loads(stopped["payload_json"])["aborted"])

    def test_post_spawn_event_failure_reaps_unregistered_child(self) -> None:
        job_id = self.jobs.create(
            "fake",
            "test",
            {"delay": 5, "files": {"too-late.txt": "no\n"}},
            max_attempts=1,
        )
        self.jobs.promote_eligible()
        scheduler = Scheduler(self.settings, self.db)
        claim = self.jobs.claim_next(
            scheduler.owner,
            self.settings.lease_seconds,
            max_total=1,
            type_limits={"test": 1},
        )
        assert claim is not None
        spawned: list[asyncio.subprocess.Process] = []
        real_spawn = asyncio.create_subprocess_exec
        real_emit = self.db.emit_event

        async def capture_spawn(*args: object, **kwargs: object) -> asyncio.subprocess.Process:
            process = await real_spawn(*args, **kwargs)
            spawned.append(process)
            return process

        def fail_started_event(actor: str, event_type: str, **kwargs: object) -> None:
            if event_type == "WORKER_PROCESS_STARTED":
                raise sqlite3.OperationalError("injected event write failure")
            real_emit(actor, event_type, **kwargs)

        async def scenario() -> None:
            with patch(
                "learnfactory.scheduler.asyncio.create_subprocess_exec",
                side_effect=capture_spawn,
            ), patch.object(self.db, "emit_event", side_effect=fail_started_event):
                with self.assertRaisesRegex(
                    sqlite3.OperationalError, "injected event write failure"
                ):
                    await scheduler._launch(
                        claim.job_id, claim.lease_token, claim.attempt_count
                    )

        asyncio.run(scenario())
        self.assertFalse(scheduler.children)
        self.assertEqual(1, len(spawned))
        self.assertIsNotNone(spawned[0].returncode)

    def test_dependency_staging_requires_declared_success_and_intact_checksum(self) -> None:
        parent = self.jobs.create(
            "fake",
            "test",
            {
                "files": {"student_safe/public.txt": "safe\n"},
                "artifact_path": "e2e/dependency",
            },
            max_attempts=1,
        )
        self.jobs.promote_eligible()
        asyncio.run(run_scheduler(self.settings, self.db, until_idle=True, max_jobs=1))
        with self.db.connect() as connection:
            artifact_path = Path(
                connection.execute(
                    "SELECT path FROM artifacts WHERE job_id=?", (parent,)
                ).fetchone()["path"]
            )

        undeclared = self.jobs.create(
            "codex_task",
            "student",
            {
                "inputs_from_dependencies": [
                    {
                        "job_id": parent,
                        "subpath": "student_safe/public.txt",
                        "destination": "public.txt",
                    }
                ]
            },
        )
        self.jobs.promote_eligible()
        undeclared_claim = self.jobs.claim_next(
            "security-test", 30, max_total=1, type_limits={}
        )
        assert undeclared_claim is not None
        undeclared_workspace = WorkspaceManager(
            self.settings.warehouse, self.db
        ).allocate(undeclared, undeclared_claim.attempt_count)
        with self.assertRaisesRegex(HandlerFailure, "declared dependency"):
            JobHandlers(
                self.settings, self.db, WorkspaceManager(self.settings.warehouse, self.db)
            )._stage_declared_inputs(undeclared_claim, undeclared_workspace)

        # Release the synthetic claim, then construct a correctly declared child.
        self.jobs.fail(
            undeclared,
            "security-test",
            undeclared_claim.lease_token,
            None,
            kind="test",
            error="expected boundary failure",
            retryable=False,
        )

        disguised = self.jobs.create(
            "codex_task",
            "student",
            {
                "inputs_from_dependencies": [
                    {
                        "job_id": parent,
                        "subpath": "answers/RUBRIC.md",
                        "destination": "RUBRIC.md",
                    }
                ]
            },
            dependencies=[parent],
        )
        self.jobs.promote_eligible()
        disguised_claim = self.jobs.claim_next(
            "security-test-disguised", 30, max_total=1, type_limits={}
        )
        assert disguised_claim is not None
        disguised_workspace = WorkspaceManager(
            self.settings.warehouse, self.db
        ).allocate(disguised, disguised_claim.attempt_count)
        with self.assertRaisesRegex(WorkspaceError, "under student_safe"):
            JobHandlers(
                self.settings, self.db, WorkspaceManager(self.settings.warehouse, self.db)
            )._stage_declared_inputs(disguised_claim, disguised_workspace)
        self.jobs.fail(
            disguised,
            "security-test-disguised",
            disguised_claim.lease_token,
            None,
            kind="test",
            error="expected positive-boundary failure",
            retryable=False,
        )

        copied = self.jobs.create(
            "codex_task",
            "student",
            {
                "inputs_from_dependencies": [
                    {
                        "job_id": parent,
                        "subpath": "student_safe/public.txt",
                        "destination": "public.txt",
                    }
                ]
            },
            dependencies=[parent],
        )
        self.jobs.promote_eligible()
        copied_claim = self.jobs.claim_next(
            "security-test-copy", 30, max_total=1, type_limits={}
        )
        assert copied_claim is not None
        copied_workspace = WorkspaceManager(
            self.settings.warehouse, self.db
        ).allocate(copied, copied_claim.attempt_count)
        real_copytree = shutil.copytree

        def mutate_live_after_copy(source: Path, destination: Path) -> Path:
            result = real_copytree(source, destination, symlinks=True)
            (source / "student_safe/public.txt").write_text(
                "mutated-after-copy\n", encoding="utf-8"
            )
            return result

        with patch(
            "learnfactory.handlers._copy_dependency_tree",
            side_effect=mutate_live_after_copy,
        ):
            JobHandlers(
                self.settings, self.db, WorkspaceManager(self.settings.warehouse, self.db)
            )._stage_declared_inputs(copied_claim, copied_workspace)
        self.assertEqual(
            "safe\n", (copied_workspace / "public.txt").read_text(encoding="utf-8")
        )
        self.assertEqual(
            "mutated-after-copy\n",
            (artifact_path / "student_safe/public.txt").read_text(encoding="utf-8"),
        )
        self.jobs.fail(
            copied,
            "security-test-copy",
            copied_claim.lease_token,
            None,
            kind="test",
            error="copy integrity exercised",
            retryable=False,
        )
        (artifact_path / "student_safe/public.txt").write_text(
            "safe\n", encoding="utf-8"
        )

        declared = self.jobs.create(
            "codex_task",
            "student",
            {
                "inputs_from_dependencies": [
                    {
                        "job_id": parent,
                        "subpath": "student_safe/public.txt",
                        "destination": "public.txt",
                    }
                ]
            },
            dependencies=[parent],
        )
        self.jobs.promote_eligible()
        declared_claim = self.jobs.claim_next(
            "security-test-2", 30, max_total=1, type_limits={}
        )
        assert declared_claim is not None
        declared_workspace = WorkspaceManager(
            self.settings.warehouse, self.db
        ).allocate(declared, declared_claim.attempt_count)
        (artifact_path / "student_safe/public.txt").write_text(
            "tampered\n", encoding="utf-8"
        )
        with self.assertRaisesRegex(HandlerFailure, "checksum mismatch"):
            JobHandlers(
                self.settings, self.db, WorkspaceManager(self.settings.warehouse, self.db)
            )._stage_declared_inputs(declared_claim, declared_workspace)
        self.jobs.fail(
            declared,
            "security-test-2",
            declared_claim.lease_token,
            None,
            kind="test",
            error="expected integrity failure",
            retryable=False,
        )

        secret = self.settings.warehouse / "sealed-answer.txt"
        secret.write_text("sealed\n", encoding="utf-8")
        direct = self.jobs.create(
            "codex_task",
            "student",
            {
                "inputs": [
                    {"source": str(secret), "destination": "answer.txt"}
                ]
            },
        )
        self.jobs.promote_eligible()
        direct_claim = self.jobs.claim_next(
            "security-test-3", 30, max_total=1, type_limits={}
        )
        assert direct_claim is not None
        direct_workspace = WorkspaceManager(
            self.settings.warehouse, self.db
        ).allocate(direct, direct_claim.attempt_count)
        with self.assertRaisesRegex(WorkspaceError, "outside allowed roots"):
            JobHandlers(
                self.settings, self.db, WorkspaceManager(self.settings.warehouse, self.db)
            )._stage_declared_inputs(direct_claim, direct_workspace)

    def test_dependency_directory_staging_is_verified_and_read_only(self) -> None:
        parent = self.jobs.create(
            "fake",
            "test",
            {
                "files": {
                    "candidate/src/main.c": "int main(void) { return 0; }\n",
                    "candidate/tests/README.md": "independent tests\n",
                },
                "artifact_path": "e2e/directory-dependency",
            },
            max_attempts=1,
        )
        self.jobs.promote_eligible()
        asyncio.run(run_scheduler(self.settings, self.db, until_idle=True, max_jobs=1))
        child = self.jobs.create(
            "codex_task",
            "examiner",
            {
                "inputs_from_dependencies": [
                    {
                        "job_id": parent,
                        "subpath": "candidate/src",
                        "destination": "CANDIDATE/src",
                    },
                    {
                        "job_id": parent,
                        "subpath": "candidate/tests",
                        "destination": "CANDIDATE/tests",
                    }
                ],
                "protected_input_roots": ["CANDIDATE"],
            },
            dependencies=[parent],
        )
        self.jobs.promote_eligible()
        claim = self.jobs.claim_next(
            "directory-stage-test", 30, max_total=1, type_limits={}
        )
        assert claim is not None
        manager = WorkspaceManager(self.settings.warehouse, self.db)
        workspace = manager.allocate(child, claim.attempt_count)

        with patch(
            "learnfactory.handlers._copy_dependency_tree",
            wraps=shutil.copytree,
        ) as snapshot_copy:
            integrity, provenance = JobHandlers(
                self.settings, self.db, manager
            )._stage_declared_inputs(claim, workspace)

        staged = workspace / "CANDIDATE"
        self.assertEqual(1, snapshot_copy.call_count)
        self.assertEqual(2, len(provenance))
        self.assertEqual(["CANDIDATE"], [record["path"] for record in integrity])
        self.assertEqual(
            "regular-files-nlink-one-unique-v1",
            integrity[0]["fresh_inode_policy"],
        )
        self.assertEqual(2, integrity[0]["regular_file_count"])
        self.assertEqual(
            "int main(void) { return 0; }\n",
            (staged / "src/main.c").read_text(encoding="utf-8"),
        )
        self.assertEqual(0, (staged / "src/main.c").stat().st_mode & 0o222)
        self.assertEqual(0, staged.stat().st_mode & 0o222)
        validator = Validator(self.db)
        valid = validator.run(
            child,
            workspace,
            [
                {
                    "type": "input_integrity",
                    "name": "input-bind",
                    "inputs": integrity,
                    "require_fresh_inodes": True,
                }
            ],
            self.root / "validation-logs",
            attempt_number=claim.attempt_count,
        )
        self.assertTrue(valid[0].passed)
        # Replacing a file and restoring identical bytes/mode must not defeat
        # validation: the staged copy is bound to its fresh inode inventory.
        staged.chmod(staged.stat().st_mode | 0o200)
        source = staged / "src/main.c"
        source.parent.chmod(source.parent.stat().st_mode | 0o200)
        source.unlink()
        source.write_text("int main(void) { return 0; }\n", encoding="utf-8")
        source.chmod(0o444)
        tampered = validator.run(
            child,
            workspace,
            [
                {
                    "type": "input_integrity",
                    "name": "input-bind",
                    "inputs": integrity,
                    "require_fresh_inodes": True,
                }
            ],
            self.root / "validation-logs",
            attempt_number=claim.attempt_count,
        )
        self.assertFalse(tampered[0].passed)
        self.assertEqual(
            "inode-identity-mismatch",
            tampered[0].evidence["mismatches"][0]["reason"],
        )

    def test_stage_tree_rejects_symlinks(self) -> None:
        manager = WorkspaceManager(self.settings.warehouse, self.db)
        source = self.root / "unsafe-tree"
        source.mkdir()
        (source / "regular.txt").write_text("safe\n", encoding="utf-8")
        (source / "escape").symlink_to(self.root / "outside")
        workspace = self.root / "manual-workspace"
        workspace.mkdir()

        with self.assertRaisesRegex(WorkspaceError, "contains a symlink"):
            manager.stage_tree(source, workspace, "CANDIDATE")
        self.assertFalse((workspace / "CANDIDATE").exists())

    def test_stage_tree_breaks_source_hardlinks_into_fresh_inodes(self) -> None:
        manager = WorkspaceManager(self.settings.warehouse, self.db)
        source = self.root / "hardlinked-source"
        source.mkdir()
        first = source / "first.txt"
        second = source / "second.txt"
        first.write_text("same inode at source\n", encoding="utf-8")
        second.hardlink_to(first)
        self.assertEqual(first.stat().st_ino, second.stat().st_ino)
        workspace = self.root / "hardlink-workspace"
        workspace.mkdir()

        staged = manager.stage_tree(source, workspace, "CANDIDATE")

        copied_first = staged / "first.txt"
        copied_second = staged / "second.txt"
        self.assertEqual(1, copied_first.stat().st_nlink)
        self.assertEqual(1, copied_second.stat().st_nlink)
        self.assertNotEqual(copied_first.stat().st_ino, copied_second.stat().st_ino)


if __name__ == "__main__":
    unittest.main()
