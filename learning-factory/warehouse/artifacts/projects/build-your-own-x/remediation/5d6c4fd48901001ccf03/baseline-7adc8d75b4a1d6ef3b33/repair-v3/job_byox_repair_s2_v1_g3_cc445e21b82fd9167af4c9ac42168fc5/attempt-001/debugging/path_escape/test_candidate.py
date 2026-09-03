from pathlib import Path
import tempfile
import unittest

from candidate import resolve_beneath


class EscapeReproducer(unittest.TestCase):
    def test_sibling_prefix_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "root"
            sibling = base / "root-other"
            root.mkdir()
            sibling.mkdir()
            with self.assertRaises(ValueError):
                resolve_beneath(root, "/../root-other/file")

    def test_existing_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "root"
            outside = base / "root-outside"
            root.mkdir()
            outside.mkdir()
            (root / "jump").symlink_to(outside, target_is_directory=True)
            with self.assertRaises(ValueError):
                resolve_beneath(root, "/jump/file")


if __name__ == "__main__":
    unittest.main()
