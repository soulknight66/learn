from pathlib import Path
import stat
import tempfile
import unittest

from minictr.errors import TransitionError, ValidationError
from minictr.paths import resolve_guest_path
from minictr.planner import LaunchPlan, build_launch_plan
from minictr.registry import Registry
from minictr.runner import MAX_PAYLOAD, Runner
from minictr.spec import ContainerSpec


class AdversarialReferenceTests(unittest.TestCase):
    def test_sibling_prefix_and_symlink_do_not_escape(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "root"
            sibling = base / "root-evicted"
            root.mkdir()
            sibling.mkdir()
            (root / "link").symlink_to(sibling, target_is_directory=True)
            for guest in ("/../root-evicted/file", "/link/file"):
                with self.subTest(guest=guest), self.assertRaises(ValidationError):
                    resolve_guest_path(root, guest)

    def test_shell_metacharacters_remain_workload_data(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "root"
            (root / "proc").mkdir(parents=True)
            executable = base / "unshare"
            executable.write_text("test", encoding="utf-8")
            executable.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
            spec = ContainerSpec.from_mapping(
                {
                    "id": "argv",
                    "rootfs": str(root),
                    "command": ["/bin/echo", "; touch /host/pwned", "$(id)"],
                }
            )
            plan = build_launch_plan(spec, str(executable))
            joined = " ".join(plan.argv)
            self.assertNotIn("touch", joined)
            self.assertNotIn("$(id)", joined)

    def test_sql_looking_lookup_is_only_data(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "state.db"
            registry = Registry(path)
            try:
                spec = ContainerSpec.from_mapping(
                    {"id": "safe", "rootfs": "/tmp/root", "command": ["/bin/true"]}
                )
                registry.create(spec, "2026-01-01T00:00:00Z")
                with self.assertRaises(TransitionError):
                    registry.get("safe' OR 1=1 --")
                self.assertEqual(registry.get("safe").state, "CREATED")
            finally:
                registry.close()

    def test_oversized_payload_never_reaches_launcher(self):
        launched = []
        runner = Runner(popen_factory=lambda *_a, **_kw: launched.append(True))
        inert = LaunchPlan(("/bin/false",), (("LANG", "C"),), 1.0)
        with self.assertRaises(ValidationError):
            runner.run(inert, b" " * (MAX_PAYLOAD + 1))
        self.assertEqual(launched, [])


if __name__ == "__main__":
    unittest.main()
