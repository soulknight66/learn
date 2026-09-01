#!/usr/bin/env python3
"""Deterministic unit coverage for learner-view construction."""

import json
import contextlib
import io
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock

import learner_view
import validate_student_view


PACK_ROOT = Path(__file__).resolve().parents[2]


def make_writable(path):
    if not os.path.lexists(str(path)):
        return
    for directory, directories, unused_filenames in os.walk(str(path), topdown=False):
        base = Path(directory)
        for name in directories:
            (base / name).chmod(0o700)
        base.chmod(0o700)


class LearnerViewTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.mkdtemp(prefix="pebble-view-test-")
        self.root = Path(self.temporary)
        self.source = self.root / "source"
        self.source.mkdir()
        for relative, kind, unused_access in learner_view.EXPECTED_ALLOWED:
            path = self.source / relative
            if kind == "directory":
                path.mkdir(parents=True)
                (path / "fixture.txt").write_text(relative, encoding="utf-8")
            else:
                path.write_text(relative, encoding="utf-8")
        policy = json.loads((PACK_ROOT / learner_view.POLICY_PATH).read_text(encoding="utf-8"))
        (self.source / learner_view.POLICY_PATH).write_text(
            json.dumps(policy, sort_keys=True, indent=2) + "\n", encoding="utf-8"
        )
        (self.source / "sealed").mkdir()
        (self.source / "sealed" / "marker.txt").write_text("not learner visible", encoding="utf-8")

    def tearDown(self):
        make_writable(self.root)
        shutil.rmtree(self.temporary)

    def test_materialize_copies_only_allowlist(self):
        destination = self.root / "view"
        result = learner_view.materialize(self.source, destination)
        self.assertEqual(result["content_sha256"], learner_view.verify_view(destination))
        self.assertFalse((destination / "sealed").exists())
        self.assertEqual(
            {path.name for path in destination.iterdir()},
            {entry[0] for entry in learner_view.EXPECTED_ALLOWED},
        )

    def test_existing_destination_is_never_overwritten(self):
        destination = self.root / "view"
        destination.mkdir()
        marker = destination / "marker.txt"
        marker.write_text("preserve", encoding="utf-8")
        with self.assertRaises(learner_view.ViewError):
            learner_view.materialize(self.source, destination)
        self.assertEqual(marker.read_text(encoding="utf-8"), "preserve")

    def test_destination_inside_source_is_rejected(self):
        destination = self.source / "view"
        with self.assertRaises(learner_view.ViewError):
            learner_view.materialize(self.source, destination)
        self.assertFalse(destination.exists())

    def test_special_source_entry_is_rejected(self):
        target = self.source / "starter" / "fixture.txt"
        target.unlink()
        target.symlink_to(self.source / "README.md")
        destination = self.root / "view"
        with self.assertRaises(learner_view.ViewError):
            learner_view.materialize(self.source, destination)
        self.assertFalse(destination.exists())

    def test_isolation_command_mounts_only_allowlisted_entries(self):
        destination = self.root / "isolated-view"
        observed = {}

        def fake_run(command, timeout):
            observed["command"] = command
            observed["timeout"] = timeout
            return 0, "PASS mocked learner subprocess\n"

        output = io.StringIO()
        with mock.patch.object(validate_student_view, "run_bounded", side_effect=fake_run):
            with contextlib.redirect_stdout(output):
                status = validate_student_view.main([
                    "--source", str(self.source),
                    "--destination", str(destination),
                    "--bwrap", sys.executable,
                ])
        self.assertEqual(status, 0)
        command = observed["command"]
        self.assertEqual(observed["timeout"], 30)
        self.assertIn(
            ["--bind", str(destination / "starter"), "/workspace/starter"],
            [command[index:index + 3] for index in range(len(command) - 2)],
        )
        for relative, unused_kind, access in learner_view.EXPECTED_ALLOWED:
            if access == "read-only":
                self.assertIn(
                    ["--ro-bind", str(destination / relative), "/workspace/" + relative],
                    [command[index:index + 3] for index in range(len(command) - 2)],
                )
        self.assertIn("PASS learner view content digest", output.getvalue())


if __name__ == "__main__":
    unittest.main()
