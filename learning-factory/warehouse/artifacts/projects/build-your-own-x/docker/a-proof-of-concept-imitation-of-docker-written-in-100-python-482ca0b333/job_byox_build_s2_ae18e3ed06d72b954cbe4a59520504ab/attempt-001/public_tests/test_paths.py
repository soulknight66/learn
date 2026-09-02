from __future__ import annotations

import tempfile
import unittest
from pathlib import Path, PurePosixPath

from pydocklet import PathEscape, resolve_beneath, safe_member_path


class SafePathTests(unittest.TestCase):
    def test_normalizes_relative_posix_name(self) -> None:
        self.assertEqual(safe_member_path("./usr//local/bin/tool"), PurePosixPath("usr/local/bin/tool"))

    def test_rejects_escape_forms(self) -> None:
        for candidate in ("", ".", "/etc/passwd", "../out", "a/../out", "a\\b", "bad\0name"):
            with self.subTest(candidate=candidate):
                with self.assertRaises(PathEscape):
                    safe_member_path(candidate)

    def test_resolve_beneath_is_structural(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "root"
            root.mkdir()
            result = resolve_beneath(root, PurePosixPath("var/data.txt"))
            self.assertEqual(result, root / "var" / "data.txt")
            self.assertTrue(result.is_relative_to(root))


if __name__ == "__main__":
    unittest.main()
