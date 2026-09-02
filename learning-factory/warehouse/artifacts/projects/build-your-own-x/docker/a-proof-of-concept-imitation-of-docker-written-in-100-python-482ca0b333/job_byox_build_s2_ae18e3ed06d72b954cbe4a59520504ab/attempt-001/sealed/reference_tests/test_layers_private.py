from __future__ import annotations

import tarfile
import tempfile
import unittest
from pathlib import Path, PurePosixPath

from pydocklet import InvalidLayer, LayerApplier, LayerLimits, PathEscape
from pydocklet.paths import resolve_beneath, safe_member_path

from sealed.reference_tests.helpers import directory, regular, tar_with, write_regular_layer


class PrivatePathTests(unittest.TestCase):
    def test_non_string_and_windows_separator_are_rejected(self) -> None:
        for value in (None, 12, b"path", "C:\\host\\file"):
            with self.subTest(value=value):
                with self.assertRaises(PathEscape):
                    safe_member_path(value)  # type: ignore[arg-type]

    def test_existing_symlink_parent_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            root = work / "root"
            outside = work / "outside"
            root.mkdir()
            outside.mkdir()
            (root / "jump").symlink_to(outside, target_is_directory=True)
            with self.assertRaises(PathEscape):
                resolve_beneath(root, PurePosixPath("jump/file"))


class PrivateLayerTests(unittest.TestCase):
    def test_duplicate_normalized_name_is_rejected_without_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            first = regular("a", b"one")
            second = regular("./a", b"two")
            layer = tar_with(work / "duplicate.tar", [first[0], second[0]], [first[1], second[1]])
            rootfs = work / "rootfs"
            with self.assertRaises(InvalidLayer):
                LayerApplier().apply(layer, rootfs)
            self.assertFalse(rootfs.exists())

    def test_member_and_byte_quotas(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            two = write_regular_layer(
                work / "two.tar", [("a", b"1", 0o644), ("b", b"2", 0o644)]
            )
            with self.assertRaises(InvalidLayer):
                LayerApplier(LayerLimits(max_members=1)).apply(two, work / "member-root")

            large = write_regular_layer(work / "large.tar", [("large", b"1234", 0o644)])
            with self.assertRaises(InvalidLayer):
                LayerApplier(LayerLimits(max_file_bytes=3)).apply(large, work / "file-root")

            total = write_regular_layer(
                work / "total.tar", [("a", b"12", 0o644), ("b", b"34", 0o644)]
            )
            with self.assertRaises(InvalidLayer):
                LayerApplier(LayerLimits(max_file_bytes=2, max_total_bytes=3)).apply(
                    total, work / "total-root"
                )

    def test_fifo_header_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            info = tarfile.TarInfo("pipe")
            info.type = tarfile.FIFOTYPE
            info.size = 0
            layer = tar_with(work / "fifo.tar", [info], [None])
            with self.assertRaises(InvalidLayer):
                LayerApplier().apply(layer, work / "rootfs")

    def test_opaque_whiteout_removes_old_children_before_new_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            lower = write_regular_layer(
                work / "lower.tar",
                [("cache/old-a", b"a", 0o644), ("cache/old-b", b"b", 0o644)],
            )
            upper = write_regular_layer(
                work / "upper.tar",
                [("cache/.wh..wh..opq", b"", 0o644), ("cache/new", b"n", 0o700)],
            )
            rootfs = work / "rootfs"
            applier = LayerApplier()
            applier.apply(lower, rootfs)
            applier.apply(upper, rootfs)
            self.assertEqual([path.name for path in (rootfs / "cache").iterdir()], ["new"])
            self.assertEqual((rootfs / "cache" / "new").stat().st_mode & 0o777, 0o755)

    def test_whiteout_and_replacement_in_same_layer_leaves_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            lower = write_regular_layer(work / "lower.tar", [("note", b"old", 0o644)])
            upper = write_regular_layer(
                work / "upper.tar", [(".wh.note", b"", 0o644), ("note", b"new", 0o644)]
            )
            rootfs = work / "rootfs"
            applier = LayerApplier()
            applier.apply(lower, rootfs)
            applier.apply(upper, rootfs)
            self.assertEqual((rootfs / "note").read_bytes(), b"new")

    def test_existing_destination_symlink_blocks_all_layer_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            rootfs = work / "rootfs"
            outside = work / "outside"
            rootfs.mkdir()
            outside.mkdir()
            (rootfs / "jump").symlink_to(outside, target_is_directory=True)
            layer = write_regular_layer(work / "layer.tar", [("safe", b"data", 0o644)])
            with self.assertRaises(InvalidLayer):
                LayerApplier().apply(layer, rootfs)
            self.assertFalse((rootfs / "safe").exists())

    def test_file_cannot_be_ancestor_of_another_member(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            layer = write_regular_layer(
                work / "conflict.tar", [("a", b"file", 0o644), ("a/b", b"child", 0o644)]
            )
            with self.assertRaises(InvalidLayer):
                LayerApplier().apply(layer, work / "rootfs")

    def test_directory_and_file_modes_are_normalized(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            dir_spec = directory("bin", 0o7777)
            file_spec = regular("bin/tool", b"x", 0o4001)
            layer = tar_with(work / "modes.tar", [dir_spec[0], file_spec[0]], [None, file_spec[1]])
            rootfs = work / "rootfs"
            LayerApplier().apply(layer, rootfs)
            self.assertEqual((rootfs / "bin").stat().st_mode & 0o7777, 0o755)
            self.assertEqual((rootfs / "bin" / "tool").stat().st_mode & 0o7777, 0o755)

    def test_malformed_tar_is_wrapped_as_domain_error(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            malformed = work / "not-a-tar"
            malformed.write_bytes(bytes(range(256)) + b"not-a-tar-header")
            with self.assertRaises(InvalidLayer):
                LayerApplier().apply(malformed, work / "rootfs")


if __name__ == "__main__":
    unittest.main()
