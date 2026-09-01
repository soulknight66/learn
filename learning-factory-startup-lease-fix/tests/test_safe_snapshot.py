from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import learnfactory.safe_snapshot as safe_snapshot
from learnfactory.handlers import _copy_dependency_tree
from learnfactory.safe_snapshot import (
    CSDIY_EXAMINER_SNAPSHOT_LIMITS,
    SnapshotLimits,
)
from learnfactory.workspace import WorkspaceError


class SafeDependencySnapshotTests(unittest.TestCase):
    def test_entry_limit_stops_before_retaining_or_copying_4097th(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snapshot-entry-bound-") as raw:
            root = Path(raw)
            source = root / "source"
            source.mkdir()
            limits = CSDIY_EXAMINER_SNAPSHOT_LIMITS
            for index in range(limits.max_entries + 1):
                (source / f"entry-{index:04d}.txt").touch()

            admitted: list[str] = []
            original_name_check = safe_snapshot._safe_name

            def observe_name(name: str) -> None:
                original_name_check(name)
                admitted.append(name)

            destination = root / "snapshot"
            with mock.patch.object(
                safe_snapshot, "_safe_name", side_effect=observe_name
            ), mock.patch.object(
                safe_snapshot,
                "_copy_regular_file",
                wraps=safe_snapshot._copy_regular_file,
            ) as copied, self.assertRaisesRegex(WorkspaceError, "maximum entries"):
                _copy_dependency_tree(source, destination, limits=limits)

            self.assertEqual(limits.max_entries, len(admitted))
            self.assertEqual(len(admitted), len(set(admitted)))
            copied.assert_not_called()
            self.assertFalse(destination.exists())

    def test_large_first_file_and_other_preflight_bounds_copy_nothing(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snapshot-preflight-bound-") as raw:
            base = Path(raw)
            source = base / "large" / "source"
            source.mkdir(parents=True)
            limits = CSDIY_EXAMINER_SNAPSHOT_LIMITS
            (source / "a-large.txt").write_bytes(b"x" * (limits.max_file_bytes + 1))
            (source / "b-small.txt").write_text("small\n", encoding="utf-8")
            destination = base / "large" / "snapshot"
            with mock.patch.object(
                safe_snapshot,
                "_copy_regular_file",
                wraps=safe_snapshot._copy_regular_file,
            ) as copied, self.assertRaisesRegex(WorkspaceError, "file exceeds"):
                _copy_dependency_tree(source, destination, limits=limits)
            copied.assert_not_called()
            self.assertFalse(destination.exists())

            source = base / "aggregate" / "source"
            source.mkdir(parents=True)
            (source / "a.txt").write_bytes(b"123")
            (source / "b.txt").write_bytes(b"456")
            destination = base / "aggregate" / "snapshot"
            aggregate_limits = SnapshotLimits(10, 10, 5, 4, 5)
            with mock.patch.object(
                safe_snapshot,
                "_copy_regular_file",
                wraps=safe_snapshot._copy_regular_file,
            ) as copied, self.assertRaisesRegex(WorkspaceError, "total bytes"):
                _copy_dependency_tree(
                    source, destination, limits=aggregate_limits
                )
            # The first small file can be copied before a later aggregate
            # overflow is discovered, but the partial tree is always removed.
            self.assertEqual(1, copied.call_count)
            self.assertFalse(destination.exists())

            source = base / "depth" / "source"
            (source / "one" / "two" / "three").mkdir(parents=True)
            (source / "one" / "two" / "three" / "answer.txt").touch()
            destination = base / "depth" / "snapshot"
            depth_limits = SnapshotLimits(20, 10, 20, 20, 2)
            with mock.patch.object(
                safe_snapshot,
                "_copy_regular_file",
                wraps=safe_snapshot._copy_regular_file,
            ) as copied, self.assertRaisesRegex(WorkspaceError, "depth"):
                _copy_dependency_tree(source, destination, limits=depth_limits)
            copied.assert_not_called()
            self.assertFalse(destination.exists())

    def test_snapshot_rejects_hardlink_and_copies_only_rwx_mode_bits(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snapshot-hardlink-") as raw:
            root = Path(raw)
            source = root / "source"
            source.mkdir()
            candidate = source / "answer.txt"
            candidate.write_text("answer\n", encoding="utf-8")
            os.link(candidate, root / "external-alias")
            destination = root / "snapshot"
            with self.assertRaisesRegex(WorkspaceError, "hard-link"):
                _copy_dependency_tree(source, destination)
            self.assertFalse(destination.exists())

            (root / "external-alias").unlink()
            candidate.chmod(0o6755)
            source.chmod(0o1777)
            _copy_dependency_tree(source, destination)
            self.assertEqual(
                0o755,
                destination.joinpath("answer.txt").stat().st_mode & 0o7777,
            )
            self.assertEqual(0o777, destination.stat().st_mode & 0o7777)

    def test_snapshot_detects_root_and_directory_rename_races(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snapshot-rename-race-") as raw:
            base = Path(raw)
            for race in ("root", "directory"):
                source = base / race / "source"
                nested = source / "nested"
                nested.mkdir(parents=True)
                (nested / "answer.txt").write_text("answer\n", encoding="utf-8")
                destination = base / race / "snapshot"
                original_copy = safe_snapshot._copy_regular_file
                raced = False

                def rename_after_copy(*args: object, **kwargs: object) -> int:
                    nonlocal raced
                    copied = original_copy(*args, **kwargs)
                    if not raced:
                        raced = True
                        target = source if race == "root" else nested
                        target.rename(target.with_name(target.name + "-retired"))
                        target.mkdir()
                    return copied

                with self.subTest(race=race), mock.patch.object(
                    safe_snapshot,
                    "_copy_regular_file",
                    side_effect=rename_after_copy,
                ), self.assertRaises(WorkspaceError):
                    _copy_dependency_tree(source, destination)
                self.assertTrue(raced)
                self.assertFalse(destination.exists())


if __name__ == "__main__":
    unittest.main()
