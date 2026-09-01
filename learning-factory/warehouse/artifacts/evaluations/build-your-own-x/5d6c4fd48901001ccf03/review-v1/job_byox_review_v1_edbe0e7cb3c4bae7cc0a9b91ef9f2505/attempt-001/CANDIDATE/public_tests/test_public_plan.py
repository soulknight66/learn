import tempfile
import unittest
from dataclasses import is_dataclass
from pathlib import Path

from minibox.config import from_dict
from minibox.plan import IsolationPlan, build_plan


class IsolationPlanPublicTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.rootfs = Path(self.temporary_directory.name) / "rootfs"
        self.rootfs.mkdir()

    def make_spec(self, network_mode="none"):
        return from_dict(
            {
                "schema_version": 1,
                "rootfs": str(self.rootfs),
                "argv": ["/bin/program", "an argument; not shell syntax"],
                "network_mode": network_mode,
            }
        )

    def test_none_network_plan_has_all_requested_namespaces(self):
        plan = build_plan(
            self.make_spec("none"),
            unshare_path="/test/bin/unshare",
            python_path="/test/bin/python3",
        )

        self.assertTrue(is_dataclass(plan))
        self.assertIsInstance(plan, IsolationPlan)
        self.assertEqual(
            plan.namespaces, ("user", "mount", "pid", "uts", "ipc", "net")
        )
        self.assertEqual(
            plan.argv,
            (
                "/test/bin/unshare",
                "--user",
                "--map-root-user",
                "--mount",
                "--pid",
                "--fork",
                "--uts",
                "--ipc",
                "--net",
                "--",
                "/test/bin/python3",
                "-m",
                "minibox._child",
            ),
        )

    def test_host_network_plan_omits_only_network_namespace(self):
        plan = build_plan(self.make_spec("host"))

        self.assertEqual(plan.namespaces, ("user", "mount", "pid", "uts", "ipc"))
        self.assertNotIn("--net", plan.argv)
        self.assertEqual(plan.argv[0], "/usr/bin/unshare")
        self.assertEqual(plan.argv[-3:], ("/usr/bin/python3", "-m", "minibox._child"))

    def test_plan_is_an_argv_tuple_not_a_shell_command(self):
        plan = build_plan(self.make_spec())

        self.assertIsInstance(plan.argv, tuple)
        self.assertTrue(all(isinstance(item, str) for item in plan.argv))
        self.assertNotIn("/bin/sh", plan.argv)
        self.assertNotIn("-c", plan.argv)


if __name__ == "__main__":
    unittest.main()
