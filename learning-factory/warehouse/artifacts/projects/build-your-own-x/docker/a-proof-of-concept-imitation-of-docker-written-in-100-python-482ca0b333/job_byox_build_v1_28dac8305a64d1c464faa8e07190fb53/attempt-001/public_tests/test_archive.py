from __future__ import annotations

import io
import os
from pathlib import Path
import tarfile
import tempfile
import unittest

from minibox.archive import LayerLimits, apply_layer, safe_member_path
from minibox.errors import InvalidArchive


def write_tar(path: Path, members: list[tuple[str, bytes | None, str]]) -> None:
    with tarfile.open(path, "w") as archive:
        for name, content, kind in members:
            info = tarfile.TarInfo(name)
            if kind == "dir":
                info.type = tarfile.DIRTYPE
                archive.addfile(info)
            elif kind == "symlink":
                info.type = tarfile.SYMTYPE
                info.linkname = "elsewhere"
                archive.addfile(info)
            else:
                payload = content or b""
                info.size = len(payload)
                info.mode = 0o6755
                archive.addfile(info, io.BytesIO(payload))


class MemberPathTests(unittest.TestCase):
    def test_normalizes_dot_segments(self) -> None:
        self.assertEqual(safe_member_path("./usr/bin/tool"), Path("usr/bin/tool"))

    def test_rejects_escapes_and_ambiguous_names(self) -> None:
        for name in ("/etc/passwd", "../escape", "a/../../escape", "a\\b", "x\x00y", "."):
            with self.subTest(name=name), self.assertRaises(InvalidArchive):
                safe_member_path(name)


class LayerTests(unittest.TestCase):
    def test_writes_files_and_applies_whiteouts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            rootfs = base / "rootfs"
            (rootfs / "sub").mkdir(parents=True)
            (rootfs / "remove").write_text("old", encoding="utf-8")
            (rootfs / "keep").write_text("keep", encoding="utf-8")
            (rootfs / "sub" / "old").write_text("old", encoding="utf-8")
            layer = base / "layer.tar"
            write_tar(
                layer,
                [
                    (".wh.remove", b"", "file"),
                    ("sub/.wh..wh..opq", b"", "file"),
                    ("sub/new", b"new", "file"),
                    ("bin/tool", b"payload", "file"),
                ],
            )

            stats = apply_layer(layer, rootfs)

            self.assertFalse((rootfs / "remove").exists())
            self.assertEqual((rootfs / "keep").read_text(encoding="utf-8"), "keep")
            self.assertFalse((rootfs / "sub" / "old").exists())
            self.assertEqual((rootfs / "sub" / "new").read_bytes(), b"new")
            self.assertEqual(stats.files_written, 2)
            self.assertEqual(stats.whiteouts_applied, 2)
            self.assertEqual(stats.bytes_written, 10)
            self.assertEqual(os.stat(rootfs / "bin" / "tool").st_mode & 0o7000, 0)

    def test_rejects_archive_before_payload_write(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            rootfs = base / "rootfs"
            rootfs.mkdir()
            layer = base / "bad.tar"
            write_tar(layer, [("safe", b"must-not-appear", "file"), ("../escape", b"bad", "file")])
            with self.assertRaises(InvalidArchive):
                apply_layer(layer, rootfs)
            self.assertFalse((rootfs / "safe").exists())
            self.assertFalse((base / "escape").exists())

    def test_rejects_links_duplicates_and_limits(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            rootfs = base / "rootfs"
            rootfs.mkdir()
            for filename, members, limits in (
                ("link.tar", [("link", None, "symlink")], None),
                ("duplicate.tar", [("same", b"a", "file"), ("./same", b"b", "file")], None),
                ("large.tar", [("large", b"12345", "file")], LayerLimits(max_file_size=4)),
            ):
                layer = base / filename
                write_tar(layer, members)
                with self.subTest(filename=filename), self.assertRaises(InvalidArchive):
                    apply_layer(layer, rootfs, limits=limits)

    def test_refuses_existing_symlink_parent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            outside = base / "outside"
            outside.mkdir()
            rootfs = base / "rootfs"
            rootfs.mkdir()
            (rootfs / "linked").symlink_to(outside, target_is_directory=True)
            layer = base / "layer.tar"
            write_tar(layer, [("linked/payload", b"bad", "file")])
            with self.assertRaises(InvalidArchive):
                apply_layer(layer, rootfs)
            self.assertFalse((outside / "payload").exists())


if __name__ == "__main__":
    unittest.main()
