from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from learnfactory.db import Database
from learnfactory.jobs import JobRepository
from learnfactory.util import now, tree_sha256, tree_sha256_v1
from learnfactory.validation import Validator
from learnfactory.workspace import WorkspaceError, WorkspaceManager


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_FILES = sorted((REPOSITORY_ROOT / "migrations").glob("[0-9][0-9][0-9]_*.sql"))


class WorkspaceValidationTestCase(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="learnfactory-workspace-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.migrations = self.root / "migrations"
        self.migrations.mkdir()
        for migration in MIGRATION_FILES:
            shutil.copy2(migration, self.migrations / migration.name)
        self.database = Database(self.root / "factory.db", self.migrations)
        self.database.migrate()
        self.jobs = JobRepository(self.database)
        self.warehouse = self.root / "warehouse"
        self.manager = WorkspaceManager(self.warehouse, self.database)
        self.manager.initialize()

    def _job(self, identifier: str) -> str:
        return self.jobs.create("test_job", "test", {}, job_id=identifier)

    def _active_job(self, identifier: str) -> tuple[str, str, str, Path]:
        job_id = self._job(identifier)
        self.jobs.promote_eligible()
        claim = self.jobs.claim_next(
            "workspace-test-owner", lease_seconds=30, max_total=1, type_limits={}
        )
        assert claim is not None
        workspace = self.manager.allocate(job_id, claim.attempt_count)
        worker_id = f"worker_{identifier}"
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                """
                INSERT INTO workers(worker_id,type,workspace,state,started_at,last_activity,current_job)
                VALUES (?,?,?,?,?,?,?)
                """,
                (worker_id, "test", str(workspace), "STARTING", now(), now(), job_id),
            )
        self.jobs.start(
            job_id, "workspace-test-owner", claim.lease_token, worker_id, str(workspace)
        )
        return job_id, claim.lease_token, worker_id, workspace


