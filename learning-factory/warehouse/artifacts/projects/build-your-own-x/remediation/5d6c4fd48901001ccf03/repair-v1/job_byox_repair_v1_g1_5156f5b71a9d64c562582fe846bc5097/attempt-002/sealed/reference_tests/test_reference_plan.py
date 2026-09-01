import tempfile
import unittest
from pathlib import Path

from minibox.config import from_dict
from minibox.plan import build_plan


class PlanReferenceTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.rootfs = Path(self.temporary_directory.name) / "rootfs"
        self.rootfs.mkdir()

    def spec(self, network_mode):
        return from_dict(
            {
                "schema_version": 1,
                "rootfs": str(self.rootfs),
                "argv": ["program", "$(touch /tmp/not-executed)", "a; b"],
                "network_mode": network_mode,
            }
        )

    def test_none_plan_has_deterministic_order_and_single_separator(self):
        plan = build_plan(
            self.spec("none"),
            unshare_path="/missing/unshare",
            python_path="/missing/python",
        )

        self.assertEqual(
            plan.namespaces, ("user", "mount", "pid", "uts", "ipc", "net")
        )
        self.assertEqual(
            plan.argv,
            (
                "/missing/unshare",
                "--user",
                "--map-root-user",
                "--mount",
                "--pid",
                "--fork",
                "--uts",
                "--ipc",
                "--net",
                "--",
                "/missing/python",
                "-m",
                "minibox._child",
            ),
        )
        self.assertEqual(plan.argv.count("--"), 1)
        self.assertEqual(len(plan.argv), len(set(plan.argv)))

    def test_host_plan_has_no_network_flag_or_namespace(self):
        plan = build_plan(
            self.spec("host"), unshare_path="/u", python_path="/python"
        )

        self.assertEqual(plan.namespaces, ("user", "mount", "pid", "uts", "ipc"))
        self.assertEqual(
            plan.argv,
            (
                "/u",
                "--user",
                "--map-root-user",
                "--mount",
                "--pid",
                "--fork",
                "--uts",
                "--ipc",
                "--",
                "/python",
                "-m",
                "minibox._child",
            ),
        )

    def test_user_arguments_are_not_interpolated_into_parent_shell_syntax(self):
        plan = build_plan(self.spec("none"))

        self.assertNotIn("$(touch /tmp/not-executed)", plan.argv)
        self.assertNotIn("a; b", plan.argv)
        self.assertNotIn("sh", plan.argv)
        self.assertNotIn("-c", plan.argv)
        self.assertTrue(all(isinstance(item, str) for item in plan.argv))


if __name__ == "__main__":
    unittest.main()
