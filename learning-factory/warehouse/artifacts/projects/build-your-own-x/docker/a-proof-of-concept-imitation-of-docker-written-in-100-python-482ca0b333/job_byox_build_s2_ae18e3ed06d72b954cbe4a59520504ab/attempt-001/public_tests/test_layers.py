from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pydocklet import InvalidLayer, LayerApplier, PathEscape

from public_tests.helpers import write_layer, write_symlink_layer


class LayerTests(unittest.TestCase):
    def test_later_layer_overwrites_and_whiteouts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            rootfs = work / "rootfs"
            lower = write_layer(
                work / "lower.tar",
                [
                    ("etc", None, 0o755),
                    ("etc/message", b"old\n", 0o600),
                    ("etc/keep", b"keep\n", 0o755),
                ],
            )
            upper = write_layer(
                work / "upper.tar",
                [
                    ("etc/.wh.message", b"", 0o644),
                    ("etc/keep", b"new\n", 0o600),
                ],
            )
            applier = LayerApplier()
            applier.apply(lower, rootfs)
            applier.apply(upper, rootfs)

            self.assertFalse((rootfs / "etc" / "message").exists())
            self.assertEqual((rootfs / "etc" / "keep").read_bytes(), b"new\n")
            self.assertEqual((rootfs / "etc" / "keep").stat().st_mode & 0o777, 0o644)
            self.assertFalse(any(".wh." in path.name for path in rootfs.rglob("*")))

    def test_unsafe_header_is_rejected_before_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            rootfs = work / "rootfs"
            rootfs.mkdir()
            marker = rootfs / "marker"
            marker.write_text("unchanged", encoding="utf-8")
            layer = write_layer(
                work / "bad.tar",
                [("safe", b"would mutate", 0o644), ("../../escape", b"bad", 0o644)],
            )
            with self.assertRaises((InvalidLayer, PathEscape)):
                LayerApplier().apply(layer, rootfs)
            self.assertEqual(marker.read_text(encoding="utf-8"), "unchanged")
            self.assertFalse((rootfs / "safe").exists())

    def test_symbolic_link_member_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            layer = write_symlink_layer(work / "link.tar", "shortcut", "/etc")
            with self.assertRaises(InvalidLayer):
                LayerApplier().apply(layer, work / "rootfs")


if __name__ == "__main__":
    unittest.main()
