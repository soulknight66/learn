import os
import tempfile
import unittest
from pathlib import Path

from minibox.config import from_dict
from minibox.errors import RootfsError
from minibox.rootfs import resolve_executable


class RootfsResolutionPublicTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.rootfs = Path(self.temporary_directory.name) / "rootfs"
        self.rootfs.mkdir()

    def make_spec(self, argv, env=None):
        data = {
            "schema_version": 1,
            "rootfs": str(self.rootfs),
            "argv": argv,
        }
        if env is not None:
            data["env"] = env
        return from_dict(data)

    def make_executable(self, guest_path, mode=0o755):
        host_path = self.rootfs / guest_path.lstrip("/")
        host_path.parent.mkdir(parents=True, exist_ok=True)
        host_path.write_bytes(b"#!/bin/sh\n")
        host_path.chmod(mode)
        return host_path

    def test_absolute_guest_path_maps_inside_rootfs(self):
        executable = self.make_executable("/opt/bin/hello")
        spec = self.make_spec(["/opt/bin/hello", "argument"])

        resolved = resolve_executable(spec)

        self.assertIsInstance(resolved, Path)
        self.assertEqual(resolved, executable)

    def test_bare_command_uses_default_path(self):
        executable = self.make_executable("/usr/bin/hello")
        spec = self.make_spec(["hello"])

        self.assertEqual(resolve_executable(spec), executable)

    def test_environment_path_controls_search_order(self):
        first = self.make_executable("/custom/first/tool")
        self.make_executable("/custom/second/tool")
        spec = self.make_spec(
            ["tool"], {"PATH": "/custom/first:/custom/second"}
        )

        self.assertEqual(resolve_executable(spec), first)

    def test_non_executable_and_directory_candidates_are_rejected(self):
        self.make_executable("/bin/plain", mode=0o644)
        directory = self.rootfs / "bin" / "directory"
        directory.mkdir()
        directory.chmod(0o755)

        for argv in (["/bin/plain"], ["/bin/directory"]):
            with self.subTest(argv=argv):
                with self.assertRaises(RootfsError):
                    resolve_executable(self.make_spec(argv))

    def test_traversal_is_rejected_even_when_it_would_normalize_inside_rootfs(self):
        self.make_executable("/bin/hello")

        with self.assertRaises(RootfsError):
            resolve_executable(self.make_spec(["/usr/../bin/hello"]))

    def test_symlink_executable_is_rejected(self):
        target = self.make_executable("/bin/real")
        link = target.with_name("linked")
        try:
            os.symlink(target.name, link)
        except (NotImplementedError, OSError) as exc:
            self.skipTest("symlinks are unavailable: {}".format(exc))

        with self.assertRaises(RootfsError):
            resolve_executable(self.make_spec(["/bin/linked"]))


if __name__ == "__main__":
    unittest.main()
