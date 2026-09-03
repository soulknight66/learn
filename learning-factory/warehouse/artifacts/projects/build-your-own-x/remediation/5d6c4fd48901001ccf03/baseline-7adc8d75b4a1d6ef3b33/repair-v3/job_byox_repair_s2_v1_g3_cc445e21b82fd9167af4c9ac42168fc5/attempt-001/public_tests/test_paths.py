from pathlib import Path
import tempfile
import unittest

from minictr.errors import ValidationError
from minictr.paths import resolve_guest_path, validate_rootfs


class PathBoundaryTests(unittest.TestCase):
    def test_resolves_guest_absolute_path_beneath_root(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "root"
            (root / "etc").mkdir(parents=True)
            self.assertEqual(resolve_guest_path(root, "/etc/config"), root / "etc" / "config")

    def test_rejects_parent_component(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "root"
            root.mkdir()
            with self.assertRaises(ValidationError):
                resolve_guest_path(root, "/etc/../../outside")

    def test_rejects_existing_symlink_escape(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "root"
            outside = base / "outside"
            root.mkdir()
            outside.mkdir()
            (root / "jump").symlink_to(outside, target_is_directory=True)
            with self.assertRaises(ValidationError):
                resolve_guest_path(root, "/jump/file")

    def test_rejects_rootfs_symlink(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            real_root = base / "real"
            linked_root = base / "linked"
            real_root.mkdir()
            linked_root.symlink_to(real_root, target_is_directory=True)
            with self.assertRaises(ValidationError):
                validate_rootfs(linked_root)

    def test_rejects_host_filesystem_root(self):
        with self.assertRaises(ValidationError):
            validate_rootfs(Path("/"))


if __name__ == "__main__":
    unittest.main()
