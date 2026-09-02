"""Deterministic regression tests for evaluator process cleanup."""

from __future__ import annotations

from pathlib import Path
import sys
import time
import unittest


REPOSITORY = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY))

from environment.process_runner import build_directory, run_process


class ProcessRunnerTest(unittest.TestCase):
    def test_read_only_repository_uses_attempt_parent(self) -> None:
        with build_directory(
            REPOSITORY, "minilog-fallback-test-", requested_root=None
        ) as temporary:
            immutable_repository = temporary / "immutable-repository"
            immutable_repository.mkdir()
            immutable_repository.chmod(0o500)
            try:
                with build_directory(
                    immutable_repository, "fallback-", requested_root=None
                ) as scratch:
                    self.assertEqual(
                        temporary / ".minilog-runner-tmp",
                        scratch.parent,
                    )
            finally:
                immutable_repository.chmod(0o700)

    def test_timeout_kills_descendant_process(self) -> None:
        with build_directory(
            REPOSITORY, "minilog-process-test-", requested_root=None
        ) as temporary:
            spawned_marker = temporary / "spawned"
            descendant_ready_marker = temporary / "descendant-ready"
            orphan_marker = temporary / "orphan"
            descendant = (
                "import pathlib,signal,sys,time; "
                "signal.signal(signal.SIGTERM, signal.SIG_IGN); "
                "pathlib.Path(sys.argv[2]).write_text('ready', encoding='utf-8'); "
                "time.sleep(1.5); "
                "pathlib.Path(sys.argv[1]).write_text('orphan', encoding='utf-8')"
            )
            parent = (
                "import pathlib,subprocess,sys,time; "
                "subprocess.Popen([sys.executable, '-c', sys.argv[1], "
                "sys.argv[2], sys.argv[3]]); "
                "pathlib.Path(sys.argv[4]).write_text('spawned', encoding='utf-8'); "
                "time.sleep(10)"
            )
            result = run_process(
                [
                    sys.executable,
                    "-c",
                    parent,
                    descendant,
                    str(orphan_marker),
                    str(descendant_ready_marker),
                    str(spawned_marker),
                ],
                REPOSITORY,
                timeout_seconds=0.75,
                termination_grace_seconds=0.25,
            )
            self.assertEqual(124, result)
            self.assertTrue(spawned_marker.is_file(), "parent did not launch its descendant")
            self.assertTrue(
                descendant_ready_marker.is_file(),
                "descendant did not install its SIGTERM handler",
            )
            time.sleep(1.5)
            self.assertFalse(orphan_marker.exists(), "timed-out descendant survived")


if __name__ == "__main__":
    unittest.main()
