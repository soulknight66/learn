from __future__ import annotations

import io
from pathlib import Path
import tarfile
import tempfile
import unittest

from minibox.archive import apply_layer
from minibox.errors import InvalidArchive


def add_regular(archive: tarfile.TarFile, name: str, data: bytes = b"x") -> None:
    info = tarfile.TarInfo(name)
    info.size = len(data)
    archive.addfile(info, io.BytesIO(data))


class MaliciousLayerTests(unittest.TestCase):
    def test_path_prefix_confusion_does_not_escape(self) -> None:
        names = ("../rootfs-sibling/payload", "dir/../../../payload", "/absolute/payload")
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            for index, name in enumerate(names):
                layer = base / f"attack-{index}.tar"
                with tarfile.open(layer, "w") as archive:
                    add_regular(archive, name)
                with self.subTest(name=name), self.assertRaises(InvalidArchive):
                    apply_layer(layer, base / "rootfs")
            self.assertFalse((base / "rootfs-sibling" / "payload").exists())
            self.assertFalse((base / "payload").exists())

    def test_late_hardlink_rejects_earlier_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            layer = base / "late-link.tar"
            with tarfile.open(layer, "w") as archive:
                add_regular(archive, "apparently-safe", b"do-not-write")
                link = tarfile.TarInfo("late-link")
                link.type = tarfile.LNKTYPE
                link.linkname = "../outside"
                archive.addfile(link)
            rootfs = base / "rootfs"
            with self.assertRaises(InvalidArchive):
                apply_layer(layer, rootfs)
            self.assertFalse((rootfs / "apparently-safe").exists())

    def test_existing_leaf_symlink_is_not_replaced_or_followed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            outside = base / "outside"
            outside.write_bytes(b"original")
            rootfs = base / "rootfs"
            rootfs.mkdir()
            (rootfs / "leaf").symlink_to(outside)
            layer = base / "leaf.tar"
            with tarfile.open(layer, "w") as archive:
                add_regular(archive, "leaf", b"attacker")
            with self.assertRaises(InvalidArchive):
                apply_layer(layer, rootfs)
            self.assertEqual(outside.read_bytes(), b"original")
            self.assertTrue((rootfs / "leaf").is_symlink())

    def test_whiteout_parent_alias_cannot_remove_rootfs_parent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            sentinel = base / "sentinel"
            sentinel.write_bytes(b"keep")
            layer = base / "whiteout.tar"
            with tarfile.open(layer, "w") as archive:
                add_regular(archive, ".wh...", b"")
            with self.assertRaises(InvalidArchive):
                apply_layer(layer, base / "rootfs")
            self.assertEqual(sentinel.read_bytes(), b"keep")


if __name__ == "__main__":
    unittest.main()
