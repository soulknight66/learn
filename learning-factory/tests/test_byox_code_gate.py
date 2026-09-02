from __future__ import annotations

import copy
import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import learnfactory.handlers as handlers_module
import learnfactory.validation as validation_module
from learnfactory.byox_jobs import byox_runtime_safety_validators
from learnfactory.db import Database
from learnfactory.handlers import (
    HandlerFailure,
    _cutover_byox_validation_workspace,
    _with_byox_runtime_safety_validators,
)
from learnfactory.jobs import ClaimedJob, JobRepository
from learnfactory.util import tree_sha256
from learnfactory.validation import Validator
from learnfactory.worker import (
    _enforce_validator_execution_policy,
    _validated_byox_cutover_contract,
)


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
        self.assertEqual(2, result.evidence["policy_version"])
        self.assertEqual(1, result.evidence["manifest_version"])
        self.assertRegex(result.evidence["manifest_digest"], r"^[0-9a-f]{64}$")
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

    def test_absolute_workspace_ancestor_symlink_is_rejected(self) -> None:
        actual_parent = self.root / "actual-parent"
        actual_parent.mkdir()
        workspace = actual_parent / "workspace"
        workspace.mkdir()
        self._code_tree(workspace)
        alias = self.root / "workspace-parent-alias"
        alias.symlink_to(actual_parent, target_is_directory=True)

        result = self._run(alias / "workspace", [self._gate()])[0]

        self.assertEqual("FAIL", result.status)
        self.assertTrue(
            all(
                group["missing_or_unsafe_roots"]
                for group in result.evidence["groups"]
            )
        )
        self.assertIn(
            "unsafe-workspace:symlink-component",
            {item["reason"] for item in result.evidence["unsafe_entries"]},
        )

    def test_fresh_inode_cutover_defeats_cross_root_late_writes(self) -> None:
        workspace = self.root / "cross-root-cutover"
        workspace.mkdir()
        self._code_tree(workspace)
        (workspace / "environment").mkdir()
        public_test = workspace / "public_tests/run-tests.bats"
        original_test = public_test.read_bytes()
        external = self.root / "external-test.bats"
        external.write_text("#!/usr/bin/env bats\n@test 'outside' { false; }\n")
        copy_entry = handlers_module._copy_byox_repair_authoritative_entry
        injected = False

        def mutate_retired_source(*args: object, **kwargs: object) -> None:
            nonlocal injected
            if kwargs.get("depth") == 1 and args[2] == "starter" and not injected:
                public_test.unlink()
                os.link(external, public_test)
                (workspace / "environment/solutions.txt").write_text(
                    "late forbidden answer\n", encoding="utf-8"
                )
                injected = True
            copy_entry(*args, **kwargs)

        with patch.object(
            handlers_module,
            "_copy_byox_repair_authoritative_entry",
            side_effect=mutate_retired_source,
        ):
            cutover = _cutover_byox_validation_workspace(workspace)

        self.assertTrue(injected)
        self.assertEqual(original_test, public_test.read_bytes())
        self.assertEqual(1, public_test.stat().st_nlink)
        self.assertFalse((workspace / "environment/solutions.txt").exists())
        self.assertEqual(
            cutover["validation_snapshot_checksum"], tree_sha256(workspace)
        )
        results = self._run(
            workspace,
            [self._gate(), byox_runtime_safety_validators()[1]],
        )
        self.assertTrue(all(result.passed for result in results))

    def test_retained_source_descriptor_cannot_mutate_cutover_tree(self) -> None:
        workspace = self.root / "retained-source-fd"
        workspace.mkdir()
        self._code_tree(workspace)
        target = workspace / "starter/Main.hs"
        original = target.read_bytes()
        source_descriptor = os.open(target, os.O_RDWR)
        source_identity = os.fstat(source_descriptor)
        try:
            cutover = _cutover_byox_validation_workspace(workspace)
            replacement_identity = target.stat()
            self.assertNotEqual(
                (source_identity.st_dev, source_identity.st_ino),
                (replacement_identity.st_dev, replacement_identity.st_ino),
            )
            os.lseek(source_descriptor, 0, os.SEEK_SET)
            os.write(source_descriptor, b"X" * len(original))
            os.fsync(source_descriptor)
            self.assertEqual(original, target.read_bytes())
            self.assertEqual(0, os.fstat(source_descriptor).st_nlink)
            self.assertEqual(
                cutover["validation_snapshot_checksum"], tree_sha256(workspace)
            )
        finally:
            os.close(source_descriptor)

    def test_cutover_allows_benign_parent_directory_metadata_change(self) -> None:
        parent = self.root / "changing-parent-metadata"
        workspace = parent / "workspace"
        workspace.mkdir(parents=True)
        self._code_tree(workspace)
        parent_identity = parent.stat()
        real_open = handlers_module.os.open
        changed = False

        def change_parent_metadata(
            path: object, flags: int, *args: object, **kwargs: object
        ) -> int:
            nonlocal changed
            if (
                not changed
                and path == parent.name
                and kwargs.get("dir_fd") is not None
            ):
                (parent / "concurrent-sibling").mkdir()
                changed = True
            return real_open(path, flags, *args, **kwargs)  # type: ignore[arg-type]

        with patch.object(
            handlers_module.os, "open", side_effect=change_parent_metadata
        ):
            cutover = _cutover_byox_validation_workspace(workspace)

        self.assertTrue(changed)
        current_parent_identity = parent.stat()
        self.assertEqual(
            (parent_identity.st_dev, parent_identity.st_ino),
            (current_parent_identity.st_dev, current_parent_identity.st_ino),
        )
        self.assertEqual(
            cutover["validation_snapshot_checksum"], tree_sha256(workspace)
        )

    def test_cutover_rejects_replaced_parent_directory_component(self) -> None:
        parent = self.root / "replaced-parent"
        workspace = parent / "workspace"
        workspace.mkdir(parents=True)
        self._code_tree(workspace)
        displaced = self.root / "displaced-parent"
        real_open = handlers_module.os.open
        swapped = False

        def replace_parent(
            path: object, flags: int, *args: object, **kwargs: object
        ) -> int:
            nonlocal swapped
            if (
                not swapped
                and path == parent.name
                and kwargs.get("dir_fd") is not None
            ):
                parent.rename(displaced)
                parent.mkdir()
                swapped = True
            return real_open(path, flags, *args, **kwargs)  # type: ignore[arg-type]

        with patch.object(handlers_module.os, "open", side_effect=replace_parent):
            with self.assertRaisesRegex(
                HandlerFailure, "workspace parent cannot be safely opened"
            ):
                _cutover_byox_validation_workspace(workspace)

        self.assertTrue(swapped)

    def test_structural_byox_cutover_rejects_all_executable_validator_forms(self) -> None:
        workspace = self.root / "executable-validator-contract"
        workspace.mkdir()
        self._code_tree(workspace)
        cutover = _cutover_byox_validation_workspace(workspace)
        gate = self._gate()
        for executable in (
            {"type": "command", "name": "direct-command", "argv": ["true"]},
            {
                "type": "review_acceptance",
                "name": "nested-command",
                "mode": "command",
                "argv": ["true"],
            },
        ):
            with self.subTest(executable=executable["name"]):
                with self.assertRaisesRegex(
                    HandlerFailure, "cannot be mixed with executable validators"
                ):
                    _validated_byox_cutover_contract(
                        [gate, executable],
                        None,
                        {"byox_validation_cutover": cutover},
                    )

    def test_worker_execution_policy_rejects_malformed_handler_envelopes(self) -> None:
        malformed = (
            None,
            {},
            {"type": None},
            {"type": "review_acceptance", "mode": {"command": True}},
            {"type": "review_acceptance", "mode": "unknown"},
        )
        for specification in malformed:
            with self.subTest(specification=specification):
                with self.assertRaises(HandlerFailure) as captured:
                    _enforce_validator_execution_policy(
                        [specification], allow_host_commands=False
                    )
                self.assertEqual(
                    "blocked_validator_execution_policy",
                    captured.exception.kind,
                )

    def test_capture_revalidates_the_absolute_workspace_binding(self) -> None:
        workspace = self.root / "final-workspace-coherence"
        workspace.mkdir()
        self._code_tree(workspace)
        displaced = self.root / "final-workspace-before-swap"
        outside = self.root / "final-workspace-outside"
        outside.mkdir()
        self._code_tree(outside)
        original_capture = validation_module._capture_byox_regular_file_at
        readmes_seen = 0
        swapped = False

        def replace_workspace_after_last_root(*args: object, **kwargs: object) -> str:
            nonlocal readmes_seen, swapped
            digest = original_capture(*args, **kwargs)
            if args[1] == "README.md":
                readmes_seen += 1
                if readmes_seen == 4:
                    workspace.rename(displaced)
                    workspace.symlink_to(outside, target_is_directory=True)
                    swapped = True
            return digest

        with patch.object(
            validation_module,
            "_capture_byox_regular_file_at",
            side_effect=replace_workspace_after_last_root,
        ):
            result = self._run(workspace, [self._gate()])[0]

        self.assertTrue(swapped)
        self.assertEqual("FAIL", result.status)
        self.assertTrue(
            any(
                "workspace-binding" in item["reason"]
                for item in result.evidence["unsafe_entries"]
            )
        )

    def test_external_hardlinks_fail_both_runtime_structural_gates(self) -> None:
        workspace = self.root / "external-hardlink"
        workspace.mkdir()
        self._code_tree(workspace)
        external = self.root / "external-source.py"
        external.write_text("def external(): return True\n", encoding="utf-8")
        linked = workspace / "starter/external.py"
        os.link(external, linked)

        code_result = self._run(workspace, [self._gate()])[0]
        boundary_result = self._run(
            workspace, [byox_runtime_safety_validators()[1]]
        )[0]

        self.assertEqual("FAIL", code_result.status)
        self.assertIn(
            ("starter/external.py", "hardlink"),
            {
                (item["path"], item["reason"])
                for item in code_result.evidence["unsafe_entries"]
            },
        )
        self.assertEqual("FAIL", boundary_result.status)
        self.assertIn(
            ("starter/external.py", "hardlink"),
            {
                (item["path"], item["reason"])
                for item in boundary_result.evidence["unsafe_entries"]
            },
        )

    def test_runtime_depth_bound_accepts_exact_limit_and_rejects_next_level(self) -> None:
        def add_chain(workspace: Path, depth: int) -> None:
            current = workspace / "starter"
            for _ in range(depth):
                current = current / "d"
                current.mkdir()
            (current / "leaf.txt").write_text("leaf\n", encoding="utf-8")

        exact = self.root / "depth-exact"
        exact.mkdir()
        self._code_tree(exact)
        (exact / "environment").mkdir()
        add_chain(exact, validation_module.BYOX_TREE_MAX_DEPTH)

        over = self.root / "depth-over"
        over.mkdir()
        self._code_tree(over)
        (over / "environment").mkdir()
        add_chain(over, validation_module.BYOX_TREE_MAX_DEPTH + 1)

        exact_gate = self._run(exact, [self._gate()])[0]
        exact_boundary = self._run(
            exact, [byox_runtime_safety_validators()[1]]
        )[0]
        over_gate = self._run(over, [self._gate()])[0]
        over_boundary = self._run(
            over, [byox_runtime_safety_validators()[1]]
        )[0]

        self.assertEqual("PASS", exact_gate.status)
        self.assertEqual("PASS", exact_boundary.status)
        self.assertEqual("FAIL", over_gate.status)
        self.assertEqual("max_depth_exceeded", over_gate.evidence["limit_failure"])
        self.assertEqual("FAIL", over_boundary.status)
        self.assertEqual(
            "max_depth_exceeded", over_boundary.evidence["limit_failure"]
        )

        exact_cutover = _cutover_byox_validation_workspace(exact)
        self.assertEqual(
            tree_sha256(exact), exact_cutover["validation_snapshot_checksum"]
        )
        with self.assertRaisesRegex(HandlerFailure, "maximum depth"):
            _cutover_byox_validation_workspace(over)

    def test_runtime_directory_fd_closes_when_initial_fstat_raises(self) -> None:
        workspace = self.root / "fstat-failure"
        workspace.mkdir()
        self._code_tree(workspace)
        original_open_relative = validation_module._open_relative_directory
        original_fstat = validation_module.os.fstat
        returned_descriptors: list[int] = []
        fail_descriptors: set[int] = set()

        def mark_returned(*args: object, **kwargs: object) -> int:
            descriptor = original_open_relative(*args, **kwargs)
            if kwargs.get("expected") is not None and not fail_descriptors:
                returned_descriptors.append(descriptor)
                fail_descriptors.add(descriptor)
            return descriptor

        def fail_initial_fstat(descriptor: int):
            if descriptor in fail_descriptors:
                fail_descriptors.remove(descriptor)
                raise OSError("injected initial fstat failure")
            return original_fstat(descriptor)

        try:
            with (
                patch.object(
                    validation_module,
                    "_open_relative_directory",
                    side_effect=mark_returned,
                ),
                patch.object(
                    validation_module.os,
                    "fstat",
                    side_effect=fail_initial_fstat,
                ),
            ):
                with self.assertRaisesRegex(OSError, "injected initial fstat"):
                    validation_module.capture_byox_code_manifest(workspace)
            self.assertTrue(returned_descriptors)
            for descriptor in returned_descriptors:
                with self.assertRaises(OSError):
                    os.fstat(descriptor)
        finally:
            for descriptor in returned_descriptors:
                try:
                    os.close(descriptor)
                except OSError:
                    pass

    def test_nested_directory_swap_cannot_import_outside_code(self) -> None:
        workspace = self.root / "nested-directory-swap"
        workspace.mkdir()
        self._roots(workspace, include_sealed_tests=False)
        (workspace / "sealed/reference/engine.py").write_text(
            "def answer(): return 42\n", encoding="utf-8"
        )
        (workspace / "public_tests/test_engine.py").write_text(
            "def test_answer(): assert True\n", encoding="utf-8"
        )
        nested = workspace / "starter/pkg"
        nested.mkdir()
        displaced = workspace / "starter/pkg-before-swap"
        outside = self.root / "outside-code"
        outside.mkdir()
        outside_content = b"def imported_from_outside(): return True\n"
        (outside / "external.py").write_bytes(outside_content)

        real_open = validation_module.os.open
        real_scandir = validation_module.os.scandir
        swapped = False

        def perform_swap() -> None:
            nonlocal swapped
            if swapped:
                return
            nested.rename(displaced)
            nested.symlink_to(outside, target_is_directory=True)
            swapped = True

        def race_directory_open(
            path: object, flags: int, *args: object, **kwargs: object
        ) -> int:
            if path == "pkg" and kwargs.get("dir_fd") is not None:
                perform_swap()
            return real_open(path, flags, *args, **kwargs)  # type: ignore[arg-type]

        def race_path_reopen(path: object):
            if isinstance(path, (str, os.PathLike)) and Path(path) == nested:
                perform_swap()
            return real_scandir(path)  # type: ignore[arg-type]

        with (
            patch.object(
                validation_module.os, "open", side_effect=race_directory_open
            ),
            patch.object(
                validation_module.os, "scandir", side_effect=race_path_reopen
            ),
        ):
            result = self._run(workspace, [self._gate()])[0]

        self.assertTrue(swapped)
        self.assertEqual("FAIL", result.status)
        self.assertIn("learner_starter", result.evidence["missing_groups"])
        self.assertNotIn(
            hashlib.sha256(outside_content).hexdigest(),
            json.dumps(result.evidence, sort_keys=True),
        )

    def test_recursive_boundary_fails_closed_on_nested_directory_swap(self) -> None:
        workspace = self.root / "nested-boundary-swap"
        workspace.mkdir()
        for root in ("starter", "public_tests", "environment"):
            (workspace / root).mkdir()
        nested = workspace / "starter/pkg"
        nested.mkdir()
        displaced = workspace / "starter/pkg-before-swap"
        outside = self.root / "outside-boundary"
        outside.mkdir()
        (outside / "ordinary.txt").write_text("outside\n", encoding="utf-8")

        real_open = validation_module.os.open
        real_scandir = validation_module.os.scandir
        swapped = False

        def perform_swap() -> None:
            nonlocal swapped
            if swapped:
                return
            nested.rename(displaced)
            nested.symlink_to(outside, target_is_directory=True)
            swapped = True

        def race_directory_open(
            path: object, flags: int, *args: object, **kwargs: object
        ) -> int:
            if path == "pkg" and kwargs.get("dir_fd") is not None:
                perform_swap()
            return real_open(path, flags, *args, **kwargs)  # type: ignore[arg-type]

        def race_path_reopen(path: object):
            if isinstance(path, (str, os.PathLike)) and Path(path) == nested:
                perform_swap()
            return real_scandir(path)  # type: ignore[arg-type]

        with (
            patch.object(
                validation_module.os, "open", side_effect=race_directory_open
            ),
            patch.object(
                validation_module.os, "scandir", side_effect=race_path_reopen
            ),
        ):
            result = self._run(
                workspace,
                [byox_runtime_safety_validators()[1]],
            )[0]

        self.assertTrue(swapped)
        self.assertEqual("FAIL", result.status)
        self.assertIn(
            "starter/pkg",
            {item["path"] for item in result.evidence["unsafe_entries"]},
        )

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
