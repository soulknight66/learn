from __future__ import annotations

import gzip
import io
import os
from pathlib import Path
import tarfile
import tempfile
import unittest

from minibox.archive import LayerLimits, apply_layer
from minibox.errors import InvalidArchive


def archive_with(path: Path, entries: list[tarfile.TarInfo], payloads: list[bytes | None]) -> None:
    with tarfile.open(path, "w") as archive:
        for info, payload in zip(entries, payloads):
            archive.addfile(info, io.BytesIO(payload) if payload is not None else None)


def regular(name: str, payload: bytes) -> tuple[tarfile.TarInfo, bytes]:
    info = tarfile.TarInfo(name)
    info.size = len(payload)
    return info, payload


class ReferenceArchiveTests(unittest.TestCase):
    def test_rejects_all_special_member_types(self) -> None:
        special_types = (
            tarfile.SYMTYPE,
            tarfile.LNKTYPE,
            tarfile.CHRTYPE,
            tarfile.BLKTYPE,
            tarfile.FIFOTYPE,
        )
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            for index, member_type in enumerate(special_types):
                info = tarfile.TarInfo("special")
                info.type = member_type
                info.linkname = "target"
                layer = base / f"special-{index}.tar"
                archive_with(layer, [info], [None])
                with self.subTest(member_type=member_type), self.assertRaises(InvalidArchive):
                    apply_layer(layer, base / f"root-{index}")

    def test_count_and_total_limits_include_all_regular_payloads(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            first, first_data = regular("first", b"abc")
            second, second_data = regular("second", b"def")
            layer = base / "layer.tar"
            archive_with(layer, [first, second], [first_data, second_data])
            with self.assertRaises(InvalidArchive):
                apply_layer(layer, base / "count", limits=LayerLimits(max_members=1))
            with self.assertRaises(InvalidArchive):
                apply_layer(layer, base / "total", limits=LayerLimits(max_total_size=5))
            self.assertFalse((base / "count").exists())
            self.assertFalse((base / "total").exists())

    def test_nonempty_whiteout_is_rejected_before_writes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            safe, safe_data = regular("safe", b"safe")
            marker, marker_data = regular(".wh.target", b"x")
            layer = base / "layer.tar"
            archive_with(layer, [safe, marker], [safe_data, marker_data])
            with self.assertRaises(InvalidArchive):
                apply_layer(layer, base / "rootfs")
            self.assertFalse((base / "rootfs").exists())

    def test_whiteout_cannot_name_dot_or_parent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            for index, name in enumerate((".wh..", ".wh...")):
                marker, marker_data = regular(name, b"")
                layer = base / f"whiteout-{index}.tar"
                archive_with(layer, [marker], [marker_data])
                with self.subTest(name=name), self.assertRaises(InvalidArchive):
                    apply_layer(layer, base / "rootfs")
            self.assertTrue(base.exists())

    def test_replaces_file_with_directory_and_directory_with_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            rootfs = base / "rootfs"
            rootfs.mkdir()
            (rootfs / "node").write_bytes(b"old-file")
            (rootfs / "other").mkdir()
            (rootfs / "other" / "child").write_bytes(b"old-child")
            directory = tarfile.TarInfo("node")
            directory.type = tarfile.DIRTYPE
            directory.mode = 0o755
            child, child_data = regular("node/child", b"new-child")
            replacement, replacement_data = regular("other", b"new-file")
            layer = base / "layer.tar"
            archive_with(
                layer,
                [directory, child, replacement],
                [None, child_data, replacement_data],
            )
            apply_layer(layer, rootfs)
            self.assertEqual((rootfs / "node" / "child").read_bytes(), b"new-child")
            self.assertEqual((rootfs / "other").read_bytes(), b"new-file")

    def test_reads_compressed_tar_and_strips_sticky_bit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            raw = base / "raw.tar"
            info, payload = regular("bin/program", b"content")
            info.mode = 0o1755
            archive_with(raw, [info], [payload])
            compressed = base / "layer.tar.gz"
            with raw.open("rb") as source, gzip.open(compressed, "wb") as target:
                target.write(source.read())
            rootfs = base / "rootfs"
            apply_layer(compressed, rootfs)
            self.assertEqual((rootfs / "bin" / "program").read_bytes(), b"content")
            self.assertEqual(os.stat(rootfs / "bin" / "program").st_mode & 0o7000, 0)

    def test_rejects_symlink_in_rootfs_path_itself(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            real = base / "real"
            real.mkdir()
            linked = base / "linked"
            linked.symlink_to(real, target_is_directory=True)
            info, payload = regular("payload", b"blocked")
            layer = base / "layer.tar"
            archive_with(layer, [info], [payload])
            with self.assertRaises(InvalidArchive):
                apply_layer(layer, linked)
            self.assertFalse((real / "payload").exists())


if __name__ == "__main__":
    unittest.main()
