from pathlib import Path
import stat
import tempfile
import unittest

from minictr.errors import ValidationError
from minictr.planner import build_launch_plan
from minictr.spec import ContainerSpec


def make_spec(root: Path, network=False):
    return ContainerSpec.from_mapping(
        {
            "id": "plan",
            "rootfs": str(root),
            "command": ["/bin/echo", "$(not-a-shell)"],
            "env": {"PRIVATE_VALUE": "not-in-argv"},
            "network": network,
        }
    )


class PlannerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)
        self.root = self.base / "root"
        (self.root / "proc").mkdir(parents=True)
        self.unshare = self.base / "unshare"
        self.unshare.write_text("placeholder", encoding="utf-8")
        self.unshare.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)

    def tearDown(self):
        self.temporary.cleanup()

    def test_builds_explicit_isolation_argv(self):
        plan = build_launch_plan(make_spec(self.root), str(self.unshare))
        self.assertEqual(plan.argv[0], str(self.unshare))
        for flag in ("--user", "--map-root-user", "--mount", "--uts", "--ipc", "--pid", "--fork", "--net"):
            self.assertIn(flag, plan.argv)
        self.assertIn("--kill-child=SIGKILL", plan.argv)
        self.assertFalse(any(item.startswith("--mount-proc") for item in plan.argv))
        self.assertEqual(plan.argv[-2:], ("-m", "minictr.child"))
        self.assertNotIn("/bin/echo", plan.argv)
        self.assertNotIn("not-in-argv", plan.argv)

    def test_network_true_omits_new_network_namespace(self):
        plan = build_launch_plan(make_spec(self.root, network=True), str(self.unshare))
        self.assertNotIn("--net", plan.argv)

    def test_helper_environment_is_minimal_and_does_not_include_spec_env(self):
        plan = build_launch_plan(make_spec(self.root), str(self.unshare))
        self.assertEqual(
            set(plan.helper_env), {"LANG", "LC_ALL", "PATH", "PYTHONDONTWRITEBYTECODE", "PYTHONPATH"}
        )
        self.assertNotIn("PRIVATE_VALUE", plan.helper_env)

    def test_rejects_bad_executable_and_bad_root(self):
        for executable in ("relative", str(self.base / "missing")):
            with self.subTest(executable=executable), self.assertRaises(ValidationError):
                build_launch_plan(make_spec(self.root), executable)
        self.unshare.chmod(stat.S_IRUSR | stat.S_IWUSR)
        with self.assertRaises(ValidationError):
            build_launch_plan(make_spec(self.root), str(self.unshare))

    def test_requires_real_proc_directory(self):
        (self.root / "proc").rmdir()
        with self.assertRaises(ValidationError):
            build_launch_plan(make_spec(self.root), str(self.unshare))


if __name__ == "__main__":
    unittest.main()