class ValidationTests(WorkspaceValidationTestCase):
    def test_shared_workspace_ancestor_churn_does_not_forge_path_rebinding(self) -> None:
        job_id = self._job("job_validator_shared_ancestor_churn")
        shared = self.root / "shared-ancestor"
        workspace = shared / "workspaces" / "job" / "attempt-001"
        (workspace / "starter").mkdir(parents=True)
        (workspace / "starter" / "main.py").write_text(
            "print('stable')\n", encoding="utf-8"
        )
        specification = {
            "type": "forbidden_tree_names",
            "name": "no-sealed-starter-content",
            "roots": ["starter"],
            "names": ["sealed", "solution"],
            "max_entries": 100,
        }
        validator = Validator(self.database)
        baseline = validator.run(
            job_id,
            workspace,
            [specification],
            self.root / "logs" / job_id / "baseline",
        )[0]
        real_open = os.open
        mutated = False

        def churn_shared_ancestor(path, flags, *args, **kwargs):
            nonlocal mutated
            if (
                not mutated
                and path == shared.name
                and kwargs.get("dir_fd") is not None
            ):
                os.utime(shared, None)
                mutated = True
            return real_open(path, flags, *args, **kwargs)

        with patch(
            "learnfactory.validation.os.open",
            side_effect=churn_shared_ancestor,
        ):
            observed = validator.run(
                job_id,
                workspace,
                [specification],
                self.root / "logs" / job_id / "churn",
            )[0]

        self.assertTrue(mutated)
        self.assertEqual("PASS", baseline.status)
        self.assertEqual("PASS", observed.status)
        self.assertEqual(baseline.evidence, observed.evidence)

    def test_json_contract_requires_object_and_schema_types(self) -> None:
        job_id = self._job("job_json_contract")
        workspace = self.root / "json-contract"
        workspace.mkdir()
        document = workspace / "evaluation.json"
        document.write_text('["result", "score"]\n', encoding="utf-8")
        fields = Validator(self.database).run(
            job_id,
            workspace,
            [{"type": "json_fields", "path": "evaluation.json", "required": ["result"]}],
            self.root / "logs" / job_id,
        )
        self.assertEqual("FAIL", fields[0].status)

        document.write_text('{"result":"PASS","score":101}\n', encoding="utf-8")
        schema = Validator(self.database).run(
            job_id,
            workspace,
            [
                {
                    "type": "json_schema",
                    "path": "evaluation.json",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "result": {"type": "string", "enum": ["PASS", "FAIL"]},
                            "score": {"type": "number", "minimum": 0, "maximum": 100},
                        },
                        "required": ["result", "score"],
                        "additionalProperties": False,
                    },
                }
            ],
            self.root / "logs" / job_id / "schema",
        )
        self.assertEqual("FAIL", schema[0].status)
        self.assertTrue(any("maximum" in error for error in schema[0].evidence["errors"]))

        document.write_text('{"result":"PASS","score":NaN}\n', encoding="utf-8")
        nonfinite = Validator(self.database).run(
            job_id,
            workspace,
            [
                {
                    "type": "json_schema",
                    "path": "evaluation.json",
                    "schema": {"type": "object", "properties": {"score": {"type": "number"}}},
                }
            ],
            self.root / "logs" / job_id / "nonfinite",
        )
        self.assertEqual("FAIL", nonfinite[0].status)

    def test_malformed_or_unsupported_json_schema_contracts_error(self) -> None:
        job_id = self._job("job_schema_contract_fail_closed")
        workspace = self.root / "schema-contract-fail-closed"
        workspace.mkdir()
        (workspace / "value.json").write_text(
            '{"result":"PASS"}\n', encoding="utf-8"
        )
        malformed = [
            {"type": "object", "properties": []},
            {"type": "object", "required": "result"},
            {"type": "object", "additionalProperties": "false"},
            {"type": "object", "propertiez": {}},
            {"type": "objekt"},
            {"type": "array", "items": []},
            {"type": "string", "minimum": 1},
            {
                "type": "object",
                "properties": {"result": {"type": "string", "typoEnum": ["PASS"]}},
            },
        ]
        results = Validator(self.database).run(
            job_id,
            workspace,
            [
                {
                    "type": "json_schema",
                    "name": f"malformed-schema-{index}",
                    "path": "value.json",
                    "schema": schema,
                    "fail_fast": False,
                }
                for index, schema in enumerate(malformed)
            ],
            self.root / "logs" / job_id,
        )

        self.assertEqual(len(malformed), len(results))
        self.assertTrue(all(result.status == "ERROR" for result in results))
        self.assertTrue(
            all(result.evidence.get("error_count", 0) >= 1 for result in results)
        )

    def test_json_schema_enum_comparison_does_not_alias_booleans_and_numbers(self) -> None:
        job_id = self._job("job_schema_type_aware_enum")
        workspace = self.root / "schema-type-aware-enum"
        workspace.mkdir()
        document = workspace / "value.json"
        document.write_text("true\n", encoding="utf-8")
        boolean_result = Validator(self.database).run(
            job_id,
            workspace,
            [
                {
                    "type": "json_schema",
                    "path": "value.json",
                    "schema": {"type": "boolean", "enum": [1]},
                }
            ],
            self.root / "logs" / job_id / "boolean",
        )[0]
        self.assertEqual("FAIL", boolean_result.status)
        self.assertIn("outside enum", boolean_result.evidence["errors"][0])

        document.write_text("1\n", encoding="utf-8")
        number_result = Validator(self.database).run(
            job_id,
            workspace,
            [
                {
                    "type": "json_schema",
                    "path": "value.json",
                    "schema": {"type": "integer", "enum": [True]},
                }
            ],
            self.root / "logs" / job_id / "number",
        )[0]
        self.assertEqual("FAIL", number_result.status)

    def test_command_validator_kills_daemonized_descendants(self) -> None:
        job_id = self._job("job_validator_descendant")
        workspace = self.root / "validator-descendant"
        workspace.mkdir()
        marker = workspace / "late-write.txt"
        child = (
            "import pathlib,time; time.sleep(0.25); "
            f"pathlib.Path({str(marker)!r}).write_text('changed')"
        )
        parent = (
            "import subprocess,sys; "
            f"subprocess.Popen([sys.executable, '-c', {child!r}])"
        )
        results = Validator(self.database).run(
            job_id,
            workspace,
            [{"type": "command", "argv": [sys.executable, "-c", parent]}],
            self.root / "logs" / job_id,
        )
        self.assertEqual("PASS", results[0].status)
        time.sleep(0.4)
        self.assertFalse(marker.exists())

    def test_command_logs_are_bounded_and_redacted_before_retention(self) -> None:
        job_id = self._job("job_validator_retained_logs")
        workspace = self.root / "validator-retained-logs"
        workspace.mkdir()
        results = Validator(self.database, log_limit_bytes=1024).run(
            job_id,
            workspace,
            [
                {
                    "type": "command",
                    "argv": [
                        sys.executable,
                        "-c",
                        (
                            "import sys; "
                            "sys.stdout.buffer.write(b'HEAD token=stdout-secret\\n' + b'x'*8000 + b'\\nTAIL'); "
                            "sys.stderr.buffer.write(b'HEADERR\\n' + b'y'*8000 + "
                            "b'\\nAuthorization: Bearer stderr-secret\\nTAILERR')"
                        ),
                    ],
                }
            ],
            self.root / "logs" / job_id,
        )

        self.assertEqual("PASS", results[0].status)
        assert results[0].stdout_path is not None
        assert results[0].stderr_path is not None
        self.assertLessEqual(results[0].stdout_path.stat().st_size, 1024)
        self.assertLessEqual(results[0].stderr_path.stat().st_size, 1024)
        stdout = results[0].stdout_path.read_text(encoding="utf-8")
        stderr = results[0].stderr_path.read_text(encoding="utf-8")
        self.assertIn("HEAD", stdout)
        self.assertIn("TAIL", stdout)
        self.assertIn("token=<redacted>", stdout)
        self.assertNotIn("stdout-secret", stdout)
        self.assertIn("HEADERR", stderr)
        self.assertIn("TAILERR", stderr)
        self.assertIn("Authorization: Bearer <redacted>", stderr)
        self.assertNotIn("stderr-secret", stderr)
        self.assertGreater(results[0].evidence["stdout_bytes"], 1024)
        self.assertGreater(results[0].evidence["stderr_bytes"], 1024)

    def test_invalid_command_contracts_are_rejected_before_spawn(self) -> None:
        job_id = self._job("job_validator_invalid_contract")
        workspace = self.root / "validator-invalid-contract"
        workspace.mkdir()
        marker = workspace / "spawned.txt"
        argv = [
            sys.executable,
            "-c",
            f"from pathlib import Path; Path({str(marker)!r}).write_text('spawned')",
        ]
        specifications = [
            {
                "type": "command",
                "name": "nan-timeout",
                "argv": argv,
                "timeout_seconds": math.nan,
                "fail_fast": False,
            },
            {
                "type": "command",
                "name": "zero-timeout",
                "argv": argv,
                "timeout_seconds": 0,
                "fail_fast": False,
            },
            {
                "type": "command",
                "name": "noninteger-exit",
                "argv": argv,
                "expected_exit": "0",
                "fail_fast": False,
            },
            {
                "type": "command",
                "name": "nonobject-env",
                "argv": argv,
                "env": ["UNSAFE=value"],
                "fail_fast": False,
            },
            {
                "type": "command",
                "name": "nested-env",
                "argv": argv,
                "env": {"UNSAFE": {"nested": "value"}},
                "fail_fast": False,
            },
            {
                "type": "command",
                "name": "nonfinite-env",
                "argv": argv,
                "env": {"UNSAFE": math.inf},
                "fail_fast": False,
            },
        ]

        results = Validator(self.database).run(
            job_id,
            workspace,
            specifications,
            self.root / "logs" / job_id,
        )

        self.assertEqual(len(specifications), len(results))
        self.assertTrue(all(result.status == "ERROR" for result in results))
        self.assertFalse(marker.exists())

    def test_later_validator_cannot_mutate_candidate_after_claim(self) -> None:
        job_id = self._job("job_validator_mutation")
        workspace = self.root / "validator-mutation"
        workspace.mkdir()
        candidate = workspace / "program.py"
        candidate.write_text("good\n", encoding="utf-8")
        results = Validator(self.database).run(
            job_id,
            workspace,
            [
                {
                    "type": "command",
                    "name": "assert-good",
                    "argv": [
                        sys.executable,
                        "-c",
                        "from pathlib import Path; assert Path('program.py').read_text() == 'good\\n'",
                    ],
                    "claims": ["TESTED"],
                    "fail_fast": False,
                },
                {
                    "type": "command",
                    "name": "malicious-later-check",
                    "argv": [
                        sys.executable,
                        "-c",
                        "from pathlib import Path; Path('program.py').write_text('bad\\n')",
                    ],
                },
            ],
            self.root / "logs" / job_id,
        )
        self.assertEqual("PASS", results[0].status)
        self.assertEqual(("TESTED",), results[0].claims)
        self.assertEqual("FAIL", results[1].status)
        self.assertIn("mutated candidate", results[1].evidence["error"])

    def test_later_validator_cannot_remove_required_empty_directory(self) -> None:
        job_id = self._job("job_validator_directory_mutation")
        workspace = self.root / "validator-directory-mutation"
        required = workspace / "required-empty-dir"
        required.mkdir(parents=True)
        results = Validator(self.database).run(
            job_id,
            workspace,
            [
                {
                    "type": "required_paths",
                    "name": "required-directory",
                    "paths": ["required-empty-dir"],
                    "claims": ["TESTED"],
                    "fail_fast": False,
                },
                {
                    "type": "command",
                    "name": "remove-directory",
                    "argv": [
                        sys.executable,
                        "-c",
                        "from pathlib import Path; Path('required-empty-dir').rmdir()",
                    ],
                },
            ],
            self.root / "logs" / job_id,
        )
        self.assertEqual("PASS", results[0].status)
        self.assertEqual("FAIL", results[1].status)

    def test_required_forbidden_and_command_validators_record_real_evidence(self) -> None:
        job_id = self._job("job_validation_pass")
        workspace = self.root / "validation-workspace"
        project = workspace / "project"
        project.mkdir(parents=True)
        (workspace / "README.md").write_text("exercise\n", encoding="utf-8")
        marker = workspace / "shell-injection-marker"
        literal_argument = f"; touch {marker}"
        log_dir = self.root / "logs" / job_id

        results = Validator(self.database).run(
            job_id,
            workspace,
            [
                {
                    "type": "required_paths",
                    "name": "required",
                    "paths": ["README.md", "project"],
                },
                {
                    "type": "forbidden_paths",
                    "name": "forbidden",
                    "paths": ["sealed", "reference"],
                },
                {
                    "type": "command",
                    "name": "command",
                    "cwd": "project",
                    "argv": [
                        sys.executable,
                        "-c",
                        "import sys; print(sys.argv[1])",
                        literal_argument,
                    ],
                    "timeout_seconds": 10,
                },
            ],
            log_dir,
        )

        self.assertEqual(["PASS", "PASS", "PASS"], [result.status for result in results])
        self.assertFalse(marker.exists(), "validator argv must not be interpreted by a shell")
        command_result = results[-1]
        self.assertEqual(0, command_result.exit_code)
        self.assertEqual(
            literal_argument,
            command_result.stdout_path.read_text(encoding="utf-8").strip(),
        )
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT validator,status,command_json,exit_code
                FROM validations WHERE job_id=? ORDER BY rowid
                """,
                (job_id,),
            ).fetchall()
        self.assertEqual(3, len(rows))
        self.assertEqual(["PASS", "PASS", "PASS"], [row["status"] for row in rows])
        self.assertEqual(
            [sys.executable, "-c", "import sys; print(sys.argv[1])", literal_argument],
            json.loads(rows[-1]["command_json"]),
        )

    def test_required_forbidden_and_command_failures_are_not_promoted(self) -> None:
        job_id = self._job("job_validation_fail")
        workspace = self.root / "validation-workspace"
        workspace.mkdir()
        (workspace / "forbidden.txt").write_text("must not exist\n", encoding="utf-8")

        results = Validator(self.database).run(
            job_id,
            workspace,
            [
                {
                    "type": "required_paths",
                    "name": "missing-required",
                    "paths": ["missing.txt"],
                    "fail_fast": False,
                },
                {
                    "type": "forbidden_paths",
                    "name": "present-forbidden",
                    "paths": ["forbidden.txt"],
                    "fail_fast": False,
                },
                {
                    "type": "command",
                    "name": "nonzero-command",
                    "argv": [sys.executable, "-c", "raise SystemExit(7)"],
                    "expected_exit": 0,
                    "timeout_seconds": 10,
                    "fail_fast": False,
                },
            ],
            self.root / "logs" / job_id,
        )

        self.assertEqual(["FAIL", "FAIL", "FAIL"], [result.status for result in results])
        self.assertEqual(7, results[-1].exit_code)
        with self.database.connect() as connection:
            persisted = connection.execute(
                "SELECT COUNT(*) AS total, SUM(status='FAIL') AS failed FROM validations WHERE job_id=?",
                (job_id,),
            ).fetchone()
        self.assertEqual(3, persisted["total"])
        self.assertEqual(3, persisted["failed"])

    def test_validator_rejects_escaping_paths_and_invalid_command_argv(self) -> None:
        job_id = self._job("job_validation_escape")
        workspace = self.root / "validation-workspace"
        workspace.mkdir()
        outside = self.root / "outside"
        outside.mkdir()
        (workspace / "outside-link").symlink_to(outside, target_is_directory=True)

        required_escape = Validator(self.database).run(
            job_id,
            workspace,
            [{"type": "required_paths", "name": "escape", "paths": ["../outside"]}],
            self.root / "logs" / job_id,
        )
        cwd_escape = Validator(self.database).run(
            job_id,
            workspace,
            [
                {
                    "type": "command",
                    "name": "cwd-escape",
                    "cwd": "outside-link",
                    "argv": [sys.executable, "-c", "pass"],
                }
            ],
            self.root / "logs" / job_id,
        )
        invalid_argv = Validator(self.database).run(
            job_id,
            workspace,
            [{"type": "command", "name": "invalid-argv", "argv": "echo unsafe"}],
            self.root / "logs" / job_id,
        )

        self.assertEqual("ERROR", required_escape[0].status)
        self.assertEqual("ERROR", cwd_escape[0].status)
        self.assertEqual("ERROR", invalid_argv[0].status)


class WorkspaceTests(WorkspaceValidationTestCase):
    def test_framed_tree_hash_distinguishes_structural_v1_collision(self) -> None:
        first = self.root / "tree-a"
        second = self.root / "tree-b"
        (first / "a").mkdir(parents=True)
        (first / "b").mkdir()
        (second / "aDb").mkdir(parents=True)
        self.assertEqual(tree_sha256_v1(first), tree_sha256_v1(second))
        self.assertNotEqual(tree_sha256(first), tree_sha256(second))

    def test_job_id_cannot_escape_workspace_root(self) -> None:
        escaped = self.root / "escaped-by-job-id"
        with self.assertRaisesRegex(WorkspaceError, "unexpected job id"):
            self.manager.allocate("job_x/../../../escaped-by-job-id", 1)
        self.assertFalse(escaped.exists())

    def test_student_view_excludes_sealed_and_nonpublic_material(self) -> None:
        challenge = self.root / "challenge"
        (challenge / "starter").mkdir(parents=True)
        (challenge / "public_tests").mkdir()
        (challenge / "sealed" / "reference").mkdir(parents=True)
        (challenge / "alternatives").mkdir()
        (challenge / "README.md").write_text("start here\n", encoding="utf-8")
        (challenge / "starter" / "main.py").write_text("pass\n", encoding="utf-8")
        (challenge / "public_tests" / "test_public.py").write_text("pass\n", encoding="utf-8")
        sealed_sentinel = challenge / "sealed" / "reference" / "SENTINEL"
        sealed_sentinel.write_text("answer\n", encoding="utf-8")
        (challenge / "alternatives" / "design.md").write_text("hidden\n", encoding="utf-8")

        view = self.manager.create_student_view(challenge, self.root / "student-view")

        self.assertTrue((view / "README.md").is_file())
        self.assertTrue((view / "starter" / "main.py").is_file())
        self.assertTrue((view / "public_tests" / "test_public.py").is_file())
        self.assertTrue((view / ".isolated-view").is_file())
        self.assertFalse((view / "sealed").exists())
        self.assertFalse((view / "alternatives").exists())
        self.assertFalse(any(path.name == sealed_sentinel.name for path in view.rglob("*")))

    def test_student_view_rejects_symlink_in_public_tree(self) -> None:
        challenge = self.root / "challenge"
        starter = challenge / "starter"
        starter.mkdir(parents=True)
        secret = self.root / "secret.txt"
        secret.write_text("sealed answer\n", encoding="utf-8")
        (starter / "apparently-public.txt").symlink_to(secret)

        with self.assertRaisesRegex(WorkspaceError, "student-visible input contains symlink"):
            self.manager.create_student_view(challenge, self.root / "student-view")

    def test_archive_projection_excludes_staged_inputs_and_rejects_overlap(self) -> None:
        workspace = self.manager.allocate("job_projection_boundary", 1)
        (workspace / "CANDIDATE" / "sealed").mkdir(parents=True)
        (workspace / "CANDIDATE" / "sealed" / "answer.txt").write_text(
            "must not be duplicated\n", encoding="utf-8"
        )
        (workspace / "EVALUATION.json").write_text(
            '{"verdict":"REVISE"}\n', encoding="utf-8"
        )
        (workspace / "REVIEW.md").write_text("review\n", encoding="utf-8")
        (workspace / "VALIDATION.md").write_text("checks\n", encoding="utf-8")

        projection = self.manager.create_archive_projection(
            workspace, ("EVALUATION.json", "REVIEW.md", "VALIDATION.md")
        )
        self.assertEqual(workspace, projection.parent)
        self.assertEqual(
            ["EVALUATION.json", "REVIEW.md", "VALIDATION.md"],
            sorted(path.name for path in projection.iterdir()),
        )
        self.assertFalse((projection / "CANDIDATE").exists())
        self.manager.discard_archive_projection(projection)
        self.assertFalse(projection.exists())

        with self.assertRaisesRegex(WorkspaceError, "paths overlap"):
            self.manager.create_archive_projection(
                workspace, ("CANDIDATE", "CANDIDATE/sealed/answer.txt")
            )

    def test_archive_projection_cleanup_handles_read_only_output_directories(self) -> None:
        workspace = self.manager.allocate("job_projection_read_only", 1)
        output = workspace / "student_work"
        (output / "nested").mkdir(parents=True)
        (output / "nested" / "submission.md").write_text(
            "finished\n", encoding="utf-8"
        )
        (output / "nested").chmod(0o555)
        output.chmod(0o555)

        projection = self.manager.create_archive_projection(
            workspace, ("student_work",)
        )
        self.assertEqual(
            "finished\n",
            (projection / "student_work/nested/submission.md").read_text(
                encoding="utf-8"
            ),
        )
        self.manager.discard_archive_projection(projection)
        self.assertFalse(projection.exists())

        # Keep TemporaryDirectory cleanup independent from the behavior under test.
        output.chmod(0o755)
        (output / "nested").chmod(0o755)

    def test_archive_projection_does_not_follow_file_replaced_by_symlink(self) -> None:
        workspace = self.manager.allocate("job_projection_symlink_race", 1)
        output = workspace / "REVIEW.md"
        output.write_text("review\n", encoding="utf-8")
        outside = self.root / "sealed.txt"
        outside.write_text("must not be copied\n", encoding="utf-8")
        original_copy = shutil.copy2

        def replace_before_copy(
            source: Path,
            destination: Path,
            *,
            follow_symlinks: bool = True,
        ) -> Path:
            source.unlink()
            source.symlink_to(outside)
            return original_copy(
                source, destination, follow_symlinks=follow_symlinks
            )

        with patch(
            "learnfactory.workspace.shutil.copy2", side_effect=replace_before_copy
        ):
            with self.assertRaisesRegex(WorkspaceError, "symlink"):
                self.manager.create_archive_projection(workspace, ("REVIEW.md",))

        self.assertFalse(
            any(
                path.name.startswith(".archive-projection-")
                for path in self.manager.workspaces.rglob("*")
            )
        )

    def test_archive_projection_detects_output_mutation_during_copy(self) -> None:
        workspace = self.manager.allocate("job_projection_mutation_race", 1)
        output = workspace / "feedback.md"
        output.write_text("validated version\n", encoding="utf-8")
        original_copy = shutil.copy2

        def mutate_after_copy(
            source: Path,
            destination: Path,
            *,
            follow_symlinks: bool = True,
        ) -> Path:
            copied = original_copy(
                source, destination, follow_symlinks=follow_symlinks
            )
            source.write_text("changed version\n", encoding="utf-8")
            return copied

        with patch(
            "learnfactory.workspace.shutil.copy2", side_effect=mutate_after_copy
        ):
            with self.assertRaisesRegex(WorkspaceError, "changed while it was copied"):
                self.manager.create_archive_projection(workspace, ("feedback.md",))

        self.assertFalse(
            any(
                path.name.startswith(".archive-projection-")
                for path in self.manager.workspaces.rglob("*")
            )
        )

    def test_archive_records_checksum_of_exact_copied_tree(self) -> None:
        job_id, lease_token, worker_id, workspace = self._active_job("job_artifact_checksum")
        (workspace / "README.md").write_text("artifact\n", encoding="utf-8")
        (workspace / "src").mkdir()
        (workspace / "src" / "main.py").write_text("print('ok')\n", encoding="utf-8")
        source_checksum = tree_sha256(workspace)

        Validator(self.database).run(
            job_id,
            workspace,
            [
                {
                    "type": "handler_evidence",
                    "name": "artifact-checked",
                    "passed": True,
                    "claims": ["TESTED"],
                }
            ],
            self.root / "logs" / job_id,
            attempt_number=1,
        )
        archived = self.manager.prepare_archive(
            job_id,
            1,
            workspace,
            artifact_type="reference",
            semantic_path="projects/checksum-example",
            metadata={"provenance": "deterministic-test"},
            validation_status="TESTED",
            validation_labels=["GENERATED", "TESTED"],
        )

        self.assertEqual(source_checksum, archived.checksum)
        self.assertEqual(archived.checksum, tree_sha256(archived.path))
        with self.database.connect() as connection:
            self.assertIsNone(
                connection.execute(
                    "SELECT artifact_id FROM artifacts WHERE artifact_id=?",
                    (archived.artifact_id,),
                ).fetchone(),
                "preparation must not publish an artifact",
            )
        self.jobs.succeed_with_artifact(
            job_id, "workspace-test-owner", lease_token, worker_id, archived
        )
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT path,checksum,checksum_algorithm,integrity_status,metadata_json,validation_status
                FROM artifacts WHERE artifact_id=?
                """,
                (archived.artifact_id,),
            ).fetchone()
        self.assertIsNotNone(row)
        assert row is not None
        self.assertEqual(str(archived.path), row["path"])
        self.assertEqual(archived.checksum, row["checksum"])
        self.assertEqual("tree-sha256-v2", row["checksum_algorithm"])
        self.assertEqual("VERIFIED_V2", row["integrity_status"])
        self.assertEqual({"provenance": "deterministic-test"}, json.loads(row["metadata_json"]))
        self.assertEqual("TESTED", row["validation_status"])

        (archived.path / "README.md").write_text("tampered\n", encoding="utf-8")
        self.assertNotEqual(archived.checksum, tree_sha256(archived.path))

    def test_archive_fsyncs_staging_tree_before_atomic_rename(self) -> None:
        job_id = self._job("job_artifact_durable_stage")
        workspace = self.manager.allocate(job_id, 1)
        (workspace / "result.txt").write_text("durable\n", encoding="utf-8")
        events: list[tuple[str, Path, Path | None]] = []
        real_fsync_tree = __import__(
            "learnfactory.workspace", fromlist=["_fsync_tree"]
        )._fsync_tree
        real_rename = os.rename

        def observe_fsync(path: Path) -> None:
            events.append(("fsync", path, None))
            path.resolve().relative_to(self.manager.artifacts.resolve())
            self.assertTrue(path.name.endswith(".staging"))
            real_fsync_tree(path)

        def observe_rename(source: Path, destination: Path) -> None:
            events.append(("rename", Path(source), Path(destination)))
            self.assertEqual(Path(source).parent, Path(destination).parent)
            real_rename(source, destination)

        with patch(
            "learnfactory.workspace._fsync_tree", side_effect=observe_fsync
        ), patch("learnfactory.workspace.os.rename", side_effect=observe_rename):
            artifact = self.manager.prepare_archive(
                job_id,
                1,
                workspace,
                artifact_type="test-output",
                semantic_path="durability/staged",
                metadata={},
            )

        self.assertEqual(["fsync", "rename"], [event[0] for event in events])
        self.assertTrue(artifact.path.is_dir())
        self.assertFalse(
            any(path.name.endswith(".staging") for path in artifact.path.parent.iterdir())
        )
        self.manager.discard_prepared(artifact)

    def test_archive_durability_failure_cleans_staging_and_final_path(self) -> None:
        job_id = self._job("job_artifact_durability_failure")
        workspace = self.manager.allocate(job_id, 1)
        (workspace / "result.txt").write_text("candidate\n", encoding="utf-8")
        destination = (
            self.manager.artifacts
            / "durability/failure"
            / job_id
            / "attempt-001"
        )

        with patch(
            "learnfactory.workspace._fsync_tree",
            side_effect=OSError("injected fsync failure"),
        ):
            with self.assertRaisesRegex(OSError, "injected fsync failure"):
                self.manager.prepare_archive(
                    job_id,
                    1,
                    workspace,
                    artifact_type="test-output",
                    semantic_path="durability/failure",
                    metadata={},
                )

        self.assertFalse(destination.exists())
        self.assertFalse(
            any(
                path.name.endswith(".staging")
                for path in destination.parent.iterdir()
            )
        )

    def test_startup_reconciliation_quarantines_changed_v2_artifact(self) -> None:
        job_id, lease_token, worker_id, workspace = self._active_job(
            "job_artifact_reconcile"
        )
        (workspace / "result.txt").write_text("validated\n", encoding="utf-8")
        Validator(self.database).run(
            job_id,
            workspace,
            [{"type": "handler_evidence", "passed": True}],
            self.root / "logs" / job_id,
            attempt_number=1,
        )
        artifact = self.manager.prepare_archive(
            job_id,
            1,
            workspace,
            artifact_type="test-output",
            semantic_path="durability/reconcile",
            metadata={},
        )
        self.jobs.succeed_with_artifact(
            job_id, "workspace-test-owner", lease_token, worker_id, artifact
        )
        (artifact.path / "result.txt").write_text("damaged\n", encoding="utf-8")

        self.assertEqual(1, self.manager.reconcile_published_artifacts())
        self.assertEqual(0, self.manager.reconcile_published_artifacts())
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT integrity_status,validation_status FROM artifacts
                WHERE artifact_id=?
                """,
                (artifact.artifact_id,),
            ).fetchone()
            label = connection.execute(
                """
                SELECT evidence_json FROM artifact_validation_labels
                WHERE artifact_id=? AND label='PARTIAL'
                """,
                (artifact.artifact_id,),
            ).fetchone()
            events = connection.execute(
                """
                SELECT COUNT(*) AS n FROM events
                WHERE job_id=? AND type='ARTIFACT_INTEGRITY_QUARANTINED'
                """,
                (job_id,),
            ).fetchone()["n"]
        self.assertEqual("LEGACY_UNVERIFIED", row["integrity_status"])
        self.assertIn("PARTIAL", row["validation_status"].split("+"))
        self.assertTrue(json.loads(label["evidence_json"])["integrity_quarantine"])
        self.assertEqual(1, events)

    def test_archive_rejects_symlink_candidates(self) -> None:
        job_id = self._job("job_artifact_symlink")
        workspace = self.manager.allocate(job_id, 1)
        secret = self.root / "secret.txt"
        secret.write_text("do not archive\n", encoding="utf-8")
        (workspace / "reference.txt").symlink_to(secret)

        with self.assertRaisesRegex(WorkspaceError, "may not contain symlinks"):
            self.manager.prepare_archive(
                job_id,
                1,
                workspace,
                artifact_type="reference",
                semantic_path="projects/symlink-example",
                metadata={},
            )

    @unittest.skipUnless(shutil.which("bwrap"), "bubblewrap is not installed")
    def test_bubblewrap_view_cannot_see_sealed_sentinel(self) -> None:
        job_id = self._job("job_bwrap_isolation")
        workspace = self.manager.allocate(job_id, 1)
        visible = workspace / "visible-sentinel"
        visible.write_text("public\n", encoding="utf-8")
        sealed = self.warehouse / "sealed" / "sealed-sentinel"
        sealed.parent.mkdir(parents=True)
        sealed.write_text("secret\n", encoding="utf-8")

        visible_command = self.manager.bwrap_command(
            ["/usr/bin/test", "-e", "/workspace/visible-sentinel"],
            workspace,
            network=False,
        )
        visible_result = subprocess.run(
            visible_command,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=20,
            check=False,
        )
        self.assertEqual(0, visible_result.returncode, visible_result.stderr.decode(errors="replace"))

        hidden_command = self.manager.bwrap_command(
            ["/usr/bin/test", "!", "-e", str(sealed)],
            workspace,
            network=False,
        )
        hidden_result = subprocess.run(
            hidden_command,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=20,
            check=False,
        )
        self.assertEqual(0, hidden_result.returncode, hidden_result.stderr.decode(errors="replace"))


if __name__ == "__main__":
    unittest.main()
