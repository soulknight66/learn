from __future__ import annotations

import copy
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from learnfactory.byox_jobs import byox_runtime_safety_validators
from learnfactory.db import Database
from learnfactory.handlers import HandlerFailure, _with_byox_runtime_safety_validators
from learnfactory.jobs import ClaimedJob, JobRepository
from learnfactory.validation import Validator


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = REPOSITORY_ROOT / "migrations"
GATE_NAME = "byox-authoritative-code-bearing-tree"


class ByoxCodePresenceGateTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="learnfactory-byox-code-gate-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.database = Database(self.root / "factory.db", MIGRATIONS)
        self.database.migrate()
        self.jobs = JobRepository(self.database)
        self.counter = 0

    def _gate(self, **overrides: int) -> dict[str, object]:
        gate = next(
            dict(item)
            for item in byox_runtime_safety_validators()
            if item["name"] == GATE_NAME
        )
        gate.update(overrides)
        return gate

    def _run(
        self,
        workspace: Path,
        validators: list[dict[str, object]],
        *,
        payload: dict[str, object] | None = None,
    ):
        self.counter += 1
        job_id = f"job_byox_code_gate_{self.counter}"
        self.jobs.create(
            "codex_task",
            "reference_builder",
            payload
            or {
                "artifact_type": "byox-challenge-pack",
                "seed_policy": {"kind": "byox_reference_build", "version": 1},
            },
            job_id=job_id,
        )
        return Validator(self.database).run(
            job_id,
            workspace,
            validators,
            self.root / "logs" / job_id,
        )

    @staticmethod
    def _roots(workspace: Path, *, include_sealed_tests: bool = True) -> None:
        roots = ["sealed/reference", "starter", "public_tests"]
        if include_sealed_tests:
            roots.append("sealed/reference_tests")
        for relative in roots:
            path = workspace / relative
            path.mkdir(parents=True, exist_ok=True)
            (path / "README.md").write_text("documentation only\n", encoding="utf-8")

    @staticmethod
    def _code_tree(workspace: Path, *, include_sealed_tests: bool = True) -> None:
        ByoxCodePresenceGateTests._roots(
            workspace, include_sealed_tests=include_sealed_tests
        )
        (workspace / "sealed/reference/engine.zig").write_text(
            "pub fn answer() u8 { return 42; }\n", encoding="utf-8"
        )
        (workspace / "sealed/reference/Makefile").write_text(
            "all:\n\t@echo build\n", encoding="utf-8"
        )
        (workspace / "starter/Main.hs").write_text(
            "main = error \"implement me\"\n", encoding="utf-8"
        )
        (workspace / "public_tests/run-tests.bats").write_text(
            "#!/usr/bin/env bats\n@test 'contract' { true; }\n", encoding="utf-8"
        )

    def test_markdown_only_pack_fails_all_code_roles(self) -> None:
        workspace = self.root / "markdown-only"
        workspace.mkdir()
        self._roots(workspace)

        result = self._run(workspace, [self._gate()])[0]

        self.assertEqual("FAIL", result.status)
        self.assertEqual(
            ["reference_implementation", "learner_starter", "tests"],
            result.evidence["missing_groups"],
        )
        self.assertFalse(result.evidence["claims_builds_or_tested"])
        self.assertEqual(0, sum(group["qualifying_count"] for group in result.evidence["groups"]))

    def test_code_and_test_sources_pass_with_hashed_content_free_evidence(self) -> None:
        workspace = self.root / "code-tree"
        workspace.mkdir()
        self._code_tree(workspace, include_sealed_tests=False)

        result = self._run(workspace, [self._gate()])[0]

        self.assertEqual("PASS", result.status)
        self.assertEqual([], result.evidence["missing_groups"])
        self.assertEqual(1, result.evidence["policy_version"])
        self.assertRegex(result.evidence["policy_digest"], r"^[0-9a-f]{64}$")
        self.assertEqual(("PARTIAL",), result.claims)
        evidence_text = json.dumps(result.evidence, sort_keys=True)
        self.assertNotIn("return 42", evidence_text)
        self.assertNotIn("implement me", evidence_text)
        self.assertNotIn("@test", evidence_text)
        by_name = {group["name"]: group for group in result.evidence["groups"]}
        self.assertEqual(1, by_name["reference_implementation"]["qualifying_count"])
        self.assertEqual(1, by_name["reference_implementation"]["build_descriptor_count"])
        self.assertRegex(
            by_name["reference_implementation"]["qualifying_files"][0]["sha256"],
            r"^[0-9a-f]{64}$",
        )
        self.assertEqual(1, by_name["learner_starter"]["qualifying_count"])
        self.assertEqual(1, by_name["tests"]["qualifying_count"])
        self.assertFalse({"BUILDS", "TESTED"} & set(result.claims))

    def test_wrong_roots_and_prose_extensions_do_not_qualify(self) -> None:
        workspace = self.root / "wrong-locations"
        workspace.mkdir()
        self._roots(workspace)
        misplaced = workspace / "reference"
        misplaced.mkdir()
        (misplaced / "main.py").write_text("print('wrong root')\n", encoding="utf-8")
        (workspace / "sealed/reference/design.md").write_text("not code\n", encoding="utf-8")
        (workspace / "sealed/reference/setup.py").write_text(
            "# build metadata only\n", encoding="utf-8"
        )
        (workspace / "sealed/reference/checks.bats").write_text(
            "@test 'not an implementation' { true; }\n", encoding="utf-8"
        )
        (workspace / "starter/starter.txt").write_text("not code\n", encoding="utf-8")
        (workspace / "starter/build.gradle.kts").write_text(
            "// build metadata only\n", encoding="utf-8"
        )
        (workspace / "starter/contract.feature").write_text(
            "Feature: still not starter implementation code\n", encoding="utf-8"
        )
        (workspace / "public_tests/cases.json").write_text("{}\n", encoding="utf-8")
        (workspace / "public_tests/package.json").write_text("{}\n", encoding="utf-8")

        result = self._run(workspace, [self._gate()])[0]

        self.assertEqual("FAIL", result.status)
        self.assertEqual(
            ["reference_implementation", "learner_starter", "tests"],
            result.evidence["missing_groups"],
        )
        self.assertEqual(
            [1, 1, 1],
            [group["build_descriptor_count"] for group in result.evidence["groups"]],
        )

    def test_empty_sources_and_build_descriptors_cannot_satisfy_gate(self) -> None:
        workspace = self.root / "empty-code"
        workspace.mkdir()
        self._roots(workspace)
        for relative in (
            "sealed/reference/main.rs",
            "starter/main.py",
            "public_tests/test_contract.go",
        ):
            (workspace / relative).write_bytes(b"")
        for relative in (
            "sealed/reference/Cargo.toml",
            "starter/setup.py",
            "public_tests/package.json",
        ):
            (workspace / relative).write_text("build metadata\n", encoding="utf-8")

        result = self._run(workspace, [self._gate()])[0]

        self.assertEqual("FAIL", result.status)
        self.assertEqual(
            ["reference_implementation", "learner_starter", "tests"],
            result.evidence["missing_groups"],
        )
        self.assertEqual(
            [1, 1, 1],
            [group["build_descriptor_count"] for group in result.evidence["groups"]],
        )

    def test_symlinked_root_ancestor_and_special_file_fail_closed(self) -> None:
        workspace = self.root / "unsafe-tree"
        workspace.mkdir()
        (workspace / "actual-sealed/reference").mkdir(parents=True)
        (workspace / "actual-sealed/reference/main.py").write_text(
            "answer = 42\n", encoding="utf-8"
        )
        (workspace / "sealed").symlink_to("actual-sealed", target_is_directory=True)
        for relative, content in (
            ("starter/main.py", "raise NotImplementedError\n"),
            ("public_tests/test_contract.py", "def test_contract(): assert True\n"),
        ):
            path = workspace / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        os.mkfifo(workspace / "public_tests/result.pipe")

        result = self._run(workspace, [self._gate()])[0]

        self.assertEqual("FAIL", result.status)
        self.assertIn("reference_implementation", result.evidence["missing_groups"])
        unsafe = {
            (item["path"], item["reason"])
            for item in result.evidence["unsafe_entries"]
        }
        self.assertIn(
            ("sealed/reference", "unsafe-root:symlink-component"), unsafe
        )
        self.assertIn(("public_tests/result.pipe", "special-file"), unsafe)

    def test_entry_and_byte_bounds_fail_closed(self) -> None:
        entries_workspace = self.root / "too-many-entries"
        entries_workspace.mkdir()
        self._code_tree(entries_workspace)
        entry_result = self._run(
            entries_workspace, [self._gate(max_entries=2)]
        )[0]
        self.assertEqual("FAIL", entry_result.status)
        self.assertEqual("max_entries_exceeded", entry_result.evidence["limit_failure"])

        bytes_workspace = self.root / "oversized-source"
        bytes_workspace.mkdir()
        self._code_tree(bytes_workspace)
        byte_result = self._run(
            bytes_workspace, [self._gate(max_file_bytes=4)]
        )[0]
        self.assertEqual("FAIL", byte_result.status)
        self.assertGreater(len(byte_result.evidence["oversized_files"]), 0)

    def test_read_only_gate_reaches_its_bound_without_whole_tree_manifest(self) -> None:
        workspace = self.root / "bounded-read-only"
        workspace.mkdir()
        self._roots(workspace)
        for index in range(100):
            (workspace / "sealed/reference" / f"prose-{index:03d}.txt").write_text(
                "not source code\n", encoding="utf-8"
            )

        with patch(
            "learnfactory.validation._tree_manifest",
            side_effect=AssertionError("read-only validator must not hash whole tree"),
        ):
            result = self._run(workspace, [self._gate(max_entries=20)])[0]

        self.assertEqual("FAIL", result.status)
        self.assertEqual("max_entries_exceeded", result.evidence["limit_failure"])
        self.assertEqual(21, result.evidence["counts"]["entries"])

    def test_recursive_boundary_is_bounded_and_rejects_special_files(self) -> None:
        workspace = self.root / "bounded-boundary"
        workspace.mkdir()
        for root in ("starter", "public_tests", "environment"):
            (workspace / root).mkdir()
        for index in range(10):
            (workspace / "starter" / f"file-{index:02d}.txt").write_text(
                "ordinary\n", encoding="utf-8"
            )
        boundary = byox_runtime_safety_validators()[1]
        boundary["max_entries"] = 3

        with patch(
            "learnfactory.validation._tree_manifest",
            side_effect=AssertionError("read-only validator must not hash whole tree"),
        ):
            result = self._run(workspace, [boundary])[0]

        self.assertEqual("FAIL", result.status)
        self.assertEqual("max_entries_exceeded", result.evidence["limit_failure"])
        self.assertEqual(4, result.evidence["entry_count"])

    def test_executable_validator_still_detects_undeclared_mutation(self) -> None:
        workspace = self.root / "command-mutation"
        workspace.mkdir()
        result = self._run(
            workspace,
            [
                {
                    "type": "command",
                    "name": "mutating-command",
                    "argv": [
                        sys.executable,
                        "-c",
                        "from pathlib import Path; Path('rogue.txt').write_text('x')",
                    ],
                    "timeout_seconds": 5,
                }
            ],
        )[0]

        self.assertEqual("FAIL", result.status)
        self.assertEqual(["rogue.txt"], result.evidence["changed_paths"])

    def test_unrelated_job_runs_only_its_declared_validator(self) -> None:
        workspace = self.root / "unrelated"
        workspace.mkdir()
        (workspace / "README.md").write_text("prose is valid here\n", encoding="utf-8")

        results = self._run(
            workspace,
            [{"type": "required_paths", "name": "unrelated-output", "paths": ["README.md"]}],
            payload={"artifact_type": "ordinary-report"},
        )

        self.assertEqual(1, len(results))
        self.assertTrue(results[0].passed)
        self.assertEqual("unrelated-output", results[0].name)

    @staticmethod
    def _claimed_job(artifact_type: str) -> ClaimedJob:
        return ClaimedJob(
            job_id="job_byox_runtime_floor_test",
            type="codex_task",
            worker_type="reference_builder",
            payload={
                "artifact_type": artifact_type,
                "seed_policy": {
                    "kind": (
                        "byox_reference_repair"
                        if artifact_type == "byox-remediated-challenge-pack"
                        else "byox_reference_build"
                    ),
                    "version": 1,
                },
            },
            attempt_count=1,
            workspace=None,
            model="gpt-5.6-sol",
            reasoning_effort="ultra",
            lease_token="lease-test",
        )

    def test_runtime_floor_augments_immutable_v1_and_repair_validators(self) -> None:
        runtime_floor = byox_runtime_safety_validators()
        declared = [
            {"type": "required_paths", "name": "legacy", "paths": ["README.md"]},
            *copy.deepcopy(runtime_floor[:2]),
        ]
        original = copy.deepcopy(declared)
        for artifact_type in (
            "byox-challenge-pack",
            "byox-remediated-challenge-pack",
        ):
            result = _with_byox_runtime_safety_validators(
                self._claimed_job(artifact_type), declared
            )
            self.assertEqual(original, declared)
            self.assertEqual(original, result[:-1])
            self.assertEqual(runtime_floor[-1], result[-1])

    def test_runtime_floor_rejects_reserved_name_collisions(self) -> None:
        canonical = byox_runtime_safety_validators()
        job = self._claimed_job("byox-challenge-pack")
        self.assertEqual(
            canonical,
            _with_byox_runtime_safety_validators(job, copy.deepcopy(canonical)),
        )
        divergent = copy.deepcopy(canonical)
        divergent[-1]["type"] = "required_paths"
        with self.assertRaisesRegex(HandlerFailure, "contract collision"):
            _with_byox_runtime_safety_validators(job, divergent)
        with self.assertRaisesRegex(HandlerFailure, "contract collision"):
            _with_byox_runtime_safety_validators(job, [*canonical, copy.deepcopy(canonical[-1])])


if __name__ == "__main__":
    unittest.main()
