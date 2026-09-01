from __future__ import annotations

import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from learnfactory.util import repository_revision


class RepositoryRevisionTests(unittest.TestCase):
    def test_revision_records_commit_and_ignores_untracked_corpus(self) -> None:
        calls: list[list[str]] = []

        def completed(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            calls.append(argv)
            if argv[-2:] == ["rev-parse", "HEAD"]:
                return subprocess.CompletedProcess(argv, 0, "a" * 40 + "\n", "")
            return subprocess.CompletedProcess(argv, 0, "", "")

        with patch("learnfactory.util.subprocess.run", side_effect=completed):
            result = repository_revision(Path("/factory"))
        self.assertEqual("a" * 40, result["commit"])
        self.assertTrue(result["tracked_worktree_clean"])
        self.assertEqual("RECORDED", result["status"])
        self.assertIn("--untracked-files=no", calls[1])

    def test_unversioned_repository_is_explicit(self) -> None:
        failure = subprocess.CompletedProcess(
            ["git", "rev-parse", "HEAD"], 128, "", "no commits"
        )
        with patch("learnfactory.util.subprocess.run", return_value=failure):
            result = repository_revision(Path("/factory"))
        self.assertIsNone(result["commit"])
        self.assertEqual("UNVERSIONED", result["status"])
        self.assertFalse(result["tracked_worktree_clean"])


if __name__ == "__main__":
    unittest.main()
