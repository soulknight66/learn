from __future__ import annotations

import os
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from learnfactory.util import FACTORY_EXECUTION_PATHS, repository_revision


class RepositoryRevisionTests(unittest.TestCase):
    def test_revision_records_commit_and_ignores_untracked_corpus(self) -> None:
        calls: list[list[str]] = []
        environments: list[dict[str, str]] = []

        def completed(
            argv: list[str], **kwargs: object
        ) -> subprocess.CompletedProcess[str]:
            calls.append(argv)
            environment = kwargs["env"]
            self.assertIsInstance(environment, dict)
            environments.append(environment)
            if argv[-2:] == ["rev-parse", "HEAD"]:
                return subprocess.CompletedProcess(argv, 0, "a" * 40 + "\n", "")
            return subprocess.CompletedProcess(argv, 0, "", "")

        with patch.dict(
            os.environ, {"GIT_OPTIONAL_LOCKS": "1"}, clear=False
        ), patch("learnfactory.util.subprocess.run", side_effect=completed):
            result = repository_revision(Path("/factory"))
            self.assertEqual("1", os.environ["GIT_OPTIONAL_LOCKS"])
        self.assertEqual("a" * 40, result["commit"])
        self.assertTrue(result["tracked_worktree_clean"])
        self.assertEqual("RECORDED", result["status"])
        prefix = [
            "git",
            "-c",
            "diff.autoRefreshIndex=false",
            "-C",
            "/factory",
        ]
        expected_scope = [
            "src",
            "migrations",
            "scripts",
            "prompts",
            "skills",
            "pyproject.toml",
        ]
        self.assertEqual(tuple(expected_scope), FACTORY_EXECUTION_PATHS)
        self.assertEqual([*prefix, "rev-parse", "HEAD"], calls[0])
        self.assertEqual(
            [
                *prefix,
                "diff",
                "--name-only",
                "HEAD",
                "--",
                *expected_scope,
            ],
            calls[1],
        )
        self.assertEqual(
            ["0", "0"],
            [item["GIT_OPTIONAL_LOCKS"] for item in environments],
        )

    def test_tracked_diff_marks_worktree_dirty(self) -> None:
        def completed(
            argv: list[str], **kwargs: object
        ) -> subprocess.CompletedProcess[str]:
            if argv[-2:] == ["rev-parse", "HEAD"]:
                return subprocess.CompletedProcess(argv, 0, "b" * 40 + "\n", "")
            return subprocess.CompletedProcess(argv, 0, "src/worker.py\n", "")

        with patch("learnfactory.util.subprocess.run", side_effect=completed):
            result = repository_revision(Path("/factory"))

        self.assertEqual("b" * 40, result["commit"])
        self.assertFalse(result["tracked_worktree_clean"])
        self.assertEqual("RECORDED", result["status"])

    def test_unversioned_repository_is_explicit(self) -> None:
        failure = subprocess.CompletedProcess(
            ["git", "rev-parse", "HEAD"], 128, "", "no commits"
        )
        with patch("learnfactory.util.subprocess.run", return_value=failure):
            result = repository_revision(Path("/factory"))
        self.assertIsNone(result["commit"])
        self.assertEqual("UNVERSIONED", result["status"])
        self.assertFalse(result["tracked_worktree_clean"])

    def test_diff_timeout_preserves_known_revision(self) -> None:
        calls: list[list[str]] = []

        def completed(
            argv: list[str], **kwargs: object
        ) -> subprocess.CompletedProcess[str]:
            calls.append(argv)
            if argv[-2:] == ["rev-parse", "HEAD"]:
                return subprocess.CompletedProcess(argv, 0, "c" * 40 + "\n", "")
            raise subprocess.TimeoutExpired(argv, timeout=5)

        with patch("learnfactory.util.subprocess.run", side_effect=completed):
            result = repository_revision(Path("/factory"))

        self.assertEqual("c" * 40, result["commit"])
        self.assertFalse(result["tracked_worktree_clean"])
        self.assertEqual("STATUS_UNAVAILABLE", result["status"])
        self.assertEqual(
            [
                "git",
                "-c",
                "diff.autoRefreshIndex=false",
                "-C",
                "/factory",
                "diff",
                "--name-only",
                "HEAD",
                "--",
                *FACTORY_EXECUTION_PATHS,
            ],
            calls[1],
        )

    def test_diff_failure_preserves_known_revision(self) -> None:
        def completed(
            argv: list[str], **kwargs: object
        ) -> subprocess.CompletedProcess[str]:
            if argv[-2:] == ["rev-parse", "HEAD"]:
                return subprocess.CompletedProcess(argv, 0, "d" * 40 + "\n", "")
            return subprocess.CompletedProcess(argv, 128, "", "diff unavailable")

        with patch("learnfactory.util.subprocess.run", side_effect=completed):
            result = repository_revision(Path("/factory"))

        self.assertEqual("d" * 40, result["commit"])
        self.assertFalse(result["tracked_worktree_clean"])
        self.assertEqual("STATUS_UNAVAILABLE", result["status"])
        self.assertEqual("diff unavailable", result["error"])


if __name__ == "__main__":
    unittest.main()
