import os
import tempfile
import unittest
from pathlib import Path

from minibox.config import from_dict
from minibox.errors import RootfsError
from minibox.rootfs import resolve_executable


class RootfsSecurityReferenceTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.base = Path(self.temporary_directory.name)
        self.rootfs = self.base / "rootfs"
        self.rootfs.mkdir()

    def spec(self, command, path=None):
        data = {
            "schema_version": 1,
            "rootfs": str(self.rootfs),
            "argv": [command],
        }
        if path is not None:
            data["env"] = {"PATH": path}
        return from_dict(data)

    def file(self, guest_path, mode=0o755):
        result = self.rootfs / guest_path.lstrip("/")
        result.parent.mkdir(parents=True, exist_ok=True)
        result.write_bytes(b"executable fixture\n")
        result.chmod(mode)
        return result

    def make_symlink(self, target, link):
        try:
            os.symlink(target, link)
        except (NotImplementedError, OSError) as exc:
            self.skipTest("symlinks are unavailable: {}".format(exc))

    def test_default_path_prefers_bin_before_usr_bin(self):
        expected = self.file("/bin/tool")
        self.file("/usr/bin/tool")

        self.assertEqual(resolve_executable(self.spec("tool")), expected)

    def test_path_search_skips_missing_and_non_executable_candidates(self):
        self.file("/one/tool", mode=0o644)
        expected = self.file("/three/tool", mode=0o010)

        resolved = resolve_executable(self.spec("tool", "/one:/two:/three"))

        self.assertEqual(resolved, expected)

    def test_path_search_skips_a_directory_candidate(self):
        (self.rootfs / "first" / "tool").mkdir(parents=True)
        expected = self.file("/second/tool")

        resolved = resolve_executable(self.spec("tool", "/first:/second"))

        self.assertEqual(resolved, expected)

    def test_explicit_path_environment_replaces_the_default(self):
        self.file("/bin/tool")

        with self.assertRaises(RootfsError):
            resolve_executable(self.spec("tool", "/custom"))

    def test_absolute_guest_command_does_not_use_path_search(self):
        expected = self.file("/direct/tool")
        self.file("/path/tool")

        resolved = resolve_executable(self.spec("/direct/tool", "/path"))

        self.assertEqual(resolved, expected)

    def test_missing_executable_raises_rootfs_error(self):
        with self.assertRaises(RootfsError):
            resolve_executable(self.spec("missing"))

    def test_any_parent_component_is_rejected_in_command(self):
        self.file("/bin/tool")
        for command in (
            "/usr/../bin/tool",
            "/../bin/tool",
            "../bin/tool",
            "/bin/../../bin/tool",
        ):
            with self.subTest(command=command):
                with self.assertRaises(RootfsError):
                    resolve_executable(self.spec(command))

    def test_parent_component_in_path_entry_is_rejected(self):
        self.file("/bin/tool")

        with self.assertRaises(RootfsError):
            resolve_executable(self.spec("tool", "/safe/../bin"))

    def test_leaf_symlink_cannot_point_inside_or_outside_rootfs(self):
        inside = self.file("/bin/inside")
        outside = self.base / "outside"
        outside.write_bytes(b"outside\n")
        outside.chmod(0o755)
        inside_link = self.rootfs / "bin" / "inside-link"
        outside_link = self.rootfs / "bin" / "outside-link"
        self.make_symlink(inside.name, inside_link)
        self.make_symlink(outside, outside_link)

        for command in ("/bin/inside-link", "/bin/outside-link"):
            with self.subTest(command=command):
                with self.assertRaises(RootfsError):
                    resolve_executable(self.spec(command))

    def test_symlink_in_parent_directory_is_rejected(self):
        real_directory = self.rootfs / "real-bin"
        real_directory.mkdir()
        executable = real_directory / "tool"
        executable.write_bytes(b"tool\n")
        executable.chmod(0o755)
        self.make_symlink("real-bin", self.rootfs / "linked-bin")

        with self.assertRaises(RootfsError):
            resolve_executable(self.spec("/linked-bin/tool"))

    def test_regular_file_needs_at_least_one_execute_bit(self):
        executable = self.file("/bin/group-executable", mode=0o010)
        self.assertEqual(
            resolve_executable(self.spec("/bin/group-executable")), executable
        )

        self.file("/bin/not-executable", mode=0o666)
        with self.assertRaises(RootfsError):
            resolve_executable(self.spec("/bin/not-executable"))

    def test_executable_directory_is_not_a_regular_file(self):
        directory = self.rootfs / "bin" / "looks-executable"
        directory.mkdir(parents=True)
        directory.chmod(0o755)

        with self.assertRaises(RootfsError):
            resolve_executable(self.spec("/bin/looks-executable"))


if __name__ == "__main__":
    unittest.main()
