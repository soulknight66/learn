from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from minibox.models import ContainerSpec
from minibox.runtime import LinuxNamespaceBackend


class NamespacePlanTests(unittest.TestCase):
    def test_builds_argv_without_interpreting_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            rootfs = Path(temporary).resolve()
            spec = ContainerSpec(
                "demo",
                "base",
                ("/bin/echo", "$(touch nope)", "semi;colon"),
                {"MODE": "test"},
                "/work",
            )
            argv = LinuxNamespaceBackend("nsbox").build_argv(rootfs, spec)

        self.assertEqual(argv[0], "nsbox")
        self.assertIn("--user", argv)
        self.assertIn("--map-root-user", argv)
        self.assertIn("--mount", argv)
        self.assertIn("--pid", argv)
        self.assertIn("--fork", argv)
        self.assertIn("--mount-proc=/proc", argv)
        self.assertIn(f"--root={rootfs}", argv)
        self.assertIn("--wd=/work", argv)
        separator = argv.index("--")
        self.assertEqual(argv[separator + 1 :], spec.argv)
        self.assertNotIn("--net", argv)

    def test_network_namespace_is_opt_in(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            spec = ContainerSpec("demo", "base", ("/bin/true",), network=True)
            argv = LinuxNamespaceBackend().build_argv(Path(temporary), spec)
        self.assertIn("--net", argv)


if __name__ == "__main__":
    unittest.main()
